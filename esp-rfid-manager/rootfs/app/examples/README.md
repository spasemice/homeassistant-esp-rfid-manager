# ESP-RFID Manager - Home Assistant Integration Examples

This directory contains example configurations for integrating ESP-RFID Manager with Home Assistant.

## Files

### `configuration.yaml`
Complete Home Assistant configuration example that includes:
- MQTT sensors for door status, last access, and unknown cards
- Binary sensors for online/offline status
- Template sensors for aggregate status
- Automations for alerts and logging
- Scripts for common actions

### `lovelace-grid-dashboard.yaml`
Beautiful Lovelace dashboard configuration featuring:
- Grid layout with visual door status cards
- Real-time status indicators (green/red)
- Last access information
- History graphs
- Unknown card alerts
- Quick action buttons

### `user-specific-dashboard.yaml`
User-specific dashboard that shows only doors the current Home Assistant user has access to:
- Conditional cards based on user permissions
- Personal door access buttons
- User access history
- Dynamic door list based on ESP-RFID user database

## Setup Instructions

### 1. MQTT Auto-Discovery (Recommended)

The ESP-RFID Manager addon automatically publishes MQTT discovery messages for Home Assistant. This is the easiest setup method:

1. Install the ESP-RFID Manager addon
2. Configure MQTT settings in the addon
3. Start the addon
4. Devices will automatically appear in Home Assistant under Settings → Devices & Services → MQTT

### 2. Manual Configuration

If you prefer manual configuration:

1. Copy relevant sections from `configuration.yaml` to your Home Assistant `configuration.yaml`
2. Update device hostnames to match your ESP-RFID devices
3. Restart Home Assistant
4. Add the dashboard configuration to a new dashboard

### 3. Dashboard Setup

1. In Home Assistant, go to Settings → Dashboards
2. Create a new dashboard or edit an existing one
3. Add a new card and select "Manual" mode
4. Copy the contents of `lovelace-grid-dashboard.yaml`
5. Update entity names to match your devices
6. Save the card

## Features

### Real-time Monitoring
- ✅ Online/offline status for each door
- ✅ Last access information with user details
- ✅ Door status (ready, granted, denied, offline)
- ✅ Unknown card detection alerts
- ✅ **NEW:** Button entities for remote door unlock
- ✅ **NEW:** User-specific door access permissions

### Automation Examples
- 📱 Mobile notifications for unknown cards
- ⚠️ Alerts when doors go offline
- 📝 Automatic logging of access events
- 🔄 Scheduled user synchronization

### Dashboard Features
- 🎨 Beautiful grid layout with color-coded status
- 📊 24-hour access history graphs
- 🔍 Unknown card detection panel
- 🚪 Quick action buttons for door control
- 📱 Mobile-responsive design

## Customization

### Adding More Doors
To add additional ESP-RFID devices:

1. In `configuration.yaml`, duplicate the sensor sections and update hostnames
2. In the dashboard configuration, add new button-card entries
3. Update automation entity lists to include new sensors

### Changing Notification Settings
Modify the automation section in `configuration.yaml`:
- Change `notify.mobile_app_your_phone` to your notification service
- Adjust trigger conditions and timing
- Customize message templates

### Custom Icons and Colors
In the dashboard configuration:
- Change `icon: mdi:door` to any Material Design icon
- Modify colors in the `color` fields
- Adjust card sizes and layouts

## Troubleshooting

### Entities Not Appearing
1. Check MQTT broker connectivity
2. Verify ESP-RFID Manager addon is running
3. Check Home Assistant logs for MQTT discovery messages
4. Manually restart MQTT integration

### Dashboard Not Loading
1. Verify button-card custom component is installed via HACS
2. Check entity names match your actual devices
3. Validate YAML syntax in developer tools

### No Data in Sensors
1. Ensure ESP-RFID devices are connected and reporting
2. Check MQTT topic names match your configuration
3. Verify ESP-RFID Manager is publishing to correct topics

## Additional Resources

- [Home Assistant MQTT Integration](https://www.home-assistant.io/integrations/mqtt/)
- [Button Card Custom Component](https://github.com/custom-cards/button-card)
- [ESP-RFID Project](https://github.com/esprfid/esp-rfid)

## Support

For issues with the ESP-RFID Manager addon, create an issue in the addon repository.
For Home Assistant integration questions, check the Home Assistant community forums. 