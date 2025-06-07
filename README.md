# Home Assistant ESP-RFID Manager Add-ons Repository

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield] 
![Supports armhf Architecture][armhf-shield]
![Supports armv7 Architecture][armv7-shield]
![Supports i386 Architecture][i386-shield]

Централизовано управување на ESP-RFID уреди, корисници и контрола на пристап преку MQTT во Home Assistant.

![ESP-RFID Manager Dashboard](https://via.placeholder.com/800x400?text=ESP-RFID+Manager+Dashboard)

## Карактеристики

### 🏠 Управување со уреди
- ✅ Автоматско откривање на ESP-RFID уреди
- ✅ Real-time статус мониторинг (online/offline)
- ✅ Heartbeat мониторинг
- ✅ Отворање врати преку MQTT команди

### 👥 Управување со корисници
- ✅ Додавање корисници преку веб интерфејс
- ✅ Автоматска регистрација на нови картички
- ✅ Временски ограничен пристап (valid from/until)
- ✅ Различни типови пристап (Always, Admin, Disabled)
- ✅ Синхронизација со ESP-RFID уредите преку MQTT

### 📊 Логови и мониторинг
- ✅ Детални access логови (кој, кога, каде)
- ✅ Системски логови за сите ESP-RFID уреди
- ✅ Real-time ажурирања преку WebSocket
- ✅ Филтрирање логови по уред

### 🔧 MQTT интеграција
- ✅ Полна компатибилност со ESP-RFID MQTT протокол
- ✅ Поддршка за повеќе уреди
- ✅ Команди: adduser, deletuid, opendoor, getuserlist
- ✅ События: access, heartbeat, boot, door status

## Брза инсталација

### 1. Додајте го repository-то

1. Во Home Assistant, одете на **Settings** → **Add-ons** → **Add-on Store**
2. Кликнете на **⋮** (три точки) во горниот десен агол
3. Изберете **Repositories**
4. Додајте го следниов URL:

```
https://github.com/your-username/homeassistant-esp-rfid-manager
```

5. Кликнете **Add**

### 2. Инсталирајте го addon-от

1. Refresh-ирајте го Add-on Store
2. Најдете **ESP-RFID Manager** во листата
3. Кликнете **Install**
4. Чекајте да заврши инсталацијата

### 3. Конфигурирајте го addon-от

```yaml
mqtt_host: "127.0.0.1"          # IP на MQTT broker
mqtt_port: 1883                 # MQTT port  
mqtt_user: ""                   # MQTT username (опционално)
mqtt_password: ""               # MQTT password (опционално)
mqtt_topic: "/esprfid"          # MQTT topic база
log_level: "info"               # Log level
web_port: 8080                  # Web интерфејс port
auto_discovery: true            # Auto device discovery
```

### 4. Стартувајте го addon-от

1. Кликнете **Start**
2. Активирајте **Start on boot**  
3. Проверете ги логовите за грешки

### 5. Пристапете до веб интерфејсот

Отворете: `http://homeassistant.local:8080`

## Add-ons во овој repository

### ESP-RFID Manager

![Addon Stage][addon-stage-shield]
![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]
![Supports armhf Architecture][armhf-shield] 
![Supports armv7 Architecture][armv7-shield]
![Supports i386 Architecture][i386-shield]

ESP-RFID Manager е централизован веб интерфејс за управување на ESP-RFID уреди преку MQTT.

[:books: ESP-RFID Manager add-on documentation][addon-doc]

## ESP-RFID конфигурација

За да работи со овој addon, вашите ESP-RFID уреди треба да се конфигурирани со:

1. **MQTT активиран** со истите параметри како addon-от
2. **MQTT топик** поставен на `/esprfid` (или истиот како во addon-от)
3. **Send Events via MQTT** активирано
4. **Send Logs via MQTT** активирано (опционално)

## Home Assistant интеграција

Addon-от работи одлично со Home Assistant MQTT сензори и автоматизации:

```yaml
# configuration.yaml
mqtt:
  sensor:
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

## Поддршка

Имате прашање? Потребна ви е помош?

- 📖 [Документација][addon-doc]
- 🐛 [Issue Tracker][issues]
- 💬 [Дискусии][discussions]

## Придонеси

Ова е open source проект! Придонесите се добредојдени:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Лиценца

Дистрибуира се под MIT лиценца. Видете `LICENSE` за повеќе информации.

## Благодарности

- [ESP-RFID](https://github.com/esprfid/esp-rfid) проектот
- [Home Assistant](https://www.home-assistant.io/) заедницата
- Сите придонесувачи кон овој проект

---

[addon-doc]: https://github.com/your-username/homeassistant-esp-rfid-manager/blob/main/esp-rfid-manager/DOCS.md
[addon-stage-shield]: https://img.shields.io/badge/addon%20stage-stable-green.svg
[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg
[license-shield]: https://img.shields.io/github/license/your-username/homeassistant-esp-rfid-manager.svg
[releases-shield]: https://img.shields.io/github/release/your-username/homeassistant-esp-rfid-manager.svg
[releases]: https://github.com/your-username/homeassistant-esp-rfid-manager/releases
[issues]: https://github.com/your-username/homeassistant-esp-rfid-manager/issues
[discussions]: https://github.com/your-username/homeassistant-esp-rfid-manager/discussions 