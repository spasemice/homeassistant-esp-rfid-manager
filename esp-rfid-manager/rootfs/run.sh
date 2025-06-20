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
bashio::log.info "Supervisor Token: $(if [ -n "${SUPERVISOR_TOKEN}" ]; then echo "Present (${#SUPERVISOR_TOKEN} chars)"; else echo "Not set"; fi)"
bashio::log.info "Running in ingress mode with authentication"

# Debug information
bashio::log.info "Current directory: $(pwd)"
bashio::log.info "Python version: $(python3 --version)"
bashio::log.info "Available files in /app:"
ls -la /app

# Set up environment for Flask
export FLASK_ENV=production
export PYTHONPATH=/app
export PYTHONUNBUFFERED=1

bashio::log.info "Environment variables set for Flask"

# Test if app.py exists and is readable
if [ -f "/app/app.py" ]; then
    bashio::log.info "app.py found and readable"
    
    # Test Python syntax
    bashio::log.info "Testing Python syntax..."
    python3 -m py_compile /app/app.py
    if [ $? -eq 0 ]; then
        bashio::log.info "Python syntax check passed"
    else
        bashio::log.error "Python syntax check failed!"
        exit 1
    fi
else
    bashio::log.error "app.py not found or not readable!"
    exit 1
fi

# Start the application
cd /app
bashio::log.info "Changing to /app directory and starting Python application..."

# Add timeout and monitoring
bashio::log.info "Starting Python with timeout monitoring..."

# Run with timeout to see if it hangs
timeout 30 python3 -u app.py 2>&1 &
PID=$!

# Monitor the process
bashio::log.info "Python PID: $PID"
sleep 5

if kill -0 $PID 2>/dev/null; then
    bashio::log.info "Python process is running, waiting for Flask startup..."
    wait $PID
else
    bashio::log.error "Python process died unexpectedly"
    exit 1
fi 