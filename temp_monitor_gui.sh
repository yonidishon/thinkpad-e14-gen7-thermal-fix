#!/bin/bash
# Temperature Monitor with GUI Notifications for ThinkPad E14 Gen 7
# Monitors temperatures and shows popup warnings when temps get too high

# Temperature thresholds
WARN_TEMP=85
CRITICAL_TEMP=90
CHECK_INTERVAL=10  # Check every 10 seconds

# Log file
LOG_FILE="$HOME/.temp_monitor.log"

# PID file to track if already running
PID_FILE="$HOME/.temp_monitor.pid"

# Function to check if already running
check_already_running() {
    if [ -f "$PID_FILE" ]; then
        old_pid=$(cat "$PID_FILE")
        if ps -p "$old_pid" > /dev/null 2>&1; then
            echo "Temperature monitor already running (PID: $old_pid)"
            exit 0
        fi
    fi
    echo $$ > "$PID_FILE"
}

# Function to clean up on exit
cleanup() {
    rm -f "$PID_FILE"
    exit 0
}

trap cleanup EXIT INT TERM

# Function to send notification
send_notification() {
    local urgency="$1"
    local title="$2"
    local message="$3"

    # Try notify-send first (works in most Linux desktops)
    if command -v notify-send &> /dev/null; then
        notify-send -u "$urgency" -i dialog-warning "$title" "$message"
    fi

    # Also try zenity for critical warnings (blocks until user clicks OK)
    if [ "$urgency" = "critical" ] && command -v zenity &> /dev/null; then
        zenity --warning --title="$title" --text="$message" --width=400 &
    fi
}

# Function to log message
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check if notification tools are available
if ! command -v notify-send &> /dev/null; then
    echo "Warning: notify-send not found. Installing libnotify-bin..."
    if command -v apt &> /dev/null; then
        pkexec apt install -y libnotify-bin
    fi
fi

# Track warning states to avoid spam
last_warning_time=0
last_critical_time=0
warning_cooldown=300  # 5 minutes between repeat warnings

# Counter for periodic logging (every minute)
check_counter=0

check_already_running

log_message "Temperature monitor started (PID: $$)"
log_message "Thresholds: Warning=${WARN_TEMP}°C, Critical=${CRITICAL_TEMP}°C"

# Initial notification
send_notification "normal" "Temperature Monitor" "Temperature monitoring active\nWarning: ${WARN_TEMP}°C | Critical: ${CRITICAL_TEMP}°C"

while true; do
    max_temp=0
    temp_readings=""
    current_time=$(date +%s)

    # Check all thermal zones
    for zone in /sys/class/thermal/thermal_zone*; do
        if [ -f "$zone/temp" ]; then
            type=$(cat "$zone/type" 2>/dev/null || echo "unknown")
            temp=$(cat "$zone/temp" 2>/dev/null || echo "0")
            temp_c=$((temp / 1000))

            # Track max temperature
            if [ "$temp_c" -gt "$max_temp" ]; then
                max_temp=$temp_c
            fi

            temp_readings="${temp_readings}${type}: ${temp_c}°C\n"
        fi
    done

    # Check temperature thresholds and send notifications
    if [ "$max_temp" -ge "$CRITICAL_TEMP" ]; then
        time_since_last=$((current_time - last_critical_time))
        if [ "$time_since_last" -ge "$warning_cooldown" ]; then
            message="⚠️  CRITICAL TEMPERATURE: ${max_temp}°C!\n\nSystem may freeze/hang!\nClose applications and let system cool down.\n\n${temp_readings}"
            send_notification "critical" "🔥 CRITICAL TEMPERATURE ALERT" "$message"
            log_message "CRITICAL: Temperature reached ${max_temp}°C"
            last_critical_time=$current_time

            # Also beep if available
            if command -v paplay &> /dev/null && [ -f /usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga ]; then
                paplay /usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga &
            fi
        fi
    elif [ "$max_temp" -ge "$WARN_TEMP" ]; then
        time_since_last=$((current_time - last_warning_time))
        if [ "$time_since_last" -ge "$warning_cooldown" ]; then
            message="Temperature elevated: ${max_temp}°C\n\nEnsure good ventilation.\nConsider using cooling pad.\n\n${temp_readings}"
            send_notification "normal" "⚠️  Temperature Warning" "$message"
            log_message "WARNING: Temperature reached ${max_temp}°C"
            last_warning_time=$current_time
        fi
    fi

    # Log current max temp every minute (every 6 checks × 10 seconds)
    check_counter=$((check_counter + 1))
    if [ $((check_counter % 6)) -eq 0 ]; then
        log_message "Current max temperature: ${max_temp}°C"
    fi

    sleep "$CHECK_INTERVAL"
done
