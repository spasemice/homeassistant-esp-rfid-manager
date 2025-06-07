# Changelog

Сите важни промени во ESP-RFID Manager addon ќе бидат документирани во овој фајл.

Форматот е базиран на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
и овој проект се придржува до [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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