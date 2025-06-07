# Home Assistant интеграција за ESP-RFID Manager

Овој документ објаснува како да интегрирате ESP-RFID Manager со Home Assistant за создавање на сензори, автоматизации и картички за dashboard-от.

## MQTT сензори

Додајте ги овие сензори во вашиот `configuration.yaml`:

### Статус на уредите

```yaml
mqtt:
  sensor:
    - name: "ESP-RFID Door Status"
      state_topic: "/rfid/send"
      value_template: >
        {% if value_json.type == 'heartbeat' %}
          online
        {% else %}
          {{ states('sensor.esp_rfid_door_status') }}
        {% endif %}
      json_attributes_topic: "/rfid/send"
      json_attributes_template: >
        {% if value_json.hostname is defined %}
          {
            "hostname": "{{ value_json.hostname }}",
            "ip": "{{ value_json.ip }}",
            "uptime": "{{ value_json.uptime }}",
            "last_seen": "{{ now().isoformat() }}"
          }
        {% endif %}

    - name: "ESP-RFID Last Access"
      state_topic: "/rfid/send"
      value_template: >
        {% if value_json.type == 'access' %}
          {{ value_json.username }}
        {% else %}
          {{ states('sensor.esp_rfid_last_access') }}
        {% endif %}
      json_attributes_topic: "/rfid/send"
      json_attributes_template: >
        {% if value_json.type == 'access' %}
          {
            "uid": "{{ value_json.uid }}",
            "access": "{{ value_json.access }}",
            "isKnown": {{ value_json.isKnown }},
            "hostname": "{{ value_json.hostname }}",
            "doorName": "{{ value_json.doorName }}",
            "time": "{{ value_json.time }}"
          }
        {% endif %}

  binary_sensor:
    - name: "ESP-RFID Device Online"
      state_topic: "/rfid/send"
      value_template: >
        {% if value_json.type == 'heartbeat' %}
          ON
        {% elif value_json.type == 'boot' %}
          ON
        {% else %}
          {{ states('binary_sensor.esp_rfid_device_online') }}
        {% endif %}
      device_class: connectivity
      off_delay: 300  # 5 минути

    - name: "ESP-RFID Door Open"
      state_topic: "/rfid/io/door"
      payload_on: "OPEN"
      payload_off: "CLOSED"
      device_class: door

    - name: "ESP-RFID Access Granted"
      state_topic: "/rfid/send"
      value_template: >
        {% if value_json.type == 'access' and value_json.isKnown == 'true' and value_json.access != 'Denied' %}
          ON
        {% else %}
          OFF
        {% endif %}
      auto_off: 5  # Се исклучува по 5 секунди
```

## Автоматизации

### Известување при непознат пристап

```yaml
automation:
  - alias: "ESP-RFID Unknown Card Alert"
    trigger:
      - platform: mqtt
        topic: "/rfid/send"
    condition:
      - condition: template
        value_template: >
          {{ trigger.payload_json.type == 'access' and 
             trigger.payload_json.isKnown == 'false' }}
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🚨 Unknown Card Detected"
          message: >
            Unknown card {{ trigger.payload_json.uid }} was used on 
            {{ trigger.payload_json.hostname }} at {{ now().strftime('%H:%M') }}
          data:
            actions:
              - action: "REGISTER_CARD"
                title: "Register Card"
                uri: "http://homeassistant.local:8080"

  - alias: "ESP-RFID Access Granted Log"
    trigger:
      - platform: mqtt
        topic: "/rfid/send"
    condition:
      - condition: template
        value_template: >
          {{ trigger.payload_json.type == 'access' and 
             trigger.payload_json.isKnown == 'true' and
             trigger.payload_json.access != 'Denied' }}
    action:
      - service: logbook.log
        data:
          name: "ESP-RFID Access"
          message: >
            {{ trigger.payload_json.username }} accessed 
            {{ trigger.payload_json.doorName }} on 
            {{ trigger.payload_json.hostname }}

  - alias: "ESP-RFID Device Offline Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.esp_rfid_device_online
        to: 'off'
        for: '00:05:00'
    action:
      - service: notify.persistent_notification
        data:
          title: "ESP-RFID Device Offline"
          message: >
            ESP-RFID device has been offline for more than 5 minutes.
            Last seen: {{ state_attr('sensor.esp_rfid_door_status', 'last_seen') }}
```

## Dashboard картички

### Lovelace картички за ESP-RFID

```yaml
type: vertical-stack
cards:
  - type: entities
    title: ESP-RFID Status
    entities:
      - entity: binary_sensor.esp_rfid_device_online
        name: Device Status
      - entity: sensor.esp_rfid_door_status
        name: Device Info
      - entity: binary_sensor.esp_rfid_door_open
        name: Door Status
      - entity: sensor.esp_rfid_last_access
        name: Last Access

  - type: iframe
    url: "http://homeassistant.local:8080"
    title: "ESP-RFID Manager"
    aspect_ratio: 75%

  - type: button
    entity: script.esp_rfid_open_door
    name: Open Door
    icon: mdi:door-open
    tap_action:
      action: call-service
      service: script.esp_rfid_open_door

  - type: history-graph
    title: Access History
    entities:
      - binary_sensor.esp_rfid_access_granted
      - binary_sensor.esp_rfid_door_open
    hours_to_show: 24
```

## Скрипти

### Отворање врата

```yaml
script:
  esp_rfid_open_door:
    alias: "Open ESP-RFID Door"
    sequence:
      - service: mqtt.publish
        data:
          topic: "/rfid/cmd"
          payload: >
            {
              "cmd": "opendoor",
              "doorip": "{{ state_attr('sensor.esp_rfid_door_status', 'ip') }}"
            }
      - service: notify.persistent_notification
        data:
          title: "Door Opened"
          message: "ESP-RFID door was opened remotely"

  esp_rfid_add_user:
    alias: "Add ESP-RFID User"
    fields:
      username:
        description: "Username"
        example: "John Doe"
      uid:
        description: "Card UID"
        example: "1234567890"
      device_ip:
        description: "Device IP"
        example: "192.168.1.100"
      valid_until:
        description: "Valid until (unix timestamp)"
        example: "1735689600"
    sequence:
      - service: mqtt.publish
        data:
          topic: "/rfid/cmd"
          payload: >
            {
              "cmd": "adduser",
              "doorip": "{{ device_ip }}",
              "uid": "{{ uid }}",
              "user": "{{ username }}",
              "acctype": "1",
              "validsince": "0",
              "validuntil": "{{ valid_until | default('0') }}"
            }
```

## Сензори за статистики

```yaml
sensor:
  - platform: template
    sensors:
      esp_rfid_daily_access_count:
        friendly_name: "Daily Access Count"
        value_template: >
          {{ states.sensor.esp_rfid_last_access.attributes.get('access_count_today', 0) }}
        icon_template: mdi:counter

  - platform: sql
    db_url: "sqlite:////config/esp_rfid.db"
    queries:
      - name: "ESP-RFID Access Count Today"
        query: >
          SELECT COUNT(*) as count 
          FROM access_logs 
          WHERE DATE(timestamp) = DATE('now') 
          AND is_known = 1
        column: "count"

      - name: "ESP-RFID Most Active User"
        query: >
          SELECT username 
          FROM access_logs 
          WHERE DATE(timestamp) = DATE('now') 
          AND is_known = 1 
          GROUP BY username 
          ORDER BY COUNT(*) DESC 
          LIMIT 1
        column: "username"
```

## Node-RED интеграција

Ако користите Node-RED, можете да создадете flow за напредна автоматизација:

```json
[
  {
    "id": "esp-rfid-flow",
    "type": "mqtt in",
    "z": "flow-id",
    "name": "ESP-RFID Events",
    "topic": "/rfid/send",
    "qos": "0",
    "broker": "mqtt-broker",
    "x": 100,
    "y": 100,
    "wires": [["process-event"]]
  },
  {
    "id": "process-event",
    "type": "function",
    "z": "flow-id", 
    "name": "Process ESP-RFID Event",
    "func": "const payload = msg.payload;\n\nif (payload.type === 'access') {\n  if (payload.isKnown === 'false') {\n    // Unknown card detected\n    node.send([{payload: payload}, null]);\n  } else if (payload.access !== 'Denied') {\n    // Access granted\n    node.send([null, {payload: payload}]);\n  }\n}\n\nreturn null;",
    "outputs": 2,
    "x": 300,
    "y": 100,
    "wires": [["unknown-card"], ["access-granted"]]
  }
]
```

## Сигурност

### Ограничување на пристап

1. **MQTT Authentication**: Користете username/password за MQTT
2. **TLS/SSL**: Активирајте TLS за MQTT комуникација
3. **Firewall**: Ограничете го пристапот до ESP-RFID Manager портот
4. **Regular Updates**: Редовно ажурирајте го addon-от

### Backup

Редовно правете backup на базата података:

```yaml
automation:
  - alias: "ESP-RFID Database Backup"
    trigger:
      - platform: time
        at: "02:00:00"
    action:
      - service: shell_command.backup_esp_rfid
        
shell_command:
  backup_esp_rfid: "cp /config/esp_rfid.db /config/backups/esp_rfid_$(date +%Y%m%d).db"
```

Оваа интеграција ви дозволува целосно управување на ESP-RFID системот директно од Home Assistant dashboard-от. 