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

from flask import Flask, render_template, request, jsonify, redirect, url_for
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
            client.subscribe(f"{MQTT_TOPIC}/+/send")
            client.subscribe(f"{MQTT_TOPIC}/send")  # For single device setup
            logger.info(f"Subscribed to {MQTT_TOPIC}/+/send and {MQTT_TOPIC}/send")
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        logger.warning("Disconnected from MQTT broker")
        
    def on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            logger.debug(f"Received MQTT message: {topic} -> {payload}")
            
            # Extract device info from topic or payload
            device_hostname = payload.get('hostname', 'unknown')
            device_ip = payload.get('ip', '')
            
            # Update device status
            self.update_device_status(device_hostname, device_ip)
            
            # Handle different message types
            msg_type = payload.get('type', '')
            cmd = payload.get('cmd', '')
            
            if msg_type == 'boot':
                self.handle_boot_message(payload)
            elif msg_type == 'heartbeat':
                self.handle_heartbeat_message(payload)  
            elif msg_type == 'access':
                self.handle_access_message(payload)
            elif msg_type in ['INFO', 'WARN', 'ERRO']:
                self.handle_event_message(payload)
            elif cmd == 'userfile':
                self.handle_userfile_message(payload)
            elif payload.get('uid') and not msg_type:  # Card scan for registration
                self.handle_card_scan(payload)
                
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
    
    def handle_event_message(self, payload: Dict):
        """Handle system event message"""
        hostname = payload.get('hostname', '')
        event_type = payload.get('type', 'INFO')
        source = payload.get('src', '')
        description = payload.get('desc', '')
        data = payload.get('data', '')
        
        self.log_event(hostname, event_type, source, description, data)
    
    def handle_userfile_message(self, payload: Dict):
        """Handle user file message from device"""
        # This is response to getuserlist command
        uid = payload.get('uid', '')
        username = payload.get('user', '')
        acctype = payload.get('acctype', 1)
        valid_since = payload.get('validsince', 0)
        valid_until = payload.get('validuntil', 0)
        
        # We need to determine which device this came from
        # This might need to be tracked differently
        logger.info(f"Received user file: {username} ({uid})")
    
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
    
    def send_mqtt_command(self, device_ip: str, command: Dict):
        """Send command to ESP-RFID device via MQTT"""
        command['doorip'] = device_ip
        topic = f"{MQTT_TOPIC}/cmd"
        
        try:
            self.mqtt_client.publish(topic, json.dumps(command))
            logger.info(f"Sent MQTT command to {device_ip}: {command}")
            return True
        except Exception as e:
            logger.error(f"Failed to send MQTT command: {e}")
            return False
    
    def add_user(self, device_ip: str, uid: str, username: str, acctype: int = 1, 
                 valid_since: int = 0, valid_until: int = 0) -> bool:
        """Add user to ESP-RFID device"""
        command = {
            'cmd': 'adduser',
            'uid': uid,
            'user': username,
            'acctype': str(acctype),
            'validsince': str(valid_since),
            'validuntil': str(valid_until)
        }
        return self.send_mqtt_command(device_ip, command)
    
    def delete_user(self, device_ip: str, uid: str) -> bool:
        """Delete user from ESP-RFID device"""
        command = {
            'cmd': 'deletuid',
            'uid': uid
        }
        return self.send_mqtt_command(device_ip, command)
    
    def open_door(self, device_ip: str) -> bool:
        """Open door on ESP-RFID device"""
        command = {
            'cmd': 'opendoor'
        }
        return self.send_mqtt_command(device_ip, command)
    
    def get_user_list(self, device_ip: str) -> bool:
        """Request user list from ESP-RFID device"""
        command = {
            'cmd': 'getuserlist'
        }
        return self.send_mqtt_command(device_ip, command)

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

@app.route('/api/users')
def api_users():
    """Get list of users"""
    device = request.args.get('device', '')
    
    with get_db() as conn:
        cursor = conn.cursor()
        if device:
            cursor.execute('''
                SELECT * FROM users WHERE device_hostname = ? 
                ORDER BY created_at DESC
            ''', (device,))
        else:
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
    """Add new user"""
    data = request.get_json()
    
    uid = data.get('uid', '')
    username = data.get('username', '')
    device_hostname = data.get('device_hostname', '')
    acctype = int(data.get('acctype', 1))
    valid_since = int(data.get('valid_since', 0))
    valid_until = int(data.get('valid_until', 0))
    
    if not all([uid, username, device_hostname]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Get device IP
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT ip_address FROM devices WHERE hostname = ?', (device_hostname,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Device not found'}), 404
        device_ip = row['ip_address']
    
    # Send MQTT command to device
    success = manager.add_user(device_ip, uid, username, acctype, valid_since, valid_until)
    
    if success:
        # Add to local database
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (uid, username, device_hostname, acctype, valid_since, valid_until, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (uid, username, device_hostname, acctype, valid_since, valid_until))
            conn.commit()
        
        return jsonify({'message': 'User added successfully'})
    else:
        return jsonify({'error': 'Failed to add user'}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    """Delete user"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get device IP
        cursor.execute('SELECT ip_address FROM devices WHERE hostname = ?', (user['device_hostname'],))
        device = cursor.fetchone()
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        # Send MQTT command
        success = manager.delete_user(device['ip_address'], user['uid'])
        
        if success:
            # Remove from local database
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            return jsonify({'message': 'User deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete user'}), 500

@app.route('/api/access-logs')
def api_access_logs():
    """Get access logs"""
    device = request.args.get('device', '')
    limit = int(request.args.get('limit', 100))
    
    with get_db() as conn:
        cursor = conn.cursor()
        if device:
            cursor.execute('''
                SELECT * FROM access_logs 
                WHERE device_hostname = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (device, limit))
        else:
            cursor.execute('''
                SELECT * FROM access_logs 
                ORDER BY timestamp DESC 
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
        
        success = manager.open_door(device['ip_address'])
        
        if success:
            return jsonify({'message': 'Door opened successfully'})
        else:
            return jsonify({'error': 'Failed to open door'}), 500

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

# Cleanup task for offline devices
def cleanup_offline_devices():
    """Mark devices as offline if not seen for 5 minutes"""
    cutoff_time = datetime.now() - timedelta(minutes=5)
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE devices 
            SET status = 'offline' 
            WHERE last_seen < ? AND status = 'online'
        ''', (cutoff_time,))
        conn.commit()

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