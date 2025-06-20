# Changelog

Сите важни промени во ESP-RFID Manager addon ќе бидат документирани во овој фајл.

Форматот е базиран на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
и овој проект се придржува до [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2025-06-07

### Додадено
- **Home Assistant Authentication Integration**: Addon сега бара authentication со Home Assistant
- User session management со автоматски redirect кон HA login ако не е најавен
- User info display во navbar со admin/standard user roles 
- Logout функционалност со правилно session cleanup
- Ingress поддршка за сигурен пристап преку Home Assistant интерфејс
- Auth API интеграција за user validation

### Подобрено
- Сигурна access control - само најавени Home Assistant корисници можат да пристапат
- Подобрено user experience со правилен authentication flow
- Подобра интеграција со Home Assistant екосистемот
- Професионален navbar со user dropdown мени

### Променето
- Port конфигурација подновена за користење ingress наместо директен port пристап
- Authentication middleware додаден за заштита на сите non-API routes
- Session-based user management

### Безбедност
- Сиот web интерфејс пристап сега бара Home Assistant authentication
- API endpoints остануваат достапни за Home Assistant интеграција
- Сигурна token-based authentication со Supervisor API

## [1.1.5] - 2025-06-07

### Поправено
- **Offline Detection Timeout**: Зголемен timeout од 45 на 90 секунди (6x heartbeat од 15 сек) за подобра стабилност
- **Card Detection за Access Messages**: Додадена поддршка за card detection при `"type": "access"` пораки од `/send` topic
- **Device Deletion DateTime Parsing**: Поправено parsing на различни datetime формати за offline device проверки
- **Card Auto-Fill**: Сега функционира card detection за unknown cards од `esprfid/device/send` topic

### Подобрено
- Card detection сега работи за сите типови пораки: `/tag`, `/send` (access), и event messages
- Подобрено логирање за card detection events со извор на порака
- Enhanced datetime handling во device deletion логика
- Стабилнос на offline device detection за уреди со 15-секундни heartbeats

### Техничко
- Додадена `card_scan_result` event emission во `handle_access_message`
- Enhanced datetime parsing за SQLite и ISO формати
- Зголемен offline timeout на 90 секунди за подобра мрежна толеранција
- Enhanced logging за device timeout events

## [1.1.4] - 2025-06-07

### Поправено
- **Device Deletion sqlite3.Row Error**: Поправена грешка при бришење devices поради sqlite3.Row објект синтакса
- **Permission Grid Headers**: Поправени header колони во User Permissions табела за да се прикажуваат имињата на вратите
- **Table Structure**: Исправена HTML табела структура за permission grid

### Подобрено
- Јасни header колони во Permission Grid: "Main Door", "Front Door", "Back Door", "Side Door"  
- Подобрена читливост на permissions табелата
- Поправен sqlite3.Row објект handling во device operations

## [1.1.3] - 2025-06-07

### Поправено
- **Device Deletion Error**: Поправена 500 грешка при бришење offline devices поради user_permissions табела
- **Access Type Auto-Update**: Permissions сега автоматски ја менуваат access type (Always/Disabled) во users табела 
- **Card Detection**: Поправена автоматска card detection во Add User modal со правилни device checkbox ID-а
- **Bulk Assignment**: Додадено auto-check на device кога се детектира картичка во Bulk Assignment modal
- **ESP-RFID Sync**: User permissions промени се синхронизираат со ESP-RFID уреди преку MQTT команди

### Подобрено
- Enhanced error handling во device deletion со try-catch логика
- Автоматска детекција на device checkbox naming conventions (userDevice_ и device_)
- Real-time синхронизација на access types помеѓу permission grid и ESP-RFID уреди
- Подобрено логирање за debugging на permission updates

### Техничко
- Додадена error tolerant логика за user_permissions табела
- Автоматско MQTT команди за ажурирање access types на уреди
- Enhanced logging за permission updates и device sync operations

## [1.1.2] - 2025-06-07

### Додадено
- **User Permissions Grid**: Додаден комплетен систем за управување пристапни дозволи со grid интерфејс
- **Integrated Card Template Generator**: Вграден генератор за Home Assistant картички со copy-to-clipboard
- **User Permission Management**: Нови API endpoints за granular контрола на пристап по врати/уреди
- **Enhanced Database Schema**: Додадена user_permissions табела за детална контрола на пристап

### Поправено  
- **Offline Device Deletion**: Поправена логика за бришење offline уреди (offline > 2 минути)
- **Compact Device Layout**: Редизајниран компактен приказ на уреди (3-4 картички по ред)
- **Template Generator**: Поправен скршен card generator и интегриран во modal интерфејс
- **Permission Button**: Додаден permissions edit button во users табела со shield икона

### Подобрено
- **User Interface**: Подобар и компактен layout за приказ на уреди
- **Permission Management**: Визуелен grid интерфејс сличен на enterprise access control системи  
- **Device Status Indicators**: Подобри визуелни индикатори за online/offline статус
- **Error Handling**: Подобрени error мессиџи и user feedback низ интерфејсот

### Техничко
- Нови API endpoints: `/api/users/<id>/permissions` (GET/PUT)
- Додадена user_permissions табела во иницијализацијата на базата
- Enhanced device deletion логика со времински провери
- Подобрена MQTT command handling за multi-device операции

## [1.1.0] - 2025-06-07

### Главни Нови Функции
- **ДОДАДЕНО: Delete Offline Devices** - Можност за бришење offline уреди со сите нивни корисници
- **ДОДАДЕНО: Multi-Device User Deletion** - Checklist за избор од кои уреди да се обрише корисникот
- **ДОДАДЕНО: Integrated HA Card Generator** - Генератор за Home Assistant картички наместо YAML код
- **ПОДОБРЕНО: Real-time Access Logs** - Најновите логови секогаш се погоре со flash ефект

### Device Management
- Можност за бришење offline devices со предупредување за online devices
- Автоматско бришење на сите поврзани корисници кога се брише device
- Enhanced device status проверки пред бришење

### User Management Improvements
- Multi-device user deletion со checkbox selection
- Прикажување статус на секој device (online/offline) при бришење
- Separate handling за online и offline devices при user deletion
- Enhanced user-device mapping со детални информации

### Home Assistant Integration
- Интегриран card template generator наместо статички YAML
- Можност за избор на devices за card generation
- Различни типови картички: Grid, Entities, History
- Copy to clipboard функционалност за генерирани картички
- Real-time device status во card generation

### Real-time Improvements 
- Access logs сега се ordered по ID DESC, timestamp DESC (најнови погоре)
- Flash ефект за нови access log entries
- Автоматско ажурирање без refresh на страната
- Подобрени visual indicators за real-time updates

### API Enhancements
- `/api/devices/<hostname>` DELETE endpoint за бришење devices
- `/api/users/<id>/devices` GET endpoint за user device mapping
- Enhanced `/api/users/<id>` DELETE со multi-device поддршка
- `/api/homeassistant/card-template` POST endpoint за card generation
- Подобрено error handling и response messages

### UI/UX Improvements
- Нови модали за delete operations со enhanced warnings
- Device status indicators (online/offline) со color coding
- Enhanced feedback за user operations
- Professional checkbox interfaces за device selection
- Подобрени alerts и notifications

**ВАЖНО**: Оваа верзија додава значајни функции за управување со offline devices и multi-device операции!

## [1.0.9] - 2025-06-07

### Критични Поправки
- **ПОПРАВЕНИ MQTT TOPICS** - Сега користи device-specific topics (esprfid/HOSTNAME/cmd) наместо генерички
- **ДОДАДЕНА /tag TOPIC ПОДДРШКА** - Слуша на esprfid/+/tag за real-time card scan events
- **ПОПРАВЕНА CARD DETECTION** - Сега правилно детектира картички од /tag topic
- **ПОПРАВЕНИ MQTT КОМАНДИ** - adduser, deletuid, opendoor сега се испраќаат на правилните device topics

### Нови Функции
- Додадена handle_tag_message() функција за обработка на card scan events
- Автоматско извлекување на device hostname од MQTT topic структура
- Real-time card detection од /tag topic кога е отворен Add User модал
- Device-specific MQTT command routing за сите ESP-RFID команди

### Подобрено
- Enhanced MQTT logging со 🏷️ емоџи за tag events
- Подобрена device hostname detection од topic path
- Real-time dashboard updates кога се скенираат картички
- Поправена MQTT command delivery со правилни device-specific topics

### Техничко
- Проширени MQTT subscriptions: +/send, +/cmd, +/tag topics
- Додаден device_hostname параметар во сите MQTT command функции
- Автоматско hostname mapping од topic structure
- Enhanced error handling за device hostname detection

**ВАЖНО**: Оваа верзија решава критичен проблем со MQTT комуникација што спречуваше додавање корисници и real-time updates!

## [1.0.8] - 2025-06-07

### Поправено
- Поправена автоматска детекција на картички во Add User модалот - сега правилно ја пополнува UID формата
- Поправени MQTT subscriptions за cmd topics - сега слуша и на /cmd topics за command responses
- Поправено MQTT message handling за log commands од различни topic формати  
- Поправена логика за device checkbox selection во Add User модалот
- Поправен Home Assistant users API за да врати вистински корисници од базата

### Подобрено
- Додадено подобрено MQTT debugging со емоџи лог мессиџи (📩📤🔍🎯)
- Подобрени card detection мессиџи и статус известувања
- Додадена showAlert функција за подобри visual notifications
- Подобрени MQTT command logs со публish result status
- Enhanced card scan result logging со повеќе детали
- Подобрени warning мессиџи кога картичката е веќе регистрирана

### Додадено
- Поддршка за слушање MQTT cmd topics поред send topics
- Автоматски warnings кога се детектира веќе регистрирана картичка
- Визуелни feedback alerts за card detection events
- Enhanced debugging за troubleshooting MQTT комуникација
- Подобрени SocketIO event мессиџи за card detection start/stop

### Техничко
- Проширени MQTT subscriptions: /send, /cmd, и HA button topics
- Додадено enhanced logging во сите MQTT операции  
- Поправена device naming convention за checkboxes
- Подобрена error handling во frontend
- Enhanced ESP-RFID users integration во HA users API

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