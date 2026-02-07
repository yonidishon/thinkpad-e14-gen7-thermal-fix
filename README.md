# ThinkPad E14 Gen 7 System Hang Analysis & Monitoring

## ⚠️ LATEST UPDATE - February 7, 2026

**New crash identified with different root cause!**

The February 7 crash (flashing CAPS LOCK, kernel panic) was caused by **i915 DSB (Display State Buffer) hardware bug**, not Mesa or thermal issues.

**See:** [`Analysis_Process.md`](./Analysis_Process.md) for complete investigation and findings.

**Quick Summary:**
- Intel i915 DSB poll error on Arrow Lake-P graphics
- Causes kernel panic when closing laptop lid without suspend
- **Solution:** Disable DSB with kernel parameter `i915.enable_dsb=0` (see below)
- Mesa downgrade was attempted but did NOT fix the issue (DSB is kernel-level)

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

### Crash Type 2: Mesa 25.3.4 Regression (Feb 7, 2026)

**New finding:** Bleeding-edge Mesa driver has critical bug:

1. **Mesa 25.3.4 DSB Bug** (Primary)
   - Display State Buffer polling fails on boot
   - Monitor configuration breaks when lid closes
   - System runs in corrupted graphics state
   - **Result:** Kernel panic after hours (flashing CAPS LOCK)

2. **Lid Close Without Suspend** (Trigger)
   - Power settings: "No action" on lid close when on AC
   - GNOME tries to turn off display without suspending
   - DSB failure causes monitor manager to fail
   - **Result:** System continues in broken state → eventual panic

**Combined Effect:** Mesa DSB bug → Broken display management → Lid close triggers failures → Kernel panic

**See full investigation:** [`Analysis_Process.md`](./Analysis_Process.md)

---

## System Information

- **Model:** Lenovo ThinkPad E14 Gen 7 (21SX005CIV)
- **CPU:** Intel Core Ultra 7 255H (Arrow Lake-P)
- **GPU:** Intel Arrow Lake-P Integrated Graphics (i915 driver)
- **RAM:** 30GB
- **OS:** Ubuntu 24.04.3 LTS
- **Kernel:** 6.14.0-37-generic
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
- **`Analysis_Process.md`** - **NEW:** Complete Feb 7 crash investigation with reproducible analysis
- **`REVISED_hang_analysis.md`** - Original thermal/i915 crash analysis
- **`analyze_system_hang.py`** - Python script to analyze system logs
- **`README.md`** - This file

### Mesa Downgrade (Feb 7 Issue)
- **`downgrade_mesa.sh`** - Script to downgrade Mesa 25.3.4 → 25.2.8
- **`verify_mesa_fix.sh`** - Verification script to check after downgrade

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

### 3. Update Graphics Stack

```bash
sudo apt update
sudo apt install linux-generic-hwe-24.04 intel-microcode
sudo add-apt-repository ppa:kisak/kisak-mesa
sudo apt update && sudo apt upgrade
sudo reboot
```

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

- ✓ Analysis complete
- ✓ Root causes identified
- ✓ Temperature monitoring implemented
- ✓ Kernel workarounds documented
- ⏳ Waiting for BIOS fix from Lenovo
- ⏳ Waiting for better kernel support for Arrow Lake

**Last Updated:** 2026-02-07

---

## Contact

For questions about this analysis or the monitoring tools, refer to:
- `REVISED_hang_analysis.md` - Technical details
- `SETUP_INSTRUCTIONS.md` - Temperature monitor configuration
