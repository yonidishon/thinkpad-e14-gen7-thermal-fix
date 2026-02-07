# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working Guidelines for Claude Code

**CRITICAL: These are permanent instructions that must be followed in every session:**

1. **Always use `sudo` for system diagnostic commands**:
   - `dmesg` requires root privileges on Ubuntu 24.04
   - When checking kernel logs, always use `sudo dmesg`, never just `dmesg`
   - Verification scripts that check dmesg must use `sudo` to avoid false negatives

2. **Document findings as we work**:
   - Update CLAUDE.md with new discoveries about hardware issues
   - Record attempted fixes and their outcomes
   - Maintain accurate kernel parameter documentation
   - Add new workarounds to the "System Workarounds Applied" section

3. **User preferences**:
   - No unnecessary scripts - provide direct instructions when possible
   - User will run commands manually when given clear guidance
   - Focus on documentation over automation

## Project Overview

This repository contains diagnostic and monitoring tools for analyzing and mitigating system hangs on a ThinkPad E14 Gen 7 (Model 21SX005CIV) running Ubuntu 24.04. The laptop suffers from two hardware/firmware issues:

1. **ACPI/EC Communication Failure**: ThinkPad ACPI Embedded Controller access fails, preventing thermal sensor reading and fan control
2. **Intel i915 Graphics Driver Instability**: Arrow Lake-P (Core Ultra 7 255H) graphics have cursor update failures causing system freezes

The combined effect is that the system can overheat silently (no thermal management) while the GPU driver becomes unstable, leading to complete system freezes after hours of operation.

## Core Tools

### System Analysis
- **`analyze_system_hang.py`**: Comprehensive Python script that analyzes system logs (journalctl, dmesg) to identify causes of freezes. Checks for kernel panics, OOM events, graphics issues, hardware errors, thermal problems, disk errors, and CPU lockups.

### Temperature Monitoring
Since the ACPI/EC bug prevents normal thermal management, custom monitoring scripts compensate:

- **`temp_monitor_gui.sh`**: Background daemon that monitors `/sys/class/thermal/thermal_zone*/temp` every 10 seconds and shows desktop notifications when temperatures exceed thresholds (warning at 85°C, critical at 90°C). Includes cooldown logic to prevent notification spam.
- **`monitor_temps.sh`**: Interactive console monitor that displays real-time temperatures with color-coded output, refreshing every 2 seconds.
- **`cpu_stress_test.py`**: Multi-process CPU stress testing tool using math operations (sqrt, sin, cos, powers) to generate heat for thermal testing.

### Graphics Driver Diagnostics
- **`verify_mesa_fix.sh`**: Verification script that checks Mesa/XWayland versions, DSB errors, and package hold status. **IMPORTANT:** Uses `sudo dmesg` for accurate kernel log checking (dmesg requires root on Ubuntu 24.04).
- **`downgrade_mesa.sh`**: Script that downgrades Mesa and XWayland packages from Kisak PPA to Ubuntu stable versions (attempted fix for DSB errors - was unsuccessful).

### Installation & Setup
- **`install_temp_monitor.sh`**: Interactive installer that offers systemd service or autostart desktop entry installation methods for the temperature monitor.
- **`temp-monitor.service`**: Systemd user service configuration for running the GUI monitor as a background service.
- **`temp-monitor.desktop`**: XDG autostart desktop entry for starting the monitor on login.

## Architecture

### Temperature Monitoring System
The monitoring system works around broken hardware by reading kernel thermal zones directly:

1. **Data Source**: `/sys/class/thermal/thermal_zone*/temp` (millicelsius format)
2. **State Tracking**: Uses timestamp-based cooldown (`last_warning_time`, `last_critical_time`) to prevent notification spam (5-minute cooldown between repeats)
3. **PID Management**: `temp_monitor_gui.sh` uses a PID file (`~/.temp_monitor.pid`) to prevent multiple instances
4. **Logging**: All events logged to `~/.temp_monitor.log` with timestamps
5. **Notifications**: Multi-method approach using `notify-send` (non-blocking) and `zenity` (blocking for critical alerts)

### System Analysis Workflow
The `analyze_system_hang.py` script follows this pattern:
1. Check if running as root (warns if not, since some logs require privileges)
2. Query system info (CPU, GPU, memory, boot times)
3. Run independent checks in sequence (kernel panics, OOM, hardware errors, graphics, thermal, disk, CPU lockup, suspend/resume)
4. Display last 50 messages from previous boot
5. Color-coded output using ANSI escape codes (red for errors, yellow for warnings, green for success)

## Common Commands

### Running System Analysis
```bash
# Basic analysis (may have limited info)
python3 analyze_system_hang.py

# Full analysis with all permissions
sudo python3 analyze_system_hang.py
```

### Temperature Monitoring
```bash
# Install monitor (interactive - choose systemd or autostart)
./install_temp_monitor.sh

# View real-time console temperatures
./monitor_temps.sh

# Check GUI monitor status (systemd method)
systemctl --user status temp-monitor.service

# View temperature logs
tail -f ~/.temp_monitor.log

# Stop monitor
systemctl --user stop temp-monitor.service  # systemd method
pkill -f temp_monitor_gui.sh                # autostart method

# Manually check current temperatures
cat /sys/class/thermal/thermal_zone*/temp | awk '{print $1/1000 " C"}'
```

### CPU Stress Testing
```bash
# Interactive stress test (will prompt for confirmation)
python3 cpu_stress_test.py -d 60

# Stress specific number of cores
python3 cpu_stress_test.py -c 4 -d 30

# Gradual ramp-up test
python3 cpu_stress_test.py -d 60 --ramp-up

# Quick 10-second test
python3 cpu_stress_test.py --quick
```

## System Workarounds Applied

### Kernel Parameters (GRUB Configuration)

The laptop requires these kernel parameters in `/etc/default/grub`:
```
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash acpi_ec_no_wakeup i915.enable_psr=0 i915.enable_dsb=0"
```

**Parameter explanations:**
- `acpi_ec_no_wakeup`: Attempts to mitigate EC communication issues
- `i915.enable_psr=0`: Disables Panel Self Refresh to fix cursor update failures
- `i915.enable_dsb=0`: **[REQUIRED]** Disables Display State Buffer to fix DSB poll errors

After modifying GRUB config, always run:
```bash
sudo update-grub
sudo reboot
```

### DSB (Display State Buffer) Issue - Diagnosis and Fix

**Problem:** Arrow Lake-P graphics (Core Ultra 7 255H) produces DSB poll errors:
```
[drm] *ERROR* [CRTC:88:pipe A] DSB 0 poll error
```

**Attempted Fix #1 - Mesa Downgrade (UNSUCCESSFUL):**
- Downgraded Mesa from 25.3.4 (Kisak PPA) to 25.2.8 (Ubuntu stable)
- Downgraded XWayland from 24.1.6 to 23.2.6
- Held packages to prevent auto-upgrade
- **Result:** DSB error persisted after downgrade and reboot
- **Conclusion:** DSB issue is in the kernel i915 driver, not Mesa userspace

**Working Fix - Disable DSB in Kernel:**
- Added `i915.enable_dsb=0` to GRUB kernel parameters
- This disables the Display State Buffer feature in i915 driver
- Trade-off: Slightly higher power consumption, but eliminates DSB errors
- **Verification:** After reboot, check with `sudo dmesg | grep -i 'DSB.*error'`

### Mesa/XWayland Package Holds

The following packages are held at older versions to prevent Kisak PPA upgrades:
```bash
sudo apt-mark hold mesa-vulkan-drivers libegl-mesa0 libgl1-mesa-dri \
  mesa-va-drivers mesa-vdpau-drivers libglx-mesa0 mesa-libgallium xwayland
```

To check hold status: `apt-mark showhold | grep -E "mesa|xwayland"`

To unhold if needed: `sudo apt-mark unhold <package-name>`

## Temperature Thresholds

| Temperature | Status | Action |
|------------|--------|--------|
| < 85°C | Normal | No action needed |
| 85-90°C | Warning | GUI notification, ensure good ventilation |
| 90-95°C | Critical | Blocking popup, close apps immediately |
| > 95°C | Extreme | System may hang, shut down to prevent damage |

## Key Limitations

Due to hardware/firmware bugs:
- **No fan control**: Cannot programmatically adjust fan speed
- **No thinkpad_acpi sensors**: Standard ThinkPad thermal sensors unavailable
- **No thermald support**: Thermal daemon doesn't support Arrow Lake CPU
- **Manual monitoring required**: Must rely on custom scripts to prevent overheating

## Testing

When modifying monitoring scripts:
1. Test notification system: `notify-send "Test" "This is a test"`
2. Verify thermal zone access: `ls /sys/class/thermal/thermal_zone*/temp`
3. Check log file creation: `tail ~/.temp_monitor.log`
4. Ensure PID file cleanup on exit
5. Test with actual CPU load using `cpu_stress_test.py`

## Dependencies

- **Python 3**: Required for `analyze_system_hang.py` and `cpu_stress_test.py`
- **libnotify-bin**: Required for desktop notifications (`notify-send`)
- **zenity** (optional): Used for blocking critical temperature alerts
- **paplay** (optional): Plays alert sounds for critical warnings

Install missing dependencies:
```bash
sudo apt install libnotify-bin zenity pulseaudio-utils
```

## Documentation Files

- **README.md**: User-facing quick start guide with BIOS update status and temperature guidelines
- **SETUP_INSTRUCTIONS.md**: Detailed installation and troubleshooting for temperature monitor
- **REVISED_hang_analysis.md**: Complete technical analysis of the root causes (ACPI/EC bug + i915 instability)
