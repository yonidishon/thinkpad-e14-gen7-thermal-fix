# ThinkPad E14 Gen 7 System Hang Analysis & Monitoring

## ✅ MAJOR FIX - March 19, 2026

**BIOS updated (r30uj55wd.iso) — ACPI/EC issue resolved.**

The ACPI/EC communication failure that prevented thermal sensor reading and fan control is fixed. `thinkpad_acpi` now loads fully: `/proc/acpi/ibm/thermal` and `/proc/acpi/ibm/fan` are available. The BIOS controls the fan automatically. Custom temperature monitoring scripts are no longer needed.

**Also: kernel updated to 6.17.0-19-generic** (was 6.17.0-14). i915 PSR/DSB kernel parameters removed — no errors observed so far, still under observation.

---

## ⚠️ Previous update - March 17, 2026

**Fifth hang: Extended idle GPU hang — sleep inhibitors blocked `IdleAction=suspend`.**

Despite `IdleAction=suspend` being configured, the system ran for 3+ days without suspending because **Google Antigravity** and GNOME Shell hold persistent `sleep` inhibitors that block logind's idle action. Fixed by adding `IdleActionIgnoreInhibitors=yes` to logind.conf.

**Previous (March 12):** GDM authentication service failure after lid open. Fixed with `IdleAction=suspend` + `IdleActionSec=20min`.

**Previous (March 9):** i915 GPU hard hang after ~37hr idle on lock screen. Auto-suspend was disabled on AC.

---

## Executive Summary

Your ThinkPad E14 Gen 7 (Model: 21SX005CIV) has experienced multiple types of system freezes:

### Crash Type 1: Thermal + Graphics (Original Issue)

Analysis of earlier system logs revealed a **compound hardware/software issue**:

1. **ACPI/EC Communication Failure** (Primary) - **✅ RESOLVED 2026-03-19 via BIOS update r30uj55wd.iso**
   - ~~ThinkPad ACPI Embedded Controller cannot be accessed~~
   - EC now fully operational; BIOS controls fan automatically
   - `/proc/acpi/ibm/thermal` and `/proc/acpi/ibm/fan` now available

2. **Intel i915 Graphics Driver Issues** (Secondary)
   - Multiple "Cursor update failed: drmModeAtomicCommit" errors
   - Intel Arrow Lake-P (Core Ultra 7 255H) is very new hardware
   - Driver support still maturing in Linux kernel
   - **Result:** Graphics driver instability (mitigated by kernel params + auto-suspend)

**Previous combined effect:** System runs for hours → Components overheat silently → GPU becomes unstable → **Complete system freeze**

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

**Fix:** `i915.enable_dsb=0` kernel parameter. Mesa downgrade was attempted but did NOT fix it (DSB is kernel-level). See [`Analysis_Process.md`](./Analysis_Process.md) for full investigation.

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

3. **No Thermal Management** (Contributing Factor, now resolved)
   - ACPI/EC was broken at the time, no fan control
   - 446 network route changes from USB ethernet flapping, each triggering compositor updates

**Fix:** Auto-suspend after 20min idle on AC. Created `post_hang_analysis.py` for future diagnostics.

### Crash Type 4: GDM Auth Failure After Lid Open (Mar 12, 2026)

1. **GDM DBus Connection Failure** (Primary)
   - Lid opened after extended idle → display reconfiguration triggered
   - gnome-shell lost DBus connection to GDM auth service 8 seconds later
   - Lock screen kept rendering (GPU compositor fine), but input was rejected
   - Mouse cursor moved normally; keyboard and clicks completely unresponsive

2. **No Auto-Suspend Despite Clamshell Idle** (Enabling Factor)
   - External monitor connected via USB dock → GNOME's `gsd-power` inhibits auto-suspend
   - `sleep-inactive-ac-type=suspend` in gsettings has NO effect in clamshell mode
   - System ran 24h without suspending with lid closed

**Fix:** `IdleAction=suspend` + `IdleActionSec=20min` in `/etc/systemd/logind.conf` — operates below the GNOME layer, not affected by clamshell inhibitor.

---

## System Information

- **Model:** Lenovo ThinkPad E14 Gen 7 (21SX005CIV)
- **CPU:** Intel Core Ultra 7 255H (Arrow Lake-P)
- **GPU:** Intel Arrow Lake-P Integrated Graphics (i915 driver)
- **RAM:** 30GB
- **OS:** Ubuntu 24.04.3 LTS
- **Kernel:** 6.17.0-19-generic (HWE)
- **BIOS:** Updated 2026-03-19 via r30uj55wd.iso (was R30ET38W v1.12)

---

## BIOS Update Status

✅ **BIOS updated 2026-03-19 — EC issue resolved**

- Updated via: r30uj55wd.iso (downloaded from Lenovo support)
- Previous version: R30ET38W v1.12
- **Result:** ACPI/EC now fully functional. `thinkpad_acpi` loads correctly, fan control and thermal sensors available.

**Check for future updates periodically:**
- https://pcsupport.lenovo.com/us/en/products/laptops-and-netbooks/thinkpad-edge-laptops/thinkpad-e14-gen-7-type-21sx-21sy/downloads

---

## Files in This Directory

### Analysis Reports
- **`Analysis_Process.md`** - Complete Feb 7 DSB crash investigation (historical reference)
- **`post_hang_analysis.py`** - Post-reboot analysis script. Run after any hard reset.
- **`reports/`** - JSON reports from post-hang analysis runs
- **`README.md`** - This file

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

### 1. Kernel parameters

As of 2026-03-19, no special kernel parameters are required:
```
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
```

Both `acpi_ec_no_wakeup` (EC workaround) and `i915.enable_psr=0` / `i915.enable_dsb=0` (i915 workarounds) were removed after the BIOS update and kernel upgrade to 6.17.0-19. No errors observed so far — still under observation.

If cursor/DSB errors return, re-add the i915 params:
```bash
sudo nano /etc/default/grub
# Set: GRUB_CMDLINE_LINUX_DEFAULT="quiet splash i915.enable_psr=0 i915.enable_dsb=0"
sudo update-grub && sudo reboot
```

### 2. Temperature Monitoring (now optional)

**With the BIOS update, the EC is fixed and the BIOS handles fan control automatically.** The custom monitoring scripts are no longer needed for safety.

To check temperatures directly:
```bash
cat /proc/acpi/ibm/thermal   # ThinkPad thermal zones
cat /proc/acpi/ibm/fan       # Fan status and speed
```

If you still want GUI popup warnings, the legacy scripts remain available:
```bash
cd /home/yonatan/dev/sys_crash_analysis
./install_temp_monitor.sh
```

### 3. Configure Auto-Suspend (IMPORTANT)

Prevents i915 GPU / GDM from running idle for extended periods. **Must use logind — GNOME-only settings don't work in clamshell mode (external monitor connected).**

Edit `/etc/systemd/logind.conf` and ensure these lines are set (uncommented):
```
HandleLidSwitch=lock
HandlePowerKeyLongPress=poweroff
IdleAction=suspend
IdleActionSec=20min
IdleActionIgnoreInhibitors=yes
```

- `HandlePowerKeyLongPress=poweroff` — enables long-pressing the power button to force power off (useful when system is partially responsive but logind is still alive; does NOT help for complete freezes where logind itself is hung — use the pinhole reset button for those)

Then **reboot** (never `sudo systemctl restart systemd-logind` — this kills the Wayland session and causes a hang).

Also apply GNOME settings for battery and lid-close behavior:
```bash
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'suspend'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout 1200
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'suspend'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-timeout 1200
gsettings set org.gnome.settings-daemon.plugins.power lid-close-ac-action 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power lid-close-battery-action 'nothing'
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

### ✅ Thermal Management - RESOLVED (2026-03-19)

BIOS update r30uj55wd.iso fixed the ACPI/EC communication failure.

```bash
cat /proc/acpi/ibm/thermal   # e.g. "temperatures: 51 46 0 45 41 32 0 -128"
cat /proc/acpi/ibm/fan       # e.g. "status: enabled / speed: 0 / level: auto"
```

Fan is controlled automatically by the BIOS (`level: auto`). No manual intervention needed.

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

### Current state (2026-03-19):
- ✓ EC fixed — fan and thermal sensors working via thinkpad_acpi
- ✓ Auto-suspend after 20min idle via logind (bypasses sleep inhibitors)
- ✓ No special kernel parameters needed — i915 params removed, no errors so far
- ✓ Post-hang analysis script available for future incidents
- ⏳ i915 params removal under observation — re-add if cursor/DSB errors return

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

- ✓ Analysis complete (4 crash types identified)
- ✓ Root causes identified for all crash types
- ✓ BIOS updated — ACPI/EC fixed (2026-03-19)
- ✓ Kernel workarounds documented and applied
- ✓ Auto-suspend configured (logind IdleAction, bypasses sleep inhibitors)
- ✓ Post-hang analysis script available for future incidents
- ✓ Mesa upgraded to 26.0.1 (clean boot, no new errors)
- ⏳ i915 PSR/DSB params removed — monitoring for regressions

**Last Updated:** 2026-03-19

---

## Contact

For questions about this analysis or the monitoring tools, refer to:
- `Analysis_Process.md` - Technical details of the Feb 7 DSB crash investigation
- `SETUP_INSTRUCTIONS.md` - Temperature monitor configuration
