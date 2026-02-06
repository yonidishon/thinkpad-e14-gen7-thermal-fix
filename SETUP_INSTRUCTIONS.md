# ThinkPad E14 Gen 7 Temperature Monitor Setup

## Overview

Due to ACPI/EC errors preventing thermal sensor access and fan control on your ThinkPad E14 Gen 7, this temperature monitoring system will:
- Monitor available thermal zones every 10 seconds
- Show GUI popup warnings when temperature exceeds 80°C
- Show critical alerts when temperature exceeds 90°C
- Log all events to `~/.temp_monitor.log`
- Prevent duplicate alerts (5 minute cooldown)

---

## Installation (Choose ONE method)

### Method 1: Systemd User Service (Recommended)

This runs the monitor as a systemd service for your user.

**Install:**
```bash
# Copy service file to systemd user directory
mkdir -p ~/.config/systemd/user
cp temp-monitor.service ~/.config/systemd/user/

# Enable and start the service
systemctl --user daemon-reload
systemctl --user enable temp-monitor.service
systemctl --user start temp-monitor.service

# Check status
systemctl --user status temp-monitor.service
```

**Disable/Remove:**
```bash
# Stop and disable the service
systemctl --user stop temp-monitor.service
systemctl --user disable temp-monitor.service

# Optionally remove the service file
rm ~/.config/systemd/user/temp-monitor.service
systemctl --user daemon-reload
```

**View logs:**
```bash
# Real-time logs
journalctl --user -u temp-monitor.service -f

# Recent logs
journalctl --user -u temp-monitor.service -n 50

# Application log file
tail -f ~/.temp_monitor.log
```

---

### Method 2: Autostart Desktop Entry

This runs the monitor when you log into your desktop session.

**Install:**
```bash
# Copy desktop file to autostart directory
mkdir -p ~/.config/autostart
cp temp-monitor.desktop ~/.config/autostart/

# The monitor will start automatically on next login
# To start it now without rebooting:
/home/yonatan/dev/sys_crash_analysis/temp_monitor_gui.sh &
```

**Disable/Remove:**
```bash
# Remove from autostart
rm ~/.config/autostart/temp-monitor.desktop

# Stop currently running instance
pkill -f temp_monitor_gui.sh
```

**View logs:**
```bash
# Check application log
tail -f ~/.temp_monitor.log
```

---

## Testing the Monitor

After installation, test that notifications work:

```bash
# Send a test notification
notify-send -u normal "Test" "If you see this, notifications work!"

# Check if monitor is running
ps aux | grep temp_monitor_gui.sh

# Check current temperatures manually
/home/yonatan/dev/sys_crash_analysis/temp_monitor_gui.sh &

# View log file
cat ~/.temp_monitor.log
```

---

## Customizing Thresholds

Edit the thresholds in `temp_monitor_gui.sh`:

```bash
nano /home/yonatan/dev/sys_crash_analysis/temp_monitor_gui.sh
```

Modify these values:
```bash
WARN_TEMP=80        # Warning notification at this temperature
CRITICAL_TEMP=90    # Critical alert at this temperature
CHECK_INTERVAL=10   # How often to check (seconds)
```

After editing, restart the service:
```bash
systemctl --user restart temp-monitor.service
# OR if using autostart method:
pkill -f temp_monitor_gui.sh
/home/yonatan/dev/sys_crash_analysis/temp_monitor_gui.sh &
```

---

## Notification Types

### Normal Warning (≥80°C)
- Shows yellow notification with temperature details
- Repeats every 5 minutes if temperature stays high
- Logged to file

### Critical Alert (≥90°C)
- Shows red critical notification
- May show blocking popup dialog (zenity)
- Plays system alert sound if available
- Repeats every 5 minutes if temperature stays critical
- Logged to file with CRITICAL tag

---

## Troubleshooting

### No notifications appearing

1. Check if libnotify is installed:
   ```bash
   dpkg -l | grep libnotify-bin
   # If not found:
   sudo apt install libnotify-bin
   ```

2. Test notifications manually:
   ```bash
   notify-send "Test" "This is a test"
   ```

3. Check if the monitor is running:
   ```bash
   ps aux | grep temp_monitor_gui.sh
   ```

### Monitor not starting at boot

**For systemd method:**
```bash
# Check service status
systemctl --user status temp-monitor.service

# View errors
journalctl --user -u temp-monitor.service -n 50
```

**For autostart method:**
```bash
# Verify desktop file exists
ls -la ~/.config/autostart/temp-monitor.desktop

# Check file permissions
chmod +x /home/yonatan/dev/sys_crash_analysis/temp_monitor_gui.sh
```

### Monitor crashes or stops

The systemd service has automatic restart enabled. Check logs:
```bash
journalctl --user -u temp-monitor.service -n 100
tail -50 ~/.temp_monitor.log
```

### Want to see current temperatures

Run the original console monitor:
```bash
/home/yonatan/dev/sys_crash_analysis/monitor_temps.sh
```

---

## Files Overview

- **temp_monitor_gui.sh** - Main monitoring script with GUI notifications
- **monitor_temps.sh** - Console-based temperature display
- **temp-monitor.service** - Systemd service file
- **temp-monitor.desktop** - Autostart desktop entry
- **~/.temp_monitor.log** - Log file (created automatically)
- **~/.temp_monitor.pid** - PID file to prevent duplicate instances

---

## Recommended: Apply Kernel Workarounds

The temperature monitor is a safety measure, but you should also apply the kernel workarounds to improve stability:

```bash
sudo nano /etc/default/grub
```

Modify this line:
```
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash acpi_ec_no_wakeup i915.enable_psr=0"
```

Then update GRUB:
```bash
sudo update-grub
sudo reboot
```

This helps with:
- `acpi_ec_no_wakeup` - May help with EC communication issues
- `i915.enable_psr=0` - Fixes the graphics cursor update failures

---

## Monitoring System Health

### Check temperatures anytime:
```bash
cat /sys/class/thermal/thermal_zone*/temp | awk '{print $1/1000 " C"}'
```

### View monitor statistics:
```bash
grep -E "WARNING|CRITICAL" ~/.temp_monitor.log | tail -20
```

### See when temperatures were highest:
```bash
grep "max temperature" ~/.temp_monitor.log | sort -k7 -n | tail -10
```

---

## When to Take Action

- **< 80°C**: Normal operation, no action needed
- **80-85°C**: Elevated, ensure good ventilation, use cooling pad
- **85-90°C**: High, close demanding applications, check for dust in vents
- **90-95°C**: Critical, immediately close applications and let cool down
- **> 95°C**: Extreme danger, shut down system to prevent damage/hang

---

## Future BIOS Updates

Periodically check for BIOS updates that might fix the ACPI/EC issues:
```bash
# Check current BIOS version
sudo dmidecode -t bios | grep Version

# Visit Lenovo support:
# https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/thinkpad-edge-laptops/thinkpad-e14-gen-7-type-21sx-21sy/downloads
```

Once Lenovo releases a BIOS update that fixes EC access, you may be able to:
- Disable this temperature monitor
- Use standard thermal management tools
- Have automatic fan control working properly

---

**Last Updated:** 2026-02-06
