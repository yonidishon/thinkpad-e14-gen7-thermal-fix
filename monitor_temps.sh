#!/bin/bash
# Temperature Monitor for ThinkPad E14 Gen 7
# Workaround for broken thinkpad_acpi thermal sensors

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Temperature thresholds
WARN_TEMP=85
CRITICAL_TEMP=90

echo -e "${CYAN}=== ThinkPad E14 Temperature Monitor ===${NC}"
echo -e "${YELLOW}Note: thinkpad_acpi thermal sensors are unavailable due to EC errors${NC}"
echo -e "${YELLOW}Using alternative thermal zone monitoring${NC}"
echo ""
echo "Press Ctrl+C to exit"
echo ""

while true; do
    # Move cursor to home position (keeps display in same place)
    tput cup 6 0

    echo -e "${CYAN}=== Current Temperatures ===${NC}"
    echo ""

    max_temp=0
    has_warning=0

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

            # Color code based on temperature
            if [ "$temp_c" -ge "$CRITICAL_TEMP" ]; then
                echo -e "${RED}  $type: ${temp_c}°C [CRITICAL!]${NC}"
                has_warning=1
            elif [ "$temp_c" -ge "$WARN_TEMP" ]; then
                echo -e "${YELLOW}  $type: ${temp_c}°C [WARNING]${NC}"
                has_warning=1
            else
                echo -e "${GREEN}  $type: ${temp_c}°C${NC}"
            fi
        fi
    done

    echo ""
    echo -e "Maximum temperature: ${max_temp}°C"
    echo ""

    # Show status
    echo -e "${CYAN}=== System Status ===${NC}"
    echo "Fan control: UNAVAILABLE (EC error)"
    echo "Thermal daemon: DISABLED (unsupported CPU)"

    # Load average
    load=$(cat /proc/loadavg | awk '{print $1, $2, $3}')
    echo "Load average: $load"

    # CPU frequency (if available)
    if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq ]; then
        freq=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq)
        freq_mhz=$((freq / 1000))
        echo "CPU frequency: ${freq_mhz} MHz"
    fi

    echo ""

    # Show warnings
    if [ "$has_warning" -eq 1 ]; then
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        if [ "$max_temp" -ge "$CRITICAL_TEMP" ]; then
            echo -e "${RED}⚠️  CRITICAL: Temperature above ${CRITICAL_TEMP}°C!${NC}"
            echo -e "${RED}⚠️  System may hang/freeze! Consider cooling down.${NC}"
            # Beep to alert user
            echo -ne '\007'
        elif [ "$max_temp" -ge "$WARN_TEMP" ]; then
            echo -e "${YELLOW}⚠️  WARNING: Temperature above ${WARN_TEMP}°C${NC}"
            echo -e "${YELLOW}⚠️  System is getting hot. Ensure good ventilation.${NC}"
        fi
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    else
        echo -e "${GREEN}✓ All temperatures within safe range${NC}"
    fi

    echo ""
    echo "Last updated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "                                                    "

    # Update every 2 seconds
    sleep 2
done
