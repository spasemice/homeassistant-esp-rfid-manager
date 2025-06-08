#!/usr/bin/with-contenv bashio

# Parse configuration
export MQTT_HOST=$(bashio::config 'mqtt_host')
export MQTT_PORT=$(bashio::config 'mqtt_port')
export MQTT_USER=$(bashio::config 'mqtt_user')
export MQTT_PASSWORD=$(bashio::config 'mqtt_password')
export MQTT_TOPIC=$(bashio::config 'mqtt_topic')
export LOG_LEVEL=$(bashio::config 'log_level')
export WEB_PORT=$(bashio::config 'web_port')
export AUTO_DISCOVERY=$(bashio::config 'auto_discovery')

# Home Assistant authentication
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN:-}"
export HOMEASSISTANT_URL="${HOMEASSISTANT_URL:-http://supervisor/core}"

bashio::log.info "Starting ESP-RFID Manager..."
bashio::log.info "MQTT Host: ${MQTT_HOST}:${MQTT_PORT}"
bashio::log.info "MQTT Topic: ${MQTT_TOPIC}"
bashio::log.info "Web Port: ${WEB_PORT}"
bashio::log.info "Authentication: $(if [ -n "${SUPERVISOR_TOKEN}" ]; then echo "Enabled (Home Assistant)"; else echo "Disabled"; fi)"

# Start the application
cd /app
exec python3 app.py 