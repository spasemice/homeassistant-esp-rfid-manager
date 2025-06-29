# ESP-RFID Manager - Home Assistant Addon

Централизовано управување на ESP-RFID уреди, корисници и контрола на пристап преку MQTT.

## Карактеристики

### 🏠 Управување со уреди
- Автоматско откривање на ESP-RFID уреди
- Мониторинг на статус во реално време (online/offline)
- Heartbeat мониторинг
- Отворање врати преку MQTT команди

### 👥 Управување со корисници
- Додавање нови корисници преку веб интерфејс
- Автоматска регистрација на нови картички
- Поддршка за временски ограничен пристап
- Различни типови на пристап (Always, Admin, Disabled)
- Синхронизација на корисници со ESP-RFID уредите

### 📊 Логови и мониторинг
- Логови за секој пристап (кој, кога, каде)
- Системски години за сите ESP-RFID уреди
- Реални времски ажурирања преку WebSocket
- Филтрирање на логови по уред

### 🔧 MQTT интеграција
- Комуникација со ESP-RFID уреди преку MQTT
- Поддршка за повеќе уреди
- Автоматска конфигурација на MQTT топици
- Heartbeat мониторинг

## Инсталирање

1. Додајте го овој repository во Home Assistant Add-on Store
2. Инсталирајте го "ESP-RFID Manager" addon-от
3. Конфигурирајте ги MQTT параметрите
4. Стартувајте го addon-от

## Конфигурација

```yaml
mqtt_host: "127.0.0.1"
mqtt_port: 1883
mqtt_user: ""
mqtt_password: ""
mqtt_topic: "/rfid"
log_level: "info"
web_port: 8080
auto_discovery: true
```

### Опции

- `mqtt_host`: IP адреса или hostname на MQTT broker-от
- `mqtt_port`: Port на MQTT broker-от (default: 1883)
- `mqtt_user`: Username за MQTT (опционално)
- `mqtt_password`: Password за MQTT (опционално)
- `mqtt_topic`: База топик за MQTT комуникација (default: "/rfid")
- `log_level`: Ниво на логирање (trace|debug|info|notice|warning|error|fatal)
- `web_port`: Port за веб интерфејсот (default: 8080)
- `auto_discovery`: Автоматско откривање на уреди (default: true)

## Користење

### Пристап до веб интерфејсот
Отворете веб прелистувач и одете на:
```
http://homeassistant.local:8080
```

### Додавање нови корисници

1. **Автоматска регистрација на картички:**
   - Скенирајте нова картичка на било кој ESP-RFID уред
   - Картичката ќе се појави во "New Cards Detected" секцијата
   - Кликнете "Register" и внесете ги податоците за корисникот

2. **Рачно додавање:**
   - Кликнете на "Add User" копчето
   - Внесете име, UID на картичката, уред и период на важност
   - Кликнете "Add User"

### Управување со пристап

- **Always**: Корисникот има пристап во секое време
- **Admin**: Администраторски пристап
- **Disabled**: Пристапот е оневозможен

### Временски ограничен пристап

Можете да поставите период кога корисникот има пристап:
- **Valid From**: Од кога важи пристапот
- **Valid Until**: До кога важи пристапот

## ESP-RFID конфигурација

За да работи со овој addon, вашите ESP-RFID уреди треба да се конфигурирани со:

1. **MQTT активиран** со истите параметри како addon-от
2. **MQTT топик** поставен на истиот како во addon-от (default: "/rfid")
3. **Send Logs via MQTT** активирано за логови
4. **Send Events via MQTT** активирано за събития

## API

Addon-ot обезбедува REST API за интеграција:

### Devices
- `GET /api/devices` - Листа на уреди
- `POST /api/doors/open` - Отвори врата

### Users  
- `GET /api/users` - Листа на корисници
- `POST /api/users` - Додај корисник
- `DELETE /api/users/{id}` - Избриши корисник

### Logs
- `GET /api/access-logs` - Логови за пристап
- `GET /api/card-registrations` - Картички за регистрација

## Примери на MQTT пораки

### Додавање корисник
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

### Отворање врата
```json
{
  "cmd": "opendoor", 
  "doorip": "192.168.1.100"
}
```

### Access log (од ESP-RFID)
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

## Troubleshooting

### MQTT проблеми
1. Проверете дали MQTT broker-от работи
2. Проверете дали параметрите за поврзување се точни
3. Проверете дали ESP-RFID уредите користат ист топик

### Уредите не се поврзуваат
1. Проверете дали ESP-RFID уредите се на истата мрежа
2. Проверете дали MQTT е активиран на уредите
3. Проверете логовите на addon-от

### Проблеми со додавање корисници
1. Проверете дали уредот е online
2. Проверете дали UID-от на картичката е точен
3. Проверете MQTT логовите

## Поддршка

За прашања и проблеми, отворете issue на GitHub repository-то.

## Лиценца

MIT License - видете LICENSE фајлот за детали. 