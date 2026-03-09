# ThinkPad E14 Gen 7 System Hang Analysis & Monitoring

## ⚠️ LATEST UPDATE - March 9, 2026

**Third hang type identified: i915 GPU hard hang during extended idle.**

System froze after ~37 hours of idle operation on the lock screen. Keyboard/mouse completely unresponsive, required hard reset. Root cause: i915 GPU driver entered an unrecoverable state while rendering the lock screen for an extended period, compounded by no thermal management and no auto-suspend.

**Fixes applied:**
- ✓ Auto-suspend after 20min idle on AC and battery (was previously disabled on AC)
- ✓ Lid close = lock only (no suspend), per user preference
- ✓ Mesa upgraded 25.2.8 → 26.0.1, XWayland 23.2.6 → 24.1.6 (clean boot)
- ✓ Created `post_hang_analysis.py` for automated post-crash diagnostics

**Previous:** February 7 crash (flashing CAPS LOCK, kernel panic) was caused by **i915 DSB (Display State Buffer) hardware bug**.

**See:** [`Analysis_Process.md`](./Analysis_Process.md) for previous investigation details.

---

## Executive Summary

Your ThinkPad E14 Gen 7 (Model: 21SX005CIV) has experienced multiple types of system freezes:

### Crash Type 1: Thermal + Graphics (Original Issue)

Analysis of earlier system logs revealed a **compound hardware/software issue**:

1. **ACPI/EC Communication Failure** (Primary)
   - ThinkPad ACPI Embedded Controller cannot be accessed
   - Prevents thermal sensor reading
   - Prevents fan speed control
   - Thermal daemon cannot run (unsupported CPU)
   - **Result:** System has NO thermal management

2. **Intel i915 Graphics Driver Issues** (Secondary)
   - Multiple "Cursor update failed: drmModeAtomicCommit" errors
   - Intel Arrow Lake-P (Core Ultra 7 255H) is very new hardware
   - Driver support still maturing in Linux kernel
   - **Result:** Graphics driver instability

**Combined Effect:** System runs for hours → Components overheat silently (no monitoring) → GPU becomes unstable → i915 driver hangs → **Complete system freeze**

### Crash Type 2: i915 DSB Kernel Panic (Feb 7, 2026)

1. **i915 DSB Bug** (Primary)
   - Display State Buffer polling fails on boot
   - Monitor configuration breaks when lid closes
   - System runs in corrupted graphics state
   - **Result:** Kernel panic after hours (flashing CAPS LOCK)

2. **Lid Close Without Suspend** (Trigger)
   - GNOME tries to turn off display without suspending
   - DSB failure causes monitor manager to fail
   - **Result:** System continues in broken state → eventual panic

**Fix:** `i915.enable_dsb=0` kernel parameter. Mesa downgrade was attempted but did NOT fix it (DSB is kernel-level).

**See full investigation:** [`Analysis_Process.md`](./Analysis_Process.md)

### Crash Type 3: Extended Idle GPU Hang (Mar 9, 2026)

1. **i915 GPU Hard Hang** (Primary)
   - System idle on lock screen for ~37 hours
   - Cursor/atomic update failures were early precursors
   - GPU entered unrecoverable state, froze entire system including journald
   - No kernel panic logged (freeze at hardware/driver level)

2. **No Auto-Suspend on AC** (Enabling Factor)
   - GNOME `sleep-inactive-ac-type` was set to `nothing`
   - System never suspended despite being idle for days
   - GPU continuously rendered lock screen animations

3. **No Thermal Management** (Contributing Factor)
   - ACPI/EC broken, no fan control
   - 446 network route changes from USB ethernet flapping, each triggering compositor updates

**Fix:** Auto-suspend after 20min idle on AC. Created `post_hang_analysis.py` for future diagnostics.

---

## System Information

- **Model:** Lenovo ThinkPad E14 Gen 7 (21SX005CIV)
- **CPU:** Intel Core Ultra 7 255H (Arrow Lake-P)
- **GPU:** Intel Arrow Lake-P Integrated Graphics (i915 driver)
- **RAM:** 30GB
- **OS:** Ubuntu 24.04.3 LTS
- **Kernel:** 6.17.0-14-generic (HWE)
- **BIOS:** R30ET38W v1.12 (Latest available - 10/30/2025)
- **EC Firmware:** R30HT38W v1.12

---

## BIOS Update Status

✓ **You are already running the latest BIOS version (1.12)**

- Latest available from Lenovo: R30ET38W v1.12 / R30HT38W v1.12
- Your current version: Same ✓
- **No newer BIOS available as of 2026-02-06**
- The ACPI/EC bug exists in the latest firmware
- Lenovo has not yet released a fix for Linux EC access issues

**Check for updates periodically:**
- https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/thinkpad-edge-laptops/thinkpad-e14-gen-7-type-21sx-21sy/downloads

---

## Files in This Directory

### Analysis Reports
- **`Analysis_Process.md`** - Complete Feb 7 crash investigation with reproducible analysis
- **`REVISED_hang_analysis.md`** - Original thermal/i915 crash analysis
- **`analyze_system_hang.py`** - Python script to analyze system logs
- **`post_hang_analysis.py`** - **NEW:** Post-reboot analysis for i915/thermal/idle hangs. Run after hard reset.
- **`reports/`** - JSON reports from post-hang analysis runs
- **`README.md`** - This file

### Mesa / Graphics
- **`downgrade_mesa.sh`** - Script to downgrade Mesa (historical, no longer needed)
- **`verify_mesa_fix.sh`** - Verification script to check GPU/Mesa status

### Temperature Monitoring
- **`temp_monitor_gui.sh`** - GUI temperature monitor with popup warnings (logs every minute)
- **`monitor_temps.sh`** - Console temperature monitor (updates every 2 seconds)
- **`cpu_stress_test.py`** - CPU stress testing tool for thermal testing
- **`temp-monitor.service`** - Systemd service file for automatic startup
- **`temp-monitor.desktop`** - Autostart desktop entry
- **`install_temp_monitor.sh`** - Quick installation script
- **`SETUP_INSTRUCTIONS.md`** - Complete setup and configuration guide

---

## Quick Start

### 0. Fix DSB Issue (If Experiencing Kernel Panics on Lid Close)

**Symptoms:** Kernel panic (flashing CAPS LOCK) after closing laptop lid

**Root Cause:** Intel i915 Display State Buffer (DSB) poll error - hardware communication failure

**Solution:** Disable DSB via kernel parameter (add `i915.enable_dsb=0` in step 1 above)

**What We Tried:**
- ❌ Mesa downgrade from 25.3.4 → 25.2.8: DSB error persisted
- ✓ Kernel parameter `i915.enable_dsb=0`: Fixes the issue

**Why Mesa downgrade didn't work:**
- DSB is a **kernel driver feature** (i915), not a Mesa userspace feature
- The error occurs during driver initialization, before Mesa is involved
- DSB issue exists in both Mesa 25.3.4 and 25.2.8

**Verification after applying kernel parameter:**
```bash
sudo dmesg | grep -i 'DSB.*error'  # Should return nothing after reboot
```

See [`Analysis_Process.md`](./Analysis_Process.md) for complete investigation details.

---

### 1. Apply Kernel Workarounds (REQUIRED)

```bash
sudo nano /etc/default/grub
```

Change this line to:
```
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash acpi_ec_no_wakeup i915.enable_psr=0 i915.enable_dsb=0"
```

Then:
```bash
sudo update-grub
sudo reboot
```

**What this does:**
- `acpi_ec_no_wakeup` - May help with EC communication issues
- `i915.enable_psr=0` - Disables Panel Self Refresh (fixes cursor update failures)
- `i915.enable_dsb=0` - **[REQUIRED]** Disables Display State Buffer (fixes DSB poll error and kernel panics)

### 2. Install Temperature Monitor

```bash
cd /home/yonatan/dev/sys_crash_analysis
./install_temp_monitor.sh
```

This will:
- Install required dependencies (libnotify-bin)
- Let you choose between systemd service or autostart
- Start the monitor immediately
- Show GUI popup warnings when temps exceed 85°C
- Show critical alerts when temps exceed 90°C

### 3. Configure Auto-Suspend (IMPORTANT)

Prevents i915 GPU from running idle for extended periods (which causes hard hangs):

```bash
# Auto-suspend after 20min idle (AC and battery)
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'suspend'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout 1200
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'suspend'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-timeout 1200

# Lid close: lock only, no suspend
gsettings set org.gnome.settings-daemon.plugins.power lid-close-ac-action 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power lid-close-battery-action 'nothing'
```

Also ensure `/etc/systemd/logind.conf` has:
```
HandleLidSwitch=lock
```

### 4. Update Graphics Stack

```bash
sudo apt update
sudo apt install linux-generic-hwe-24.04 intel-microcode
sudo add-apt-repository ppa:kisak/kisak-mesa
sudo apt update && sudo apt upgrade
sudo reboot
```

### 5. After a System Hang (Hard Reset)

Run immediately after reboot to capture diagnostics:
```bash
sudo python3 post_hang_analysis.py --save
```
This analyzes the previous boot's logs for GPU errors, thermal failures, idle state, and more. Reports saved to `reports/`.

---

## How to Use

### Check Current Temperatures
```bash
./monitor_temps.sh
```

### View Temperature Monitor Logs
```bash
tail -f ~/.temp_monitor.log
```

### Check Monitor Status (if using systemd)
```bash
systemctl --user status temp-monitor.service
```

### Manually Check Temps
```bash
cat /sys/class/thermal/thermal_zone*/temp | awk '{print $1/1000 " C"}'
```

---

## Known Issues

### ❌ Thermal Management Broken
```
thinkpad_acpi: ThinkPad ACPI EC access misbehaving, disabling thermal sensors access
thinkpad_acpi: fan status and control unavailable
thermald: Unsupported cpu model or platform
```

**Impact:**
- Cannot read CPU/GPU temperatures via thinkpad_acpi
- Cannot control fan speed
- Thermal daemon cannot run
- System may overheat silently

**Workaround:**
- Use the temperature monitor scripts in this directory
- Ensure good physical ventilation
- Use laptop cooling pad
- Monitor temps regularly

### ⚠️ Graphics Driver Instability
```
gnome-shell: Cursor update failed: drmModeAtomicCommit: Invalid argument
```

**Impact:**
- Graphics driver may hang after extended use
- Can cause complete system freeze

**Workaround:**
- Disable PSR with `i915.enable_psr=0` kernel parameter
- Keep kernel updated (newer kernels have better Arrow Lake support)
- Consider switching to X11 if Wayland issues persist

---

## Temperature Guidelines

| Temperature | Status | Action |
|------------|--------|--------|
| < 85°C | ✓ Normal | No action needed |
| 85-90°C | ⚠️ Warning | Ensure good ventilation, monitor load |
| 90-95°C | 🔥 Critical | Close apps immediately, let cool down |
| > 95°C | 🚨 Extreme | Shut down to prevent damage/hang |

---

## Disable Temperature Monitor

### If using systemd:
```bash
systemctl --user stop temp-monitor.service
systemctl --user disable temp-monitor.service
```

### If using autostart:
```bash
rm ~/.config/autostart/temp-monitor.desktop
pkill -f temp_monitor_gui.sh
```

See `SETUP_INSTRUCTIONS.md` for complete details.

---

## Expected Outcomes

### With Workarounds Applied:
- ✓ PSR disabled should eliminate cursor update failures
- ✓ Temperature monitoring provides early warning
- ✓ System should run more stable (but still at risk from thermal issues)
- ⚠️ Fan control still unavailable (hardware limitation)
- ⚠️ No automatic thermal management (manual monitoring required)

### Long-term Solution Waiting On:
- Lenovo BIOS update to fix EC access
- Kernel updates with better Arrow Lake support
- Ubuntu 24.04.1+ with newer drivers

---

## Reporting Issues

### To Lenovo (for ACPI/EC bug):
- Reference: ThinkPad E14 Gen 7 Linux ACPI EC access failure
- Model: 21SX005CIV
- Include: `dmesg | grep -i "thinkpad_acpi\|acpi.*error"`

### To Kernel Developers (for i915 issues):
- Component: Intel i915 graphics driver
- Hardware: Arrow Lake-P (Intel Core Ultra 7 255H)
- Include: `dmesg | grep -i i915`

---

## Additional Resources

- **Lenovo Support:** https://pcsupport.lenovo.com
- **ThinkWiki Thermal Sensors:** https://www.thinkwiki.org/wiki/Thermal_Sensors
- **Bug #220796:** thinkpad-acpi fan not working on E14 Gen 7

---

## Maintenance

### Weekly Checks
```bash
# Check for BIOS updates
sudo dmidecode -t bios | grep Version

# Review temperature logs
grep -E "WARNING|CRITICAL" ~/.temp_monitor.log | tail -20

# Check for kernel updates
apt list --upgradable | grep linux
```

### Monthly Checks
- Check Lenovo support for BIOS updates
- Review kernel changelog for i915/thermal improvements
- Clean laptop vents and fans (if accessible)

---

## Status

- ✓ Analysis complete (3 crash types identified)
- ✓ Root causes identified for all crash types
- ✓ Temperature monitoring implemented
- ✓ Kernel workarounds documented and applied
- ✓ Auto-suspend configured to prevent extended idle GPU hangs
- ✓ Post-hang analysis script created for future incidents
- ✓ Mesa upgraded to 26.0.1 (clean boot, no new errors)
- ⏳ Waiting for BIOS fix from Lenovo (ACPI/EC)
- ⏳ Waiting for i915 driver fixes for Arrow Lake in future kernels

**Last Updated:** 2026-03-09

---

## Contact

For questions about this analysis or the monitoring tools, refer to:
- `REVISED_hang_analysis.md` - Technical details
- `SETUP_INSTRUCTIONS.md` - Temperature monitor configuration
