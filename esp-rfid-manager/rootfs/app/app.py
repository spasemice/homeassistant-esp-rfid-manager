#!/usr/bin/env python3
"""
ESP-RFID Manager - Home Assistant Addon
Manages ESP-RFID devices, users, and access logs through MQTT
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
import sqlite3
from contextlib import contextmanager

from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

# Configuration from environment variables
MQTT_HOST = os.getenv('MQTT_HOST', '127.0.0.1')
MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
MQTT_USER = os.getenv('MQTT_USER', '')
MQTT_PASSWORD = os.getenv('MQTT_PASSWORD', '')
MQTT_TOPIC = os.getenv('MQTT_TOPIC', '/esprfid')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'info').upper()
WEB_PORT = int(os.getenv('WEB_PORT', '8080'))
AUTO_DISCOVERY = os.getenv('AUTO_DISCOVERY', 'true').lower() == 'true'

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'esp-rfid-manager-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Database setup
DB_PATH = '/data/esp_rfid.db'

@contextmanager
def get_db():
    """Database context manager"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize SQLite database with required tables"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # ESP-RFID devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT UNIQUE NOT NULL,
                ip_address TEXT NOT NULL,
                last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'offline',
                door_names TEXT DEFAULT '[]',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT NOT NULL,
                username TEXT NOT NULL,
                device_hostname TEXT NOT NULL,
                acctype INTEGER DEFAULT 1,
                valid_since INTEGER DEFAULT 0,
                valid_until INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(uid, device_hostname),
                FOREIGN KEY (device_hostname) REFERENCES devices (hostname)
            )
        ''')
        
        # Access logs table  
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_hostname TEXT NOT NULL,
                uid TEXT,
                username TEXT,
                access_type TEXT,
                is_known BOOLEAN,
                door_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                raw_data TEXT,
                FOREIGN KEY (device_hostname) REFERENCES devices (hostname)
            )
        ''')
        
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_hostname TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source TEXT,
                description TEXT,
                data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_hostname) REFERENCES devices (hostname)
            )
        ''')
        
        # Card registration table (temporary storage for new cards)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT NOT NULL,
                device_hostname TEXT NOT NULL,
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")

class ESPRFIDManager:
    """Main class for managing ESP-RFID devices"""
    
    def __init__(self):
        self.mqtt_client = None
        self.connected_devices: Dict[str, Dict] = {}
        self.scheduler = BackgroundScheduler()
        self.ha_discovery_sent = set()  # Track which discoveries we've sent
        self.card_detection_active = False  # Track if we should detect new cards
        self.init_mqtt()
        
    def init_mqtt(self):
        """Initialize MQTT client"""
        self.mqtt_client = mqtt.Client()
        
        if MQTT_USER and MQTT_PASSWORD:
            self.mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
            
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        try:
            self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            logger.info(f"MQTT client connected to {MQTT_HOST}:{MQTT_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Subscribe to ESP-RFID topics
            client.subscribe(f"{MQTT_TOPIC}/+/send")     # Device status/heartbeat messages
            client.subscribe(f"{MQTT_TOPIC}/send")       # For single device setup
            client.subscribe(f"{MQTT_TOPIC}/+/cmd")      # Command responses from devices
            client.subscribe(f"{MQTT_TOPIC}/cmd")        # For single device cmd responses
            client.subscribe(f"{MQTT_TOPIC}/+/tag")      # Card scan events from devices
            client.subscribe(f"{MQTT_TOPIC}/tag")        # For single device tag events
            client.subscribe("homeassistant/button/+/cmd")  # For HA button commands
            logger.info(f"Subscribed to: {MQTT_TOPIC}/+/send, {MQTT_TOPIC}/+/cmd, {MQTT_TOPIC}/+/tag, and HA button commands")
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        logger.warning("Disconnected from MQTT broker")
        
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            logger.debug(f"Received MQTT message: {topic}")
            
            # Handle button commands from Home Assistant
            if "/unlock/cmd" in topic and topic.startswith("homeassistant/button/"):
                # Extract hostname from topic: homeassistant/button/esp_rfid_HOSTNAME_unlock/cmd
                parts = topic.split('/')
                if len(parts) >= 3:
                    button_id = parts[2]  # esp_rfid_HOSTNAME_unlock
                    if button_id.startswith('esp_rfid_') and button_id.endswith('_unlock'):
                        hostname = button_id[9:-7]  # Remove esp_rfid_ prefix and _unlock suffix
                        self.handle_unlock_command(hostname)
                return
            
            payload = json.loads(msg.payload.decode())
            logger.info(f"📩 MQTT Message: {topic} -> {payload}")
            
            # Extract device info from topic or payload
            device_hostname = payload.get('hostname', 'unknown')
            device_ip = payload.get('ip', '')
            
            # Try to extract hostname from topic if not in payload
            if device_hostname == 'unknown' and '/' in topic:
                topic_parts = topic.split('/')
                if len(topic_parts) >= 2:
                    potential_hostname = topic_parts[1]  # esprfid/HOSTNAME/send -> HOSTNAME
                    if potential_hostname and potential_hostname != 'send' and potential_hostname != 'cmd' and potential_hostname != 'tag':
                        device_hostname = potential_hostname
                        payload['hostname'] = device_hostname  # Add to payload for later processing
            
            # Update device status
            self.update_device_status(device_hostname, device_ip)
            
            # Handle different message types
            msg_type = payload.get('type', '')
            cmd = payload.get('cmd', '')
            
            # Check if this is from a tag topic (card scan event)
            if '/tag' in topic:
                self.handle_tag_message(payload)
            elif msg_type == 'boot':
                self.handle_boot_message(payload)
            elif msg_type == 'heartbeat':
                self.handle_heartbeat_message(payload)  
            elif msg_type == 'access':
                self.handle_access_message(payload)
            elif msg_type in ['INFO', 'WARN', 'ERRO']:
                self.handle_event_message(payload)
            elif cmd == 'userfile':
                self.handle_userfile_message(payload)
            elif cmd == 'log':
                self.handle_log_message(payload)
            elif payload.get('uid') and not msg_type and not cmd:  # Card scan for registration (no cmd or type)
                self.handle_card_scan(payload)
            
            # Also check for log messages from cmd topic 
            if 'cmd' in topic and payload.get('cmd') == 'log':
                self.handle_log_message(payload)
                
            # Emit to web clients
            socketio.emit('mqtt_message', {
                'topic': topic,
                'payload': payload,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def update_device_status(self, hostname: str, ip_address: str):
        """Update device status in database"""
        was_offline = False
        
        # Check if device was offline
        if hostname in self.connected_devices:
            was_offline = self.connected_devices[hostname]['status'] == 'offline'
        else:
            # Check in database
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT status FROM devices WHERE hostname = ?', (hostname,))
                row = cursor.fetchone()
                was_offline = row and row['status'] == 'offline'
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO devices (hostname, ip_address, last_seen, status)
                VALUES (?, ?, datetime('now'), 'online')
            ''', (hostname, ip_address))
            conn.commit()
            
        self.connected_devices[hostname] = {
            'ip_address': ip_address,
            'last_seen': datetime.now(),
            'status': 'online'
        }
        
        # Log when device comes back online
        if was_offline:
            logger.info(f"{hostname} Door Status changed to online")
            # Update HA sensors with detailed attributes
            try:
                timestamp = datetime.now().isoformat()
                
                # Online sensor attributes
                online_attributes = {
                    "hostname": hostname,
                    "ip_address": ip_address,
                    "last_seen": timestamp,
                    "status": "online",
                    "status_change": timestamp,
                    "previous_status": "offline"
                }
                
                # Door status attributes
                door_attributes = {
                    "hostname": hostname,
                    "ip_address": ip_address,
                    "last_status_change": timestamp,
                    "status": "ready",
                    "device_online": True
                }
                
                self.mqtt_client.publish(f"homeassistant/binary_sensor/esp_rfid_{hostname}_online/state", "ON")
                self.mqtt_client.publish(f"homeassistant/binary_sensor/esp_rfid_{hostname}_online/attributes", json.dumps(online_attributes))
                self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_door_status/state", "ready")
                self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_door_status/attributes", json.dumps(door_attributes))
            except Exception as e:
                logger.error(f"Failed to update HA sensors for online device {hostname}: {e}")
        
        # Send Home Assistant MQTT Discovery for this device
        self.send_ha_discovery(hostname, ip_address)
    
    def handle_boot_message(self, payload: Dict):
        """Handle device boot message"""
        hostname = payload.get('hostname')
        logger.info(f"Device {hostname} booted")
        self.log_event(hostname, 'INFO', 'system', 'Device booted', json.dumps(payload))
    
    def handle_heartbeat_message(self, payload: Dict):
        """Handle device heartbeat message"""
        hostname = payload.get('hostname')
        logger.debug(f"Heartbeat from {hostname}")
        # Heartbeats are already handled by update_device_status
    
    def handle_access_message(self, payload: Dict):
        """Handle access event message"""
        hostname = payload.get('hostname', '')
        uid = payload.get('uid', '')
        username = payload.get('username', 'Unknown')
        access_type = payload.get('access', 'Denied')
        is_known = payload.get('isKnown', 'false') == 'true'
        door_name = payload.get('doorName', '')
        
        # Handle multiple doors
        if isinstance(door_name, list):
            door_name = ', '.join(door_name)
        if isinstance(access_type, list):
            access_type = ', '.join(access_type)
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO access_logs 
                (device_hostname, uid, username, access_type, is_known, door_name, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (hostname, uid, username, access_type, is_known, door_name, json.dumps(payload)))
            conn.commit()
        
        logger.info(f"Access log: {username} ({uid}) -> {access_type} on {hostname}")
        
        # Emit to web clients
        socketio.emit('access_event', {
            'hostname': hostname,
            'uid': uid,
            'username': username,
            'access_type': access_type,
            'is_known': is_known,
            'door_name': door_name,
            'timestamp': datetime.now().isoformat()
        })
        
        # Update Home Assistant sensors
        self.update_ha_sensors(hostname, 'access', {
            'username': username,
            'uid': uid,
            'access_type': access_type,
            'door_name': door_name,
            'timestamp': datetime.now().isoformat()
        })
        
        # Log to HA history
        self.log_access_to_ha_history(hostname, username, uid, access_type, 'rfid')
    
    def handle_event_message(self, payload: Dict):
        """Handle system event message"""
        hostname = payload.get('hostname', '')
        event_type = payload.get('type', 'INFO')
        source = payload.get('src', '')
        description = payload.get('desc', '')
        data = payload.get('data', '')
        
        # Handle unknown card scan for automatic registration - only if detection is active
        if (event_type == 'WARN' and source == 'rfid' and 
            description == 'Unknown rfid tag is scanned' and data and self.card_detection_active):
            # Extract UID from data (before space) like "8d0a0186 34"
            uid = data.split(' ')[0] if ' ' in data else data
            
            if uid and hostname:
                logger.info(f"Card detection active - Unknown card detected: {uid} on {hostname}")
                socketio.emit('new_card_detected', {
                    'uid': uid,
                    'hostname': hostname,
                    'timestamp': datetime.now().isoformat()
                })
        
        self.log_event(hostname, event_type, source, description, data)
    
    def handle_userfile_message(self, payload: Dict):
        """Handle user file message from device"""
        # This is response to getuserlist command
        uid = payload.get('uid', '')
        username = payload.get('user', '')
        acctype = payload.get('acctype', 1)
        valid_since = payload.get('validsince', 0)
        valid_until = payload.get('validuntil', 0)
        hostname = payload.get('hostname', '')
        
        if uid and username and hostname:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (uid, username, device_hostname, acctype, valid_since, valid_until, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (uid, username, hostname, acctype, valid_since, valid_until))
                conn.commit()
            
            logger.info(f"Synced user from device {hostname}: {username} ({uid})")
            
            # Emit real-time update
            socketio.emit('user_synced', {
                'uid': uid,
                'username': username,
                'hostname': hostname,
                'acctype': acctype
            })
        else:
            logger.warning(f"Incomplete user data received: {payload}")
    
    def handle_tag_message(self, payload: Dict):
        """Handle tag message from device (card scan events from /tag topic)"""
        # Extract device hostname from MQTT topic if not in payload
        hostname = payload.get('hostname', 'unknown')
        uid = payload.get('uid', '')
        username = payload.get('username', 'Unknown')
        access_type = payload.get('access', 'Denied')
        door_name = payload.get('doorName', hostname)
        pincode = payload.get('pincode', '')
        timestamp_unix = payload.get('time', 0)
        
        logger.info(f"🏷️ Tag scan from {hostname}: {username} ({uid}) -> {access_type}")
        
        # Log the access attempt
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO access_logs 
                (device_hostname, uid, username, access_type, is_known, door_name, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (hostname, uid, username, access_type, username != 'Unknown', door_name, json.dumps(payload)))
            conn.commit()
        
        # Emit access event to web clients
        socketio.emit('access_event', {
            'hostname': hostname,
            'uid': uid,
            'username': username,
            'access_type': access_type,
            'is_known': username != 'Unknown',
            'door_name': door_name,
            'timestamp': datetime.now().isoformat()
        })
        
        # Handle unknown cards for registration - only if detection is active
        if username == 'Unknown' and uid and hostname and self.card_detection_active:
            logger.info(f"🔍 Card detection active - Unknown card detected: {uid} on {hostname}")
            socketio.emit('new_card_detected', {
                'uid': uid,
                'hostname': hostname,
                'timestamp': datetime.now().isoformat()
            })
        elif username == 'Unknown' and uid and hostname:
            logger.info(f"🔍 Unknown card scanned: {uid} on {hostname} (detection not active)")
        
        # Emit card status info (registered or unknown)
        card_scan_event = {
            'uid': uid,
            'username': username,
            'hostname': hostname,
            'door_name': door_name,
            'access_type': access_type,
            'is_registered': username != 'Unknown',
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"🎯 Card scan result: {username} ({uid}) -> {access_type} on {hostname}")
        socketio.emit('card_scan_result', card_scan_event)
        
        # Update Home Assistant sensors
        self.update_ha_sensors(hostname, 'access', {
            'username': username,
            'uid': uid,
            'access_type': access_type,
            'door_name': door_name,
            'timestamp': datetime.now().isoformat()
        })
        
        # Log to HA history
        self.log_access_to_ha_history(hostname, username, uid, access_type, 'rfid')
        
        # If unknown card, also send unknown card event
        if username == 'Unknown':
            self.update_ha_sensors(hostname, 'unknown_card', {
                'uid': uid,
                'hostname': hostname,
                'door_name': door_name,
                'timestamp': datetime.now().isoformat()
            })

    def handle_log_message(self, payload: Dict):
        """Handle log message from device (access attempts)"""
        hostname = payload.get('hostname', '')
        uid = payload.get('uid', '')
        username = payload.get('username', 'Unknown')
        access_type = payload.get('access', 'Denied')
        door_name = payload.get('doorName', '')
        
        # Log the access attempt
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO access_logs 
                (device_hostname, uid, username, access_type, is_known, door_name, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (hostname, uid, username, access_type, username != 'Unknown', door_name, json.dumps(payload)))
            conn.commit()
        
        logger.info(f"Access log: {username} ({uid}) -> {access_type} on {hostname}/{door_name}")
        
        # Emit access event to web clients
        socketio.emit('access_event', {
            'hostname': hostname,
            'uid': uid,
            'username': username,
            'access_type': access_type,
            'is_known': username != 'Unknown',
            'door_name': door_name,
            'timestamp': datetime.now().isoformat()
        })
        
        # Handle unknown cards for registration - only if detection is active
        if username == 'Unknown' and uid and hostname and self.card_detection_active:
            logger.info(f"🔍 Card detection active - Unknown card detected: {uid} on {hostname}")
            socketio.emit('new_card_detected', {
                'uid': uid,
                'hostname': hostname,
                'timestamp': datetime.now().isoformat()
            })
        elif username == 'Unknown' and uid and hostname:
            logger.info(f"🔍 Unknown card scanned: {uid} on {hostname} (detection not active)")
        
        # Emit card status info (registered or unknown)
        card_scan_event = {
            'uid': uid,
            'username': username,
            'hostname': hostname,
            'door_name': door_name,
            'access_type': access_type,
            'is_registered': username != 'Unknown',
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"🎯 Card scan result: {username} ({uid}) -> {access_type} on {hostname}")
        socketio.emit('card_scan_result', card_scan_event)
        
        # Update Home Assistant sensors
        self.update_ha_sensors(hostname, 'access', {
            'username': username,
            'uid': uid,
            'access_type': access_type,
            'door_name': door_name,
            'timestamp': datetime.now().isoformat()
        })
        
        # Log to HA history
        self.log_access_to_ha_history(hostname, username, uid, access_type, 'rfid')
        
        # If unknown card, also send unknown card event
        if username == 'Unknown':
            self.update_ha_sensors(hostname, 'unknown_card', {
                'uid': uid,
                'hostname': hostname,
                'door_name': door_name,
                'timestamp': datetime.now().isoformat()
            })

    def handle_card_scan(self, payload: Dict):
        """Handle unknown card scan for registration"""
        uid = payload.get('uid', '')
        hostname = payload.get('hostname', '')
        
        if uid and hostname:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO card_registrations (uid, device_hostname)
                    VALUES (?, ?)
                ''', (uid, hostname))
                conn.commit()
            
            logger.info(f"New card detected for registration: {uid} on {hostname}")
            socketio.emit('new_card_detected', {
                'uid': uid,
                'hostname': hostname,
                'timestamp': datetime.now().isoformat()
            })
    
    def log_event(self, hostname: str, event_type: str, source: str, description: str, data: str):
        """Log event to database"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (device_hostname, event_type, source, description, data)
                VALUES (?, ?, ?, ?, ?)
            ''', (hostname, event_type, source, description, data))
            conn.commit()
    
    def send_mqtt_command(self, device_ip: str, command: Dict, device_hostname: str = None):
        """Send command to ESP-RFID device via MQTT"""
        command['doorip'] = device_ip
        
        # Find device hostname by IP if not provided
        if not device_hostname:
            for hostname, device_info in self.connected_devices.items():
                if device_info.get('ip_address') == device_ip:
                    device_hostname = hostname
                    break
        
        # Use device-specific topic if hostname found, otherwise fallback to generic
        if device_hostname:
            topic = f"{MQTT_TOPIC}/{device_hostname}/cmd"
        else:
            topic = f"{MQTT_TOPIC}/cmd"
            logger.warning(f"⚠️ Device hostname not found for IP {device_ip}, using generic topic")
        
        try:
            command_json = json.dumps(command)
            result = self.mqtt_client.publish(topic, command_json)
            logger.info(f"📤 MQTT Command sent to {device_hostname or device_ip} via topic '{topic}': {command}")
            logger.info(f"📤 MQTT Publish result: {result.rc} (0=success)")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send MQTT command to {device_hostname or device_ip}: {e}")
            return False
    
    def add_user(self, device_ip: str, uid: str, username: str, acctype: int = 1, 
                 valid_since: int = 0, valid_until: int = 0, device_hostname: str = None) -> bool:
        """Add user to ESP-RFID device"""
        command = {
            'cmd': 'adduser',
            'uid': uid,
            'user': username,
            'acctype': str(acctype),
            'validsince': str(valid_since),
            'validuntil': str(valid_until)
        }
        return self.send_mqtt_command(device_ip, command, device_hostname)
    
    def delete_user(self, device_ip: str, uid: str, device_hostname: str = None) -> bool:
        """Delete user from ESP-RFID device"""
        command = {
            'cmd': 'deletuid',
            'uid': uid
        }
        return self.send_mqtt_command(device_ip, command, device_hostname)
    
    def open_door(self, device_ip: str, device_hostname: str = None) -> bool:
        """Open door on ESP-RFID device"""
        command = {
            'cmd': 'opendoor'
        }
        return self.send_mqtt_command(device_ip, command, device_hostname)
    
    def get_user_list(self, device_ip: str, device_hostname: str = None) -> bool:
        """Request user list from ESP-RFID device"""
        command = {
            'cmd': 'getuserlist'
        }
        return self.send_mqtt_command(device_ip, command, device_hostname)
    
    def send_ha_discovery(self, hostname: str, ip_address: str):
        """Send Home Assistant MQTT Discovery for device sensors"""
        discovery_key = f"{hostname}"
        
        if discovery_key in self.ha_discovery_sent:
            return
        
        device_info = {
            "identifiers": [f"esp_rfid_{hostname}"],
            "name": f"{hostname}",
            "model": "ESP-RFID",
            "manufacturer": "ESP-RFID", 
            "sw_version": "1.0"
        }
        
        # Door Status Sensor  
        door_status_config = {
            "name": f"{hostname} Door",
            "unique_id": f"esp_rfid_{hostname}_door_status",
            "state_topic": f"homeassistant/sensor/esp_rfid_{hostname}_door_status/state",
            "json_attributes_topic": f"homeassistant/sensor/esp_rfid_{hostname}_door_status/attributes",
            "icon": "mdi:door",
            "device": device_info
        }
        
        # Last Access Sensor
        last_access_config = {
            "name": f"{hostname} Last Access",
            "unique_id": f"esp_rfid_{hostname}_last_access",
            "state_topic": f"homeassistant/sensor/esp_rfid_{hostname}_last_access/state",
            "json_attributes_topic": f"homeassistant/sensor/esp_rfid_{hostname}_last_access/attributes",
            "icon": "mdi:account-clock",
            "device": device_info
        }
        
        # Device Online Binary Sensor
        online_config = {
            "name": f"{hostname} Online",
            "unique_id": f"esp_rfid_{hostname}_online",
            "state_topic": f"homeassistant/binary_sensor/esp_rfid_{hostname}_online/state",
            "json_attributes_topic": f"homeassistant/binary_sensor/esp_rfid_{hostname}_online/attributes",
            "payload_on": "ON", 
            "payload_off": "OFF",
            "device_class": "connectivity",
            "icon": "mdi:wifi",
            "device": device_info
        }
        
        # Unknown Card Event
        unknown_card_config = {
            "name": f"{hostname} Unknown Card",
            "unique_id": f"esp_rfid_{hostname}_unknown_card",
            "state_topic": f"homeassistant/sensor/esp_rfid_{hostname}_unknown_card/state",
            "json_attributes_topic": f"homeassistant/sensor/esp_rfid_{hostname}_unknown_card/attributes",
            "icon": "mdi:card-account-details-outline",
            "device": device_info
        }
        
        # Unlock Button
        unlock_button_config = {
            "name": f"{hostname} Unlock",
            "unique_id": f"esp_rfid_{hostname}_unlock_button",
            "command_topic": f"homeassistant/button/esp_rfid_{hostname}_unlock/cmd",
            "icon": "mdi:door-open",
            "device": device_info
        }
        
        # Access History Sensor
        access_history_config = {
            "name": f"{hostname} Access History",
            "unique_id": f"esp_rfid_{hostname}_access_history",
            "state_topic": f"homeassistant/sensor/esp_rfid_{hostname}_access_history/state",
            "json_attributes_topic": f"homeassistant/sensor/esp_rfid_{hostname}_access_history/attributes",
            "icon": "mdi:history",
            "device": device_info
        }
        
        try:
            # Send discovery messages
            self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_door_status/config", 
                                   json.dumps(door_status_config), retain=True)
            self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_last_access/config", 
                                   json.dumps(last_access_config), retain=True)
            self.mqtt_client.publish(f"homeassistant/binary_sensor/esp_rfid_{hostname}_online/config", 
                                   json.dumps(online_config), retain=True)
            self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_unknown_card/config", 
                                   json.dumps(unknown_card_config), retain=True)
            self.mqtt_client.publish(f"homeassistant/button/esp_rfid_{hostname}_unlock/config", 
                                   json.dumps(unlock_button_config), retain=True)
            self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_access_history/config", 
                                   json.dumps(access_history_config), retain=True)
            
            # Subscribe to button command topic
            self.mqtt_client.subscribe(f"homeassistant/button/esp_rfid_{hostname}_unlock/cmd")
            
            # Send initial state with attributes
            online_attributes = {
                "hostname": hostname,
                "ip_address": ip_address,
                "last_seen": datetime.now().isoformat(),
                "status": "online"
            }
            door_attributes = {
                "hostname": hostname,
                "ip_address": ip_address,
                "last_status_change": datetime.now().isoformat(),
                "status": "ready"
            }
            
            self.mqtt_client.publish(f"homeassistant/binary_sensor/esp_rfid_{hostname}_online/state", "ON")
            self.mqtt_client.publish(f"homeassistant/binary_sensor/esp_rfid_{hostname}_online/attributes", json.dumps(online_attributes))
            self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_door_status/state", "ready")
            self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_door_status/attributes", json.dumps(door_attributes))
            
            self.ha_discovery_sent.add(discovery_key)
            logger.info(f"Sent Home Assistant discovery for {hostname}")
            
        except Exception as e:
            logger.error(f"Failed to send HA discovery for {hostname}: {e}")
    
    def update_ha_sensors(self, hostname: str, event_type: str, data: Dict):
        """Update Home Assistant sensors with new data"""
        try:
            # Get device IP for attributes
            device_ip = self.connected_devices.get(hostname, {}).get('ip_address', 'unknown')
            
            if event_type == 'access':
                username = data.get('username', 'Unknown')
                uid = data.get('uid', '')
                access_type = data.get('access_type', 'Denied')
                door_name = data.get('door_name', hostname)
                timestamp = data.get('timestamp', datetime.now().isoformat())
                is_granted = "Denied" not in access_type
                
                # Update last access sensor
                state = f"{username}"
                last_access_attributes = {
                    "username": username,
                    "uid": uid,
                    "access_type": access_type,
                    "door_name": door_name,
                    "hostname": hostname,
                    "ip_address": device_ip,
                    "timestamp": timestamp,
                    "is_granted": is_granted,
                    "access_method": "rfid",
                    "friendly_name": f"{username} {access_type.lower()} access to {door_name}"
                }
                
                self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_last_access/state", state)
                self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_last_access/attributes", 
                                       json.dumps(last_access_attributes))
                
                # Update door status with detailed attributes
                door_status = "granted" if is_granted else "denied"
                door_status_attributes = {
                    "hostname": hostname,
                    "ip_address": device_ip,
                    "last_access_user": username,
                    "last_access_uid": uid,
                    "last_access_type": access_type,
                    "last_access_time": timestamp,
                    "door_name": door_name,
                    "status": door_status,
                    "last_status_change": timestamp
                }
                
                self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_door_status/state", door_status)
                self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_door_status/attributes", 
                                       json.dumps(door_status_attributes))
                
            elif event_type == 'unknown_card':
                uid = data.get('uid', '')
                timestamp = data.get('timestamp', datetime.now().isoformat())
                
                unknown_card_attributes = {
                    "uid": uid,
                    "timestamp": timestamp,
                    "hostname": hostname,
                    "ip_address": device_ip,
                    "scan_type": "unregistered_card",
                    "friendly_name": f"Unknown card {uid} scanned on {hostname}"
                }
                
                self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_unknown_card/state", f"Unknown: {uid}")
                self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_unknown_card/attributes", 
                                       json.dumps(unknown_card_attributes))
                
        except Exception as e:
            logger.error(f"Failed to update HA sensors for {hostname}: {e}")
    
    def handle_unlock_command(self, hostname: str):
        """Handle unlock command from Home Assistant button"""
        try:
            # Get device IP from database
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT ip_address FROM devices WHERE hostname = ?', (hostname,))
                row = cursor.fetchone()
                
                if not row:
                    logger.error(f"Device {hostname} not found for unlock command")
                    return
                
                device_ip = row['ip_address']
            
            # Send unlock command
            success = self.open_door(device_ip, hostname)
            
            if success:
                logger.info(f"Unlock command sent successfully to {hostname} ({device_ip})")
                
                # Update HA sensors to show door opened
                self.update_ha_sensors(hostname, 'access', {
                    'username': 'Home Assistant',
                    'uid': 'HA-BUTTON',
                    'access_type': 'Granted (Remote)',
                    'door_name': hostname,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Log to HA history
                self.log_access_to_ha_history(hostname, 'Home Assistant', 'HA-BUTTON', 'Granted (Remote)', 'ha_button')
                
                # Emit to web clients
                socketio.emit('access_event', {
                    'hostname': hostname,
                    'uid': 'HA-BUTTON',
                    'username': 'Home Assistant',
                    'access_type': 'Granted (Remote)',
                    'is_known': True,
                    'door_name': hostname,
                    'timestamp': datetime.now().isoformat()
                })
                
            else:
                logger.error(f"Failed to send unlock command to {hostname}")
                
        except Exception as e:
            logger.error(f"Error handling unlock command for {hostname}: {e}")
    
    def get_ha_user_from_rfid_user(self, rfid_username: str) -> Dict:
        """Map ESP-RFID username to Home Assistant user info"""
        # Simple mapping by username (can be enhanced later)
        return {
            'ha_username': rfid_username,
            'display_name': rfid_username.title(),
            'user_type': 'rfid_user'
        }
    
    def get_rfid_user_from_ha_user(self, ha_username: str) -> Dict:
        """Map Home Assistant username to ESP-RFID user info"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT username, device_hostname, acctype, valid_until
                FROM users 
                WHERE LOWER(username) = LOWER(?)
                LIMIT 1
            ''', (ha_username,))
            user = cursor.fetchone()
            
            if user:
                return {
                    'rfid_username': user['username'],
                    'device_hostname': user['device_hostname'],
                    'access_type': user['acctype'],
                    'valid_until': user['valid_until'],
                    'user_type': 'registered_user'
                }
            else:
                return {
                    'rfid_username': ha_username,
                    'device_hostname': None,
                    'access_type': 0,
                    'valid_until': 0,
                    'user_type': 'unknown_user'
                }
    
    def log_access_to_ha_history(self, hostname: str, username: str, uid: str, access_type: str, method: str = 'rfid'):
        """Log access event to Home Assistant history with user mapping"""
        try:
            # Get user mapping info
            if method == 'ha_button':
                user_info = self.get_rfid_user_from_ha_user(username)
                display_name = username
            else:
                user_info = self.get_ha_user_from_rfid_user(username)
                display_name = user_info['display_name']
            
            timestamp = datetime.now().isoformat()
            
            # Create detailed history entry
            history_state = f"{display_name} - {access_type}"
            history_attributes = {
                'username': username,
                'display_name': display_name,
                'uid': uid,
                'access_type': access_type,
                'access_method': method,
                'door_hostname': hostname,
                'timestamp': timestamp,
                'user_info': user_info,
                'friendly_message': f"{display_name} {access_type.lower()} access to {hostname} via {method.upper()}"
            }
            
            # Update HA history sensor
            self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_access_history/state", history_state)
            self.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_access_history/attributes", 
                                   json.dumps(history_attributes))
            
            # Create logbook entry via MQTT
            logbook_message = {
                'name': f'ESP-RFID Access - {hostname}',
                'message': f'{display_name} {access_type.lower()} access via {method.upper()}',
                'entity_id': f'sensor.esp_rfid_{hostname}_access_history',
                'domain': 'esp_rfid'
            }
            
            # Send to Home Assistant logbook topic (if configured)
            self.mqtt_client.publish('homeassistant/logbook/esp_rfid_access', json.dumps(logbook_message))
            
            logger.info(f"Logged HA history: {display_name} -> {hostname} ({access_type}) via {method}")
            
        except Exception as e:
            logger.error(f"Failed to log access to HA history: {e}")

# Global manager instance
manager = ESPRFIDManager()

# Flask routes
@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/api/devices')
def api_devices():
    """Get list of ESP-RFID devices"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT hostname, ip_address, last_seen, status, door_names
            FROM devices 
            ORDER BY last_seen DESC
        ''')
        devices = []
        for row in cursor.fetchall():
            devices.append({
                'hostname': row['hostname'],
                'ip_address': row['ip_address'],
                'last_seen': row['last_seen'],
                'status': row['status'],
                'door_names': json.loads(row['door_names'] or '[]')
            })
        
    return jsonify(devices)

@app.route('/api/devices/<hostname>', methods=['DELETE'])
def api_delete_device(hostname):
    """Delete offline device"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if device exists
        cursor.execute('SELECT * FROM devices WHERE hostname = ?', (hostname,))
        device = cursor.fetchone()
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        # Check if device is offline
        if device['status'] == 'online':
            return jsonify({'error': 'Cannot delete online device. Device must be offline.'}), 400
        
        # Delete associated users first
        cursor.execute('DELETE FROM users WHERE device_hostname = ?', (hostname,))
        users_deleted = cursor.rowcount
        
        # Delete device
        cursor.execute('DELETE FROM devices WHERE hostname = ?', (hostname,))
        
        conn.commit()
        
        logger.info(f"🗑️ Deleted offline device {hostname} and {users_deleted} associated users")
        
        return jsonify({
            'message': f'Device {hostname} deleted successfully',
            'users_deleted': users_deleted
        })

@app.route('/api/users')
def api_users():
    """Get list of users"""
    device = request.args.get('device', '')
    uid = request.args.get('uid', '')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        if uid:
            # Search by UID
            cursor.execute('''
                SELECT * FROM users WHERE uid = ? 
                ORDER BY created_at DESC
            ''', (uid,))
        elif device:
            # Filter by device
            cursor.execute('''
                SELECT * FROM users WHERE device_hostname = ? 
                ORDER BY created_at DESC
            ''', (device,))
        else:
            # Get all users
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row['id'],
                'uid': row['uid'],
                'username': row['username'],
                'device_hostname': row['device_hostname'],
                'acctype': row['acctype'],
                'valid_since': row['valid_since'],
                'valid_until': row['valid_until'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
    
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
def api_add_user():
    """Add new user to multiple devices"""
    data = request.get_json()
    
    uid = data.get('uid', '')
    username = data.get('username', '')
    devices = data.get('devices', [])  # Now expects list of device hostnames
    acctype = int(data.get('acctype', 1))
    valid_since = int(data.get('valid_since', 0))
    valid_until = int(data.get('valid_until', 0))
    
    # Support legacy single device format
    if not devices:
        device_hostname = data.get('device_hostname', '')
        if device_hostname:
            devices = [device_hostname]
    
    if not all([uid, username, devices]):
        return jsonify({'error': 'Missing required fields: uid, username, devices'}), 400
    
    results = []
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        for device_hostname in devices:
            # Get device IP
            cursor.execute('SELECT ip_address FROM devices WHERE hostname = ?', (device_hostname,))
            row = cursor.fetchone()
            if not row:
                results.append({'device': device_hostname, 'status': 'error', 'message': 'Device not found'})
                continue
            
            device_ip = row['ip_address']
            
            # Send MQTT command to device
            success = manager.add_user(device_ip, uid, username, acctype, valid_since, valid_until, device_hostname)
            
            if success:
                # Add to local database
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (uid, username, device_hostname, acctype, valid_since, valid_until, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (uid, username, device_hostname, acctype, valid_since, valid_until))
                
                results.append({'device': device_hostname, 'status': 'success', 'message': 'User added successfully'})
                
                logger.info(f"User {username} ({uid}) added to device {device_hostname} ({device_ip})")
            else:
                results.append({'device': device_hostname, 'status': 'error', 'message': 'Failed to send MQTT command'})
        
        conn.commit()
    
    # Check if any succeeded
    success_count = sum(1 for r in results if r['status'] == 'success')
    
    if success_count > 0:
        return jsonify({
            'message': f'User added to {success_count}/{len(devices)} devices', 
            'results': results
        })
    else:
        return jsonify({
            'error': 'Failed to add user to any device', 
            'results': results
        }), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    """Delete user from selected devices"""
    data = request.get_json() or {}
    selected_devices = data.get('devices', [])  # List of device hostnames to delete from
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # If no devices specified, get all devices for this user
        if not selected_devices:
            cursor.execute('SELECT DISTINCT device_hostname FROM users WHERE uid = ?', (user['uid'],))
            selected_devices = [row['device_hostname'] for row in cursor.fetchall()]
        
        results = []
        
        for device_hostname in selected_devices:
            # Get device IP
            cursor.execute('SELECT ip_address, status FROM devices WHERE hostname = ?', (device_hostname,))
            device = cursor.fetchone()
            
            if not device:
                results.append({'device': device_hostname, 'status': 'error', 'message': 'Device not found'})
                continue
            
            # Send MQTT command only if device is online
            if device['status'] == 'online':
                success = manager.delete_user(device['ip_address'], user['uid'], device_hostname)
                
                if success:
                    # Remove from local database
                    cursor.execute('DELETE FROM users WHERE uid = ? AND device_hostname = ?', (user['uid'], device_hostname))
                    results.append({'device': device_hostname, 'status': 'success', 'message': 'User deleted successfully'})
                else:
                    results.append({'device': device_hostname, 'status': 'error', 'message': 'Failed to send MQTT command'})
            else:
                # Device is offline, just remove from database
                cursor.execute('DELETE FROM users WHERE uid = ? AND device_hostname = ?', (user['uid'], device_hostname))
                results.append({'device': device_hostname, 'status': 'success', 'message': 'User removed from offline device'})
        
        conn.commit()
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        
        return jsonify({
            'message': f'User deletion completed: {success_count}/{len(selected_devices)} devices',
            'results': results
        })

@app.route('/api/users/<int:user_id>/devices')
def api_get_user_devices(user_id):
    """Get all devices where this user exists"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get all devices where this user exists
        cursor.execute('''
            SELECT DISTINCT u.device_hostname, d.ip_address, d.status, d.last_seen
            FROM users u
            LEFT JOIN devices d ON u.device_hostname = d.hostname
            WHERE u.uid = ?
            ORDER BY u.device_hostname
        ''', (user['uid'],))
        
        user_devices = []
        for row in cursor.fetchall():
            user_devices.append({
                'hostname': row['device_hostname'],
                'ip_address': row['ip_address'],
                'status': row['status'],
                'last_seen': row['last_seen']
            })
        
        return jsonify({
            'user': {
                'id': user['id'],
                'uid': user['uid'],
                'username': user['username']
            },
            'devices': user_devices
        })

@app.route('/api/access-logs')
def api_access_logs():
    """Get access logs (newest first)"""
    device = request.args.get('device', '')
    limit = int(request.args.get('limit', 100))
    
    with get_db() as conn:
        cursor = conn.cursor()
        if device:
            cursor.execute('''
                SELECT * FROM access_logs 
                WHERE device_hostname = ? 
                ORDER BY id DESC, timestamp DESC 
                LIMIT ?
            ''', (device, limit))
        else:
            cursor.execute('''
                SELECT * FROM access_logs 
                ORDER BY id DESC, timestamp DESC 
                LIMIT ?
            ''', (limit,))
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'id': row['id'],
                'device_hostname': row['device_hostname'],
                'uid': row['uid'],
                'username': row['username'],
                'access_type': row['access_type'],
                'is_known': row['is_known'],
                'door_name': row['door_name'],
                'timestamp': row['timestamp']
            })
    
    return jsonify(logs)

@app.route('/api/card-registrations')
def api_card_registrations():
    """Get pending card registrations"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM card_registrations 
            WHERE status = 'pending' 
            ORDER BY registered_at DESC
        ''')
        
        registrations = []
        for row in cursor.fetchall():
            registrations.append({
                'id': row['id'],
                'uid': row['uid'],
                'device_hostname': row['device_hostname'],
                'registered_at': row['registered_at'],
                'status': row['status']
            })
    
    return jsonify(registrations)

@app.route('/api/card-registrations/<int:registration_id>', methods=['POST'])
def api_complete_card_registration(registration_id):
    """Complete card registration by adding user"""
    data = request.get_json()
    username = data.get('username', '')
    acctype = int(data.get('acctype', 1))
    valid_since = int(data.get('valid_since', 0))
    valid_until = int(data.get('valid_until', 0))
    
    if not username:
        return jsonify({'error': 'Username required'}), 400
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM card_registrations WHERE id = ?', (registration_id,))
        registration = cursor.fetchone()
        
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404
        
        uid = registration['uid']
        device_hostname = registration['device_hostname']
        
        # Get device IP
        cursor.execute('SELECT ip_address FROM devices WHERE hostname = ?', (device_hostname,))
        device = cursor.fetchone()
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        device_ip = device['ip_address']
        
        # Add user via MQTT
        success = manager.add_user(device_ip, uid, username, acctype, valid_since, valid_until)
        
        if success:
            # Add to users table
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (uid, username, device_hostname, acctype, valid_since, valid_until)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (uid, username, device_hostname, acctype, valid_since, valid_until))
            
            # Mark registration as completed
            cursor.execute('''
                UPDATE card_registrations 
                SET status = 'completed' 
                WHERE id = ?
            ''', (registration_id,))
            
            conn.commit()
            return jsonify({'message': 'User registered successfully'})
        else:
            return jsonify({'error': 'Failed to register user'}), 500

@app.route('/api/doors/open', methods=['POST'])
def api_open_door():
    """Open door"""
    data = request.get_json()
    device_hostname = data.get('device_hostname', '')
    
    if not device_hostname:
        return jsonify({'error': 'Device hostname required'}), 400
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT ip_address FROM devices WHERE hostname = ?', (device_hostname,))
        device = cursor.fetchone()
        
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        success = manager.open_door(device['ip_address'], device_hostname)
        
        if success:
            return jsonify({'message': 'Door opened successfully'})
        else:
            return jsonify({'error': 'Failed to open door'}), 500

@app.route('/api/devices/<hostname>/sync', methods=['POST'])
def api_sync_device_users(hostname):
    """Sync users from ESP-RFID device"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT ip_address FROM devices WHERE hostname = ?', (hostname,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Device not found'}), 404
        device_ip = row['ip_address']
    
    success = manager.get_user_list(device_ip)
    
    if success:
        return jsonify({'message': 'User sync requested successfully'})
    else:
        return jsonify({'error': 'Failed to request user sync'}), 500

@app.route('/api/users/bulk-assign', methods=['POST']) 
def api_bulk_assign_user():
    """Assign user to multiple devices"""
    data = request.get_json()
    uid = data.get('uid', '')
    username = data.get('username', '')
    devices = data.get('devices', [])
    acctype = int(data.get('acctype', 1))
    valid_since = int(data.get('valid_since', 0))
    valid_until = int(data.get('valid_until', 0))
    
    if not all([uid, username, devices]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    results = []
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        for device_hostname in devices:
            # Get device IP
            cursor.execute('SELECT ip_address FROM devices WHERE hostname = ?', (device_hostname,))
            row = cursor.fetchone()
            if not row:
                results.append({'device': device_hostname, 'status': 'error', 'message': 'Device not found'})
                continue
            
            device_ip = row['ip_address']
            
            # Send MQTT command
            success = manager.add_user(device_ip, uid, username, acctype, valid_since, valid_until)
            
            if success:
                # Add to local database
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (uid, username, device_hostname, acctype, valid_since, valid_until, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (uid, username, device_hostname, acctype, valid_since, valid_until))
                results.append({'device': device_hostname, 'status': 'success', 'message': 'User added'})
            else:
                results.append({'device': device_hostname, 'status': 'error', 'message': 'Failed to add user'})
        
        conn.commit()
    
    return jsonify({'results': results})

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def api_edit_user(user_id):
    """Edit existing user"""
    data = request.get_json()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get updated values or keep existing
        username = data.get('username', user['username'])
        acctype = int(data.get('acctype', user['acctype']))
        valid_since = int(data.get('valid_since', user['valid_since']))
        valid_until = int(data.get('valid_until', user['valid_until']))
        
        # Get device IP
        cursor.execute('SELECT ip_address FROM devices WHERE hostname = ?', (user['device_hostname'],))
        device = cursor.fetchone()
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        device_ip = device['ip_address']
        
        # Send updated user info via MQTT
        success = manager.add_user(device_ip, user['uid'], username, acctype, valid_since, valid_until)
        
        if success:
            # Update local database
            cursor.execute('''
                UPDATE users 
                SET username = ?, acctype = ?, valid_since = ?, valid_until = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (username, acctype, valid_since, valid_until, user_id))
            conn.commit()
            return jsonify({'message': 'User updated successfully'})
        else:
            return jsonify({'error': 'Failed to update user'}), 500

@app.route('/api/homeassistant/users')
def api_homeassistant_users():
    """Get Home Assistant users (enhanced implementation)"""
    # Try to get real HA users from database or existing ESP-RFID users
    users = []
    
    # Get unique usernames from ESP-RFID database  
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT username FROM users ORDER BY username')
        esp_rfid_users = cursor.fetchall()
        
        for user in esp_rfid_users:
            username = user['username']
            users.append({
                'id': username.lower(),
                'name': username.title(),
                'username': username,
                'source': 'esp_rfid'
            })
    
    # Add some common HA system users if not already present
    system_users = [
        {'id': 'admin', 'name': 'Administrator', 'username': 'admin', 'source': 'system'},
        {'id': 'homeassistant', 'name': 'Home Assistant', 'username': 'homeassistant', 'source': 'system'},
        {'id': 'guest', 'name': 'Guest User', 'username': 'guest', 'source': 'system'},
    ]
    
    existing_usernames = {u['username'].lower() for u in users}
    for sys_user in system_users:
        if sys_user['username'].lower() not in existing_usernames:
            users.append(sys_user)
    
    # Sort by name
    users.sort(key=lambda x: x['name'])
    
    return jsonify(users)

@app.route('/api/homeassistant/config')
def api_homeassistant_config():
    """Generate Home Assistant configuration for ESP-RFID devices"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT hostname, ip_address, status, last_seen FROM devices ORDER BY hostname')
        devices = cursor.fetchall()
    
    # Generate YAML configuration
    config_yaml = """# ESP-RFID Manager - Home Assistant Configuration
# Add this to your configuration.yaml

# MQTT Sensors for ESP-RFID devices
mqtt:
  sensor:
"""
    
    for device in devices:
        hostname = device['hostname']
        config_yaml += f"""
    # {hostname} - Door Status
    - name: "ESP-RFID {hostname} Door Status"
      state_topic: "homeassistant/sensor/esp_rfid_{hostname}_door_status/state"
      icon: "mdi:door"
      
    # {hostname} - Last Access
    - name: "ESP-RFID {hostname} Last Access"
      state_topic: "homeassistant/sensor/esp_rfid_{hostname}_last_access/state"
      json_attributes_topic: "homeassistant/sensor/esp_rfid_{hostname}_last_access/attributes"
      icon: "mdi:account-clock"
      
    # {hostname} - Unknown Card
    - name: "ESP-RFID {hostname} Unknown Card"
      state_topic: "homeassistant/sensor/esp_rfid_{hostname}_unknown_card/state"
      json_attributes_topic: "homeassistant/sensor/esp_rfid_{hostname}_unknown_card/attributes"
      icon: "mdi:card-account-details-outline"
"""
    
    config_yaml += """
  binary_sensor:
"""
    
    for device in devices:
        hostname = device['hostname']
        config_yaml += f"""
    # {hostname} - Online Status
    - name: "ESP-RFID {hostname} Online"
      state_topic: "homeassistant/binary_sensor/esp_rfid_{hostname}_online/state"
      payload_on: "ON"
      payload_off: "OFF"
      device_class: connectivity
      icon: "mdi:wifi"
"""

    return Response(config_yaml, mimetype='text/plain')

@app.route('/api/homeassistant/dashboard')
def api_homeassistant_dashboard():
    """Get available dashboard card templates"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT hostname, ip_address, status, last_seen FROM devices ORDER BY hostname')
        devices = cursor.fetchall()
    
    # Return card templates instead of YAML
    templates = {
        'device_cards': [],
        'overview_card': {
            'type': 'markdown',
            'content': '# 🚪 ESP-RFID Access Control\nMonitor and control all your ESP-RFID devices'
        },
        'access_history_card': {
            'type': 'history-graph',
            'title': 'Recent Access History',
            'hours_to_show': 24,
            'refresh_interval': 30,
            'entities': []
        },
        'unknown_cards_card': {
            'type': 'entities',
            'title': '🔍 Unknown Cards Detected',
            'show_header_toggle': False,
            'entities': []
        }
    }
    
    for device in devices:
        hostname = device['hostname']
        status = device['status']
        
        # Individual device card
        device_card = {
            'type': 'custom:button-card',
            'entity': f'binary_sensor.esp_rfid_{hostname}_online',
            'name': hostname,
            'show_state': False,
            'show_icon': True,
            'icon': 'mdi:door',
            'tap_action': {'action': 'more-info'},
            'styles': {
                'card': ['height: 120px'],
                'name': ['font-size: 14px', 'font-weight: bold'],
                'icon': [f'color: {"green" if status == "online" else "red"}']
            },
            'custom_fields': {
                'status': f'<span style="font-size: 12px;">{status.title()}</span>',
                'last_access': f'<span style="font-size: 10px; color: gray;">Last: Unknown</span>'
            },
            'hostname': hostname,
            'selectable': True
        }
        
        templates['device_cards'].append(device_card)
        templates['access_history_card']['entities'].append(f'sensor.esp_rfid_{hostname}_last_access')
        templates['unknown_cards_card']['entities'].append(f'sensor.esp_rfid_{hostname}_unknown_card')

    return jsonify(templates)

@app.route('/api/homeassistant/card-template', methods=['POST'])
def api_generate_card_template():
    """Generate custom card template for selected devices"""
    data = request.get_json()
    selected_devices = data.get('devices', [])
    card_type = data.get('type', 'grid')
    
    if not selected_devices:
        return jsonify({'error': 'No devices selected'}), 400
    
    # Generate card configuration based on selected devices
    if card_type == 'grid':
        card_config = {
            'type': 'grid',
            'square': True,
            'columns': min(len(selected_devices), 3),
            'cards': []
        }
        
        for hostname in selected_devices:
            device_card = {
                'type': 'custom:button-card',
                'entity': f'binary_sensor.esp_rfid_{hostname}_online',
                'name': hostname,
                'show_state': False,
                'show_icon': True,
                'icon': 'mdi:door',
                'tap_action': {'action': 'more-info'},
                'styles': {
                    'card': ['height: 120px'],
                    'name': ['font-size: 14px', 'font-weight: bold']
                }
            }
            card_config['cards'].append(device_card)
    
    elif card_type == 'entities':
        card_config = {
            'type': 'entities',
            'title': 'ESP-RFID Devices',
            'entities': []
        }
        
        for hostname in selected_devices:
            card_config['entities'].extend([
                f'binary_sensor.esp_rfid_{hostname}_online',
                f'sensor.esp_rfid_{hostname}_last_access',
                f'button.esp_rfid_{hostname}_unlock'
            ])
    
    elif card_type == 'history':
        card_config = {
            'type': 'history-graph',
            'title': 'Access History',
            'hours_to_show': 24,
            'entities': [f'sensor.esp_rfid_{hostname}_last_access' for hostname in selected_devices]
        }
    
    return jsonify(card_config)

@app.route('/api/homeassistant/user-doors')
def api_homeassistant_user_doors():
    """Get doors that the current Home Assistant user has access to"""
    # Get Home Assistant user info from headers (if available)
    ha_user = request.headers.get('X-Hassio-User', 'unknown')
    ha_user_id = request.headers.get('X-Hassio-User-Id', 'unknown')
    
    # For demo purposes, we'll also accept query parameter
    username = request.args.get('username', ha_user)
    
    logger.info(f"Checking door access for HA user: {username} (ID: {ha_user_id})")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get all devices that have this user
        cursor.execute('''
            SELECT DISTINCT d.hostname, d.ip_address, d.status, d.last_seen, u.username, u.acctype, u.valid_until
            FROM devices d
            JOIN users u ON d.hostname = u.device_hostname
            WHERE LOWER(u.username) = LOWER(?) AND u.acctype > 0
            ORDER BY d.hostname
        ''', (username,))
        user_doors = cursor.fetchall()
        
        # Get all available devices for comparison
        cursor.execute('SELECT hostname, ip_address, status, last_seen FROM devices ORDER BY hostname')
        all_devices = cursor.fetchall()
    
    # Format response
    result = {
        'user': {
            'username': username,
            'ha_user_id': ha_user_id,
            'total_doors_accessible': len(user_doors)
        },
        'accessible_doors': [],
        'all_doors': []
    }
    
    # Add accessible doors with user info
    for door in user_doors:
        # Check if access is still valid
        is_valid = True
        if door['valid_until'] > 0:
            valid_until_date = datetime.fromtimestamp(door['valid_until'])
            is_valid = valid_until_date > datetime.now()
        
        result['accessible_doors'].append({
            'hostname': door['hostname'],
            'ip_address': door['ip_address'],
            'status': door['status'],
            'last_seen': door['last_seen'],
            'username': door['username'],
            'access_type': door['acctype'],
            'is_valid': is_valid,
            'ha_entity_button': f"button.esp_rfid_{door['hostname']}_unlock_door",
            'ha_entity_status': f"binary_sensor.esp_rfid_{door['hostname']}_online"
        })
    
    # Add all doors for context
    for device in all_devices:
        has_access = any(d['hostname'] == device['hostname'] for d in user_doors)
        result['all_doors'].append({
            'hostname': device['hostname'],
            'ip_address': device['ip_address'],
            'status': device['status'],
            'last_seen': device['last_seen'],
            'has_access': has_access
        })
    
    return jsonify(result)

@app.route('/api/homeassistant/access-history')
def api_homeassistant_access_history():
    """Get access history for Home Assistant with user mapping"""
    username = request.args.get('username', '')
    device_hostname = request.args.get('device', '')
    limit = int(request.args.get('limit', 50))
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Build query based on filters
        query = '''
            SELECT device_hostname, uid, username, access_type, door_name, timestamp, raw_data
            FROM access_logs 
            WHERE 1=1
        '''
        params = []
        
        if username:
            query += ' AND LOWER(username) = LOWER(?)'
            params.append(username)
        
        if device_hostname:
            query += ' AND device_hostname = ?'
            params.append(device_hostname)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        logs = cursor.fetchall()
    
    # Format for Home Assistant consumption
    history_entries = []
    
    for log in logs:
        # Map ESP-RFID user to HA user
        user_info = manager.get_ha_user_from_rfid_user(log['username'])
        
        # Determine access method from raw_data
        raw_data = json.loads(log['raw_data']) if log['raw_data'] else {}
        
        # Check if it was HA button access
        method = 'ha_button' if log['uid'] == 'HA-BUTTON' else 'rfid'
        
        entry = {
            'timestamp': log['timestamp'],
            'hostname': log['device_hostname'],
            'door_name': log['door_name'] or log['device_hostname'],
            'username': log['username'],
            'display_name': user_info['display_name'],
            'uid': log['uid'],
            'access_type': log['access_type'],
            'access_method': method,
            'ha_entity': f"sensor.esp_rfid_{log['device_hostname']}_access_history",
            'logbook_message': f"{user_info['display_name']} {log['access_type'].lower()} access to {log['door_name'] or log['device_hostname']} via {method.upper()}",
            'user_info': user_info
        }
        
        history_entries.append(entry)
    
    return jsonify({
        'total_entries': len(history_entries),
        'username_filter': username,
        'device_filter': device_hostname,
        'entries': history_entries
    })

# SocketIO events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Web client connected')
    emit('connected', {'data': 'Connected to ESP-RFID Manager'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Web client disconnected')

@socketio.on('start_card_detection')
def handle_start_card_detection():
    """Start card detection for Add User modal"""
    manager.card_detection_active = True
    logger.info("🔍 Card detection STARTED - Add User modal opened")
    emit('card_detection_status', {'active': True, 'message': 'Card detection enabled - scan a card'})

@socketio.on('stop_card_detection') 
def handle_stop_card_detection():
    """Stop card detection when Add User modal closes"""
    manager.card_detection_active = False
    logger.info("🔍 Card detection STOPPED - Add User modal closed")
    emit('card_detection_status', {'active': False, 'message': 'Card detection disabled'})

# Cleanup task for offline devices
def cleanup_offline_devices():
    """Mark devices as offline if not seen for 45 seconds (3x heartbeat)"""
    cutoff_time = datetime.now() - timedelta(seconds=45)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get devices that will be marked offline
        cursor.execute('''
            SELECT hostname FROM devices 
            WHERE last_seen < ? AND status = 'online'
        ''', (cutoff_time,))
        offline_devices = cursor.fetchall()
        
        # Mark devices as offline
        cursor.execute('''
            UPDATE devices 
            SET status = 'offline' 
            WHERE last_seen < ? AND status = 'online'
        ''', (cutoff_time,))
        conn.commit()
    
    # Update Home Assistant sensors for offline devices
    for device in offline_devices:
        hostname = device['hostname']
        if hostname in manager.connected_devices:
            manager.connected_devices[hostname]['status'] = 'offline'
        
        try:
            timestamp = datetime.now().isoformat()
            device_ip = manager.connected_devices.get(hostname, {}).get('ip_address', 'unknown')
            
            # Offline sensor attributes
            offline_attributes = {
                "hostname": hostname,
                "ip_address": device_ip,
                "last_seen": timestamp,
                "status": "offline",
                "status_change": timestamp,
                "previous_status": "online"
            }
            
            # Door status attributes for offline
            door_offline_attributes = {
                "hostname": hostname,
                "ip_address": device_ip,
                "last_status_change": timestamp,
                "status": "offline",
                "device_online": False
            }
            
            manager.mqtt_client.publish(f"homeassistant/binary_sensor/esp_rfid_{hostname}_online/state", "OFF")
            manager.mqtt_client.publish(f"homeassistant/binary_sensor/esp_rfid_{hostname}_online/attributes", json.dumps(offline_attributes))
            manager.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_door_status/state", "offline")
            manager.mqtt_client.publish(f"homeassistant/sensor/esp_rfid_{hostname}_door_status/attributes", json.dumps(door_offline_attributes))
            logger.info(f"{hostname} Door Status changed to offline")
        except Exception as e:
            logger.error(f"Failed to update HA sensors for offline device {hostname}: {e}")

if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Start scheduler for cleanup tasks
    manager.scheduler.add_job(
        func=cleanup_offline_devices,
        trigger="interval",
        minutes=1,
        id='cleanup_offline_devices'
    )
    manager.scheduler.start()
    
    # Start Flask-SocketIO server
    logger.info(f"Starting ESP-RFID Manager on port {WEB_PORT}")
    socketio.run(app, 
                host='0.0.0.0', 
                port=WEB_PORT, 
                debug=False,
                allow_unsafe_werkzeug=True) 