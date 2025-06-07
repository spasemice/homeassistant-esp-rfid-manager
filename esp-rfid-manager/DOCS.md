# ESP-RFID Manager Add-on

## Прегледх

ESP-RFID Manager е мощен addon за Home Assistant кој овозможува централизовано управување на ESP-RFID уреди преку MQTT. Со него можете да управувате со корисници, да мониторирате пристап и да контролирате врати од еден централен dashboard.

## Карактеристики

- 🏠 **Управување со уреди**: Автоматско откривање и мониторинг на ESP-RFID уреди
- 👥 **Корисници**: Додавање, бришење и управување со корисници
- 🔐 **Пристап**: Временски ограничен пристап и различни нивоа на авторизација
- 📊 **Логирање**: Детални логови за секој пристап и системски події
- 🔄 **Real-time**: Live ажурирања преку WebSocket
- 📱 **Modern UI**: Responsive веб интерфејс со Bootstrap

## Инсталирање

Овој addon е дел од ESP-RFID Manager Add-ons repository. За инсталирање:

1. Додајте го repository-то во Home Assistant
2. Инсталирајте го ESP-RFID Manager addon-от
3. Конфигурирајте ги MQTT параметрите
4. Стартувајте го addon-от

## Конфигурација

### Основни параметри

| Параметар | Опис | Default | Тип |
|-----------|------|---------|-----|
| `mqtt_host` | IP адреса на MQTT broker | `127.0.0.1` | string |
| `mqtt_port` | Port на MQTT broker | `1883` | int |
| `mqtt_user` | MQTT username | `""` | string |
| `mqtt_password` | MQTT password | `""` | string |
| `mqtt_topic` | MQTT топик база | `/esprfid` | string |
| `log_level` | Ниво на логирање | `info` | enum |
| `web_port` | Port за веб интерфејс | `8080` | int |
| `auto_discovery` | Автоматско откривање | `true` | bool |

### Пример конфигурација

```yaml
mqtt_host: "192.168.1.100"
mqtt_port: 1883
mqtt_user: "homeassistant"
mqtt_password: "secure_password"
mqtt_topic: "/esprfid"
log_level: "info"
web_port: 8080
auto_discovery: true
```

## MQTT интеграција

### Топици

Addon-от користи следни MQTT топици:

- `{mqtt_topic}/send` - Пораки од ESP-RFID уреди
- `{mqtt_topic}/cmd` - Команди кон ESP-RFID уреди  
- `{mqtt_topic}/+/send` - Пораки од специфичен уред

### Команди

#### Додавање корисник

```json
{
  "cmd": "adduser",
  "doorip": "192.168.1.100",
  "uid": "1234567890",
  "user": "Марко Петровски",
  "acctype": "1",
  "validsince": "0",
  "validuntil": "1735689600"
}
```

#### Бришење корисник

```json
{
  "cmd": "deletuid",
  "doorip": "192.168.1.100", 
  "uid": "1234567890"
}
```

#### Отворање врата

```json
{
  "cmd": "opendoor",
  "doorip": "192.168.1.100"
}
```

### События

#### Access log

```json
{
  "type": "access",
  "time": 1605991375,
  "isKnown": "true",
  "access": "Always",
  "username": "Марко Петровски",
  "uid": "1234567890",
  "hostname": "esp-rfid-door1",
  "doorName": "Main Door"
}
```

#### Heartbeat

```json
{
  "type": "heartbeat",
  "time": 1605991375,
  "uptime": 999,
  "ip": "192.168.1.100",
  "hostname": "esp-rfid-door1"
}
```

## ESP-RFID конфигурација

За да работи addon-от, вашите ESP-RFID уреди треба да се конфигурирани:

### MQTT параметри

1. **Enable MQTT** ✅
2. **MQTT Server**: Истиот како `mqtt_host`
3. **MQTT Port**: Истиот како `mqtt_port`  
4. **MQTT Topic**: Истиот како `mqtt_topic`
5. **Username/Password**: Исти како addon-от

### MQTT опции

1. **Send Events via MQTT** ✅
2. **Send Logs via MQTT** ✅ (опционално)
3. **MQTT Events**: ✅

## Веб интерфејс

### Пристап

Отворете веб прелистувач и одете на:
```
http://YOUR_HA_IP:8080
```

### Функции

#### Dashboard

- Преглед на сите ESP-RFID уреди
- Статус на секој уред (online/offline)
- Брзи акции (отвори врата, синхронизирај)

#### Управување корисници

- Листа на сите корисници
- Додавање нови корисници
- Бришење корисници
- Филтрирање по уред

#### Access логови

- Хронолошки преглед на пристапи
- Филтрирање по уред
- Real-time ажурирања

#### Card регистрација

- Автоматска детекција на нови картички
- Едноставна регистрација со име и параметри

## API

Addon-от обезбедува REST API:

### Devices

- `GET /api/devices` - Листа на уреди
- `POST /api/doors/open` - Отвори врата

### Users

- `GET /api/users` - Листа на корисници
- `POST /api/users` - Додај корисник
- `DELETE /api/users/{id}` - Избриши корисник

### Logs

- `GET /api/access-logs` - Access логови
- `GET /api/card-registrations` - Картички за регистрација

## Home Assistant сензори

```yaml
# configuration.yaml
mqtt:
  sensor:
    - name: "ESP-RFID Door Status"
      state_topic: "/esprfid/send"
      value_template: >
        {% if value_json.type == 'heartbeat' %}
          online
        {% else %}
          {{ states('sensor.esp_rfid_door_status') }}
        {% endif %}

    - name: "ESP-RFID Last Access"
      state_topic: "/esprfid/send" 
      value_template: >
        {% if value_json.type == 'access' %}
          {{ value_json.username }}
        {% else %}
          {{ states('sensor.esp_rfid_last_access') }}
        {% endif %}

  binary_sensor:
    - name: "ESP-RFID Device Online"
      state_topic: "/esprfid/send"
      value_template: >
        {% if value_json.type == 'heartbeat' %}
          ON
        {% else %}
          {{ states('binary_sensor.esp_rfid_device_online') }}
        {% endif %}
      device_class: connectivity
```

## Автоматизации

### Известување за непознат пристап

```yaml
automation:
  - alias: "ESP-RFID Unknown Card Alert"
    trigger:
      - platform: mqtt
        topic: "/esprfid/send"
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
            {{ trigger.payload_json.hostname }}
```

## Troubleshooting

### Уредите не се поврзуваат

1. Проверете MQTT broker статус
2. Проверете MQTT конфигурација на ESP-RFID уредите
3. Проверете дали топикот е ист
4. Проверете мрежна поврзаност

### Веб интерфејс не се отвора

1. Проверете дали addon-от е стартуван
2. Проверете дали портот 8080 е слободен
3. Проверете addon логови

### MQTT грешки

1. Проверете MQTT broker логови
2. Проверете username/password
3. Проверете дали портот е достапен

## Поддршка

За проблеми и прашања:

- [GitHub Issues](https://github.com/your-username/homeassistant-esp-rfid-manager/issues)
- [Дискусии](https://github.com/your-username/homeassistant-esp-rfid-manager/discussions)
- Логови од addon-от: Settings → Add-ons → ESP-RFID Manager → Log 