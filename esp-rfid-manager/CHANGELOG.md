# Changelog

Сите важни промени во ESP-RFID Manager addon ќе бидат документирани во овој фајл.

Форматот е базиран на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
и овој проект се придржува до [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.7] - 2025-06-07

### Подобрено
- Додадени детални attributes во сите Home Assistant sensors
- Door sensors сега содржат последен пристапил корисник, UID, IP адреса, и време
- Online/offline sensors со device IP, hostname, last seen timestamp, и статус промени
- Unknown card sensors со детални информации за scan тип и device info
- Access history sensors со детално мапирање на корисници и метод на пристап
- Подобрени friendly names во сите sensor attributes за полесно читање

### Додадено
- IP адреса на уредот во сите sensor attributes
- Hostname информации во сите sensors
- Timestamp за секоја статус промена
- Последен корисник пристап во door status attributes
- Access method tracking (RFID, HA button, etc.)
- Детални friendly messages за секој event
- Подобрени логови со device-specific информации

### Техничко
- Проширени update_ha_sensors() функција со повеќе attributes
- Додадени json_attributes_topic во сите HA discovery configs
- Подобрено мапирање на device IP адреси во attributes
- Enhanced event tracking со повеќе детали

## [1.0.6] - 2025-06-07

### Поправено
- Скратени имиња во Home Assistant entities (наместо "ESP-RFID esp-rfidx Door Status" сега е "esp-rfidx Door")
- Намален offline timeout од 5 минути на 45 секунди (3x heartbeat од 15 сек)
- Подобрено логирање за online/offline статус промени

### Подобрено
- Пократки и почисти имиња во Home Assistant за подобра читливост
- Побрзо детектирање на offline уреди (45 сек наместо 5 мин)
- Подобрени лог мессиџи: `{hostname} Door Status changed to online/offline`
- Автоматско ажурирање на HA сензори кога уредот се враќа online

### Техничко
- Промена на device naming schema во HA discovery
- Оптимизиран offline detection алгоритам
- Додадено online status логирање во update_device_status функцијата

## [1.0.5] - 2025-06-07

### Поправено
- Комплетно отстранета "New Cards Detected" секција која се појавуваше и кога не беше потребна
- Поправена автоматска детекција на картички во Add User модалот  
- Отстранети сите непотребни card registration функции и модали

### Подобрено
- Додаден Home Assistant корисници dropdown во Add User модалот наместо обичен text input
- Можност за избор помеѓу HA корисници (dropdown) или custom username (manual entry)
- Подобрена card detection логика - работи само преку SocketIO events кога е потребна
- Автоматско вчитување на Home Assistant корисници од API
- Toggle опција за manual entry на custom usernames

### Додадено
- `/api/homeassistant/users` endpoint за добивање на HA корисници
- `toggleManualEntry()` функција за switching помеѓу dropdown и manual input
- `getSelectedUsername()` функција за добивање на избраниот username
- `loadHomeAssistantUsers()` за автоматско вчитување на HA корисници

### Техничко
- Отстранети сите card registration табели и функции
- Поедноставена card detection архитектура
- Подобрена UX за избор на корисници

## [1.0.4] - 2025-06-07

### Поправено
- Поправен Response import error во Flask API endpoints
- Поправено испраќање MQTT команди при додавање корисници - сега се испраќаат до ESP-RFID уредите
- Паметна детекција на картички - работи само кога е отворен Add User модалот
- Отстранети непотребни "New Cards Detected" известувања што се појавуваа секогаш

### Подобрено  
- Multi-device поддршка при додавање корисници - може да се избираат повеќе уреди одеднаш
- Checkbox интерфејс за избор на уреди наместо dropdown
- Автоматско вклучување/исклучување на card detection кога се отвора/затвора Add User модалот
- Card detection status индикатор во Add User модалот
- Детални резултати за секој уред при додавање корисници (успех/грешка)
- Подобрено автоматско чистење на формите кога се затворани модалите
- Подобрено логирање на MQTT операции

### Техничко
- Додадени SocketIO events за контрола на card detection (start_card_detection, stop_card_detection)
- Ажуриран API endpoint `/api/users` за multi-device поддршка
- Додаден `card_detection_active` flag во ESPRFIDManager класата
- Поддршка за legacy single device format за backward compatibility

## [1.0.3] - 2025-06-07

### Додадено
- Home Assistant MQTT Auto Discovery sensors за door status, last access, unknown cards
- Button entities за remote door unlock со user permission checking  
- Complete access history tracking mapping HA users to ESP-RFID users
- User permission API за прикажување само на дозволени врати
- API endpoints за Home Assistant интеграција и dashboard конфигурации

## [1.0.0] - 2025-06-07

### Додадено
- Иницијална верзија на ESP-RFID Manager addon
- MQTT интеграција за комуникација со ESP-RFID уреди
- Веб интерфејс за управување со уреди и корисници
- Автоматско откривање на ESP-RFID уреди преку MQTT
- Real-time мониторинг на статус на уреди (online/offline)
- Управување со корисници (додавање, бришење, уредување)
- Автоматска регистрација на нови RFID картички
- Временски ограничен пристап (valid from/until)
- Различни типови на пристап (Always, Admin, Disabled)
- Детални access логови за секој пристап
- Системски логови за сите ESP-RFID уреди
- Real-time ажурирања преку WebSocket
- REST API за интеграција со други системи
- SQLite база за чување на податоци
- Bootstrap 5 responsive веб интерфејс
- Поддршка за повеќе ESP-RFID уреди едновремено
- MQTT команди: adduser, deletuid, opendoor, getuserlist
- Heartbeat мониторинг на уредите
- Филтрирање на логови по уред
- Отворање врати преку веб интерфејс
- Конфигурабилни MQTT параметри
- Поддршка за MQTT authentication
- Multi-architecture поддршка (amd64, armv7, aarch64, armhf, i386)

### Техничко
- Python Flask веб апликација
- SQLite база за persistence
- MQTT client за комуникација
- Flask-SocketIO за real-time комуникација
- APScheduler за автоматски задачи
- Dockerfile оптимизиран за Home Assistant add-ons
- Bashio интеграција за конфигурација

### Документација
- Комплетна документација за инсталирање
- MQTT API документација
- Примери за Home Assistant автоматизации
- Troubleshooting guide
- ESP-RFID конфигурациски примери 