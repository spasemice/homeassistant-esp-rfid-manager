# Changelog

Сите важни промени во ESP-RFID Manager addon ќе бидат документирани во овој фајл.

Форматот е базиран на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
и овој проект се придржува до [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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