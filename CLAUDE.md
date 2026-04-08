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

This repository contains diagnostic and monitoring tools for analyzing and mitigating system hangs on a ThinkPad E14 Gen 7 (Model 21SX005CIV) running Ubuntu 24.04. The laptop has experienced hangs due to:

1. **ACPI/EC Communication Failure**: ~~ThinkPad ACPI Embedded Controller access fails~~ **RESOLVED 2026-03-19** - BIOS updated via r30uj55wd.iso. EC now fully operational: `/proc/acpi/ibm/fan` and `/proc/acpi/ibm/thermal` available, fan control handled by BIOS automatically.
2. **Intel i915 Graphics Driver Instability**: Arrow Lake-P (Core Ultra 7 255H) graphics have cursor update failures. Mitigated via kernel parameters; may be resolved in kernel 6.17.0-19 (not yet confirmed).

## Core Tools

### System Analysis
- **`analyze_system_hang.py`**: Comprehensive Python script that analyzes system logs (journalctl, dmesg) to identify causes of freezes. Checks for kernel panics, OOM events, graphics issues, hardware errors, thermal problems, disk errors, and CPU lockups.

### Temperature Monitoring
**Note (2026-03-19):** With the BIOS update fixing the EC, `thinkpad_acpi` now provides proper thermal sensors and fan control. The custom monitoring scripts below are no longer necessary for safety - the BIOS controls the fan automatically. They remain in the repo for reference but can be safely ignored.

- **`temp_monitor_gui.sh`**: Background daemon that monitors `/sys/class/thermal/thermal_zone*/temp` every 10 seconds and shows desktop notifications when temperatures exceed thresholds (warning at 85°C, critical at 90°C).
- **`monitor_temps.sh`**: Interactive console monitor that displays real-time temperatures with color-coded output, refreshing every 2 seconds.
- **`cpu_stress_test.py`**: Multi-process CPU stress testing tool using math operations (sqrt, sin, cos, powers) to generate heat for thermal testing.

To check temperatures now use: `cat /proc/acpi/ibm/thermal` or `cat /proc/acpi/ibm/fan`.

### Post-Hang Analysis
- **`post_hang_analysis.py`**: Comprehensive post-reboot analysis script designed to run immediately after a hard reset. Analyzes the previous boot's journalctl logs to identify: i915 GPU errors (cursor failures, atomic update failures, DSB errors, GPU hangs), ACPI/EC thermal failures, lid/suspend state, kernel lockups, OOM events, and network interface churn. Outputs root cause determination with severity rating and actionable recommendations. Supports `--save` (JSON report to `reports/`) and `--json` (stdout) output modes.

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

### Post-Hang Analysis (run after hard reset)
```bash
# Full analysis of previous boot that caused the hang
sudo python3 post_hang_analysis.py

# Save report as JSON for future reference
sudo python3 post_hang_analysis.py --save

# Machine-readable JSON output
sudo python3 post_hang_analysis.py --json
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

Current kernel parameters in `/etc/default/grub`:
```
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash i915.enable_psr=0 i915.enable_dsb=0 i915.enable_dc=0"
```

**Removed 2026-03-19:** `acpi_ec_no_wakeup` - EC workaround, no longer needed after BIOS update.

**[REQUIRED]** `i915.enable_psr=0` and `i915.enable_dsb=0` — i915 atomic update failures confirmed on kernel 6.17.0-19 (2026-03-20). These params are still needed. Not fixed by kernel update.

**[REQUIRED]** `i915.enable_dc=0` — added 2026-03-22 after kernel panic ~25min post-resume from s2idle. Disables Display C-states (GPU power gating during suspend/resume). Trade-off: slightly higher idle GPU power draw.

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

### Mesa/XWayland Package Status

**2026-03-09:** Mesa packages were **unholded and upgraded** from 25.2.8 to 26.0.1 (Kisak PPA). XWayland upgraded from 23.2.6 to 24.1.6. The holds were originally placed during DSB troubleshooting but are no longer needed since the DSB issue is in the kernel i915 driver, not Mesa userspace. Clean boot confirmed with Mesa 26.0.1 — no DSB/atomic/cursor errors.

To re-hold if needed:
```bash
sudo apt-mark hold mesa-vulkan-drivers libegl-mesa0 libgl1-mesa-dri \
  mesa-va-drivers mesa-vdpau-drivers libglx-mesa0 mesa-libgallium xwayland
```

### Auto-Suspend on Idle (Hang Prevention)

**2026-03-09:** Configured GNOME to auto-suspend after 20 minutes of inactivity on both AC and battery. This prevents the i915 GPU from running idle for extended periods (which caused the 2026-03-09 hang).

**Settings applied:**
```bash
# Auto-suspend after 20min idle (AC and battery)
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'suspend'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout 1200
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type 'suspend'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-battery-timeout 1200

# Lid close: lock only, no suspend (user preference)
gsettings set org.gnome.settings-daemon.plugins.power lid-close-ac-action 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power lid-close-battery-action 'nothing'
```

**logind.conf** (`/etc/systemd/logind.conf`):
```
HandleLidSwitch=lock
HandlePowerKeyLongPress=poweroff
IdleAction=suspend
IdleActionSec=20min
IdleActionIgnoreInhibitors=yes
```

**`IdleActionIgnoreInhibitors=yes`** is required because multiple apps hold `sleep` inhibitors that block `IdleAction` by default: Google Antigravity, GNOME Shell, gsd-power, gsd-media-keys. Without this, logind will never fire the idle suspend. Use `systemd-inhibit --list` to see active inhibitors.

**CRITICAL:** After editing logind.conf, always **reboot** to apply changes. NEVER run `sudo systemctl restart systemd-logind` on a running Wayland session — it kills the entire graphical session and the resulting GDM login screen will hang (2026-03-12 incident).

**Behavior:** Closing the lid locks the screen. After 20 minutes of inactivity, the system suspends (s2idle) via logind — this bypasses both the GNOME clamshell inhibitor and app sleep inhibitors.

### Suspend Guard for Long-Running Tasks

**2026-04-06:** Since `IdleActionIgnoreInhibitors=yes` bypasses normal sleep inhibitors, a systemd `ExecCondition` override blocks suspend when specific processes (e.g., Shotcut video export) are running.

**Script:** `/usr/lib/systemd/system-sleep/check-exports.sh`
```bash
#!/bin/bash
case $1 in
    pre)
        if pgrep -x melt-7 > /dev/null || pgrep -x ffmpeg > /dev/null; then
            echo "Blocking suspend: video export in progress" | systemd-cat -t check-exports
            exit 1
        fi
        ;;
esac
exit 0
```

**Override:** `/etc/systemd/system/systemd-suspend.service.d/check-exports.conf`
```ini
[Service]
ExecCondition=/usr/lib/systemd/system-sleep/check-exports.sh pre
```

**How it works:** `ExecCondition` runs before `systemd-suspend.service` starts. If it returns non-zero, the suspend is skipped entirely. logind will retry after another 20min idle period.

**Note:** The sleep hook scripts in `/usr/lib/systemd/system-sleep/` alone are NOT sufficient — newer systemd versions treat them as informational only and proceed with suspend regardless of exit code. The `ExecCondition` override is required.

**Shotcut details:** Installed via snap (`/snap/shotcut/`). During export, runs `melt-7` (MLT framework renderer), which internally uses ffmpeg. The process name is `melt-7`, not `melt`.

**To add more processes:** Add more `pgrep` checks in the script (e.g., `pgrep -x handbrake`), then `sudo systemctl daemon-reload`.

## Hang Incident Log

### 2026-03-09: i915 GPU Hard Hang During Extended Idle

**Symptom:** Lock screen displayed but keyboard/mouse completely unresponsive. Required hard reset.

**Timeline:**
- Mar 07 18:18 - Boot (kernel 6.17.0-14-generic, all kernel params applied)
- Mar 07 19:03 - First `Cursor update failed: drmModeAtomicCommit: Invalid argument`
- Mar 07 20:39 - `i915 *ERROR* Atomic update failure on pipe B`
- Mar 08 00:09 - Lid closed (final time), system idle on lock screen
- Mar 08 00:11 - Second cursor update failure (USB dock reconnection event)
- Mar 08-09 - System idle for ~31 hours, only network/cron activity
- Mar 09 07:05 - Last log entry (cron job)
- Mar 09 09:55 - Hard reset / new boot

**Root Cause:** i915 GPU driver hard hang during extended idle lock screen operation. The cursor/atomic update failures were early precursors of GPU instability. Over ~37 hours of continuous operation with the lock screen actively rendering on the GPU, the driver entered an unrecoverable state that froze the entire system including journald (no panic logged). Contributing factors: no thermal management (ACPI/EC broken), no suspend triggered (s2idle not activated despite lid being closed), and excessive network interface churn (446 route changes from USB ethernet flapping, each triggering compositor updates).

**Fixes Applied:**
1. Enabled auto-suspend after 20min idle on AC (was set to 'nothing')
2. Upgraded Mesa 25.2.8 → 26.0.1, XWayland 23.2.6 → 24.1.6 (clean boot, no new errors)
3. Removed Mesa/XWayland package holds (no longer needed)

**Analysis:** Run `sudo python3 post_hang_analysis.py` after any future hang. Report saved in `reports/`.

### 2026-03-12 (Morning): GDM Auth Failure After Extended Idle With Lid Closed

**Symptom:** Lock screen visible, **mouse responsive**, keyboard and mouse clicks unresponsive. Required hard reset.

**Timeline:**
- Mar 11 09:01 - Boot
- Mar 11 10:32 - First cursor update failure (i915, pre-existing issue)
- Mar 11 20:33 - Second cursor update failure
- Mar 11 23:37 - Lid closed, system idle overnight
- Mar 12 09:54:05 - Lid opened (user turned on remote screen)
- Mar 12 09:54:13 - gnome-shell begins spamming `Gio.IOErrorEnum: The connection is closed` from GDM auth code
- Mar 12 09:54:24 - Power key pressed (hard reset)
- Mar 12 09:55:58 - New boot

**Root Cause:** GDM authentication service DBus failure triggered 8 seconds after lid open / display reconfiguration. The GPU compositor kept rendering (mouse cursor moved normally), but the unlock dialog's authentication backend was dead — keyboard and mouse clicks could not be processed. This is NOT an i915 GPU hang. The system ran without suspending for ~24h despite lid being closed for 10h because GNOME's auto-suspend was inhibited by the clamshell+external-monitor detection in gsd-power.

**Fixes Applied:**
1. Added `IdleAction=suspend` and `IdleActionSec=20min` to `/etc/systemd/logind.conf` — bypasses clamshell inhibitor
2. Improved `post_hang_analysis.py` to detect GDM auth failures and distinguish from GPU hangs

### 2026-03-12 (Afternoon): Hang Caused by `systemctl restart systemd-logind`

**Symptom:** Ran `sudo systemctl restart systemd-logind` to apply logind.conf changes. This killed the Wayland session, GDM login screen appeared, then hung in the same GDM auth failure state.

**Root Cause:** On Wayland, restarting logind terminates the entire graphical session. The resulting GDM login screen entered the same DBus failure state as the morning incident.

**Lesson:** NEVER run `sudo systemctl restart systemd-logind` on a running Wayland session. Always reboot to apply logind.conf changes.

### 2026-03-17: Extended Idle GPU Hang (Sleep Inhibitors Blocked Suspend)

**Symptom:** System found hanged. Last log Mar 16 07:32:02, reboot Mar 17 14:50:48 — frozen for 1 day 7 hours. Required hard reset.

**Timeline:**
- Mar 12 11:48:42 - Boot (after logind restart incident reboot)
- Mar 12–15 - Normal use; several cursor update failures (pre-existing i915 issue)
- Mar 15 22:40:03 - Lid closed; system idle on lock screen with external monitor
- Mar 16 07:32:02 - Last log entry (system still alive 8.9 hours after lid close)
- Mar 17 14:50:48 - Reboot after hard reset

**Root Cause:** Extended idle GPU hang — identical pattern to the 2026-03-09 incident. Despite `IdleAction=suspend` being configured, the system never suspended because sleep inhibitors blocked it. `systemd-inhibit --list` revealed 4 sleep inhibitors: **Google Antigravity** (unknown Google app installed on system), **GNOME Shell**, **gsd-media-keys**, and **gsd-power**. Antigravity holds a persistent sleep inhibitor even when idle/backgrounded.

**Why script misidentified:** `post_hang_analysis.py` reported "GDM auth failure" because 3 GDM assertion errors existed in the logs — but those were from boot time (Mar 12 11:48:48), not near the hang. Script fixed with timing check (GDM errors must be within 2 hours of hang to count).

**Fixes Applied:**
1. Added `IdleActionIgnoreInhibitors=yes` to `/etc/systemd/logind.conf` — forces suspend after 20min regardless of inhibitors
2. Fixed `post_hang_analysis.py`: GDM timing check, sleep inhibitor detection, improved "never suspended + GPU errors" root cause pattern

### 2026-03-22: Kernel Panic After Resume from s2idle

**Symptom:** System completely unresponsive — no keyboard, no mouse. Capslock LED blinking (kernel panic indicator). Lid was closed. Required hard reset.

**Timeline:**
- Mar 21 19:43 - Boot (kernel 6.17.0-19, i915.enable_psr=0, i915.enable_dsb=0)
- Mar 21 20:25 - i915 cursor update failure (pre-existing issue, not the root cause)
- Mar 21 22:52 - logind idle suspend fired — system suspended (IdleActionIgnoreInhibitors=yes working)
- Mar 22 10:01 - Resumed after 11h sleep — normal
- Mar 22 11:48 - Suspended again (logind idle)
- Mar 22 12:14 - Resumed from second suspend
- Mar 22 12:22 - Login keyring unlocked
- Mar 22 12:39 - Last log entry
- Mar 22 ~12:40-13:00 - Kernel panic (capslock blinking), hard reset

**Root Cause:** Kernel panic ~25 minutes after resume from s2idle. Exact panicking subsystem unknown (no kdump installed at the time, pstore empty). Prime suspect: i915 GPU driver failing to cleanly reinitialize Display C-states after suspend/resume. Capslock blinking confirms kernel-level panic, not a userspace or GPU driver soft hang.

**Note:** `IdleActionIgnoreInhibitors=yes` worked correctly — two successful suspend cycles occurred. This is a resume stability issue, not an idle hang.

**Fixes Applied:**
1. Added `i915.enable_dc=0` to kernel parameters — disables Display C-states to reduce GPU power gating aggressiveness on resume
2. Installed `linux-crashdump` — enables kdump for future kernel panic capture (`/var/crash/`)

### 2026-04-04: gnome-shell Compositor Freeze During Active Use

**Symptom:** System completely unresponsive — no keyboard, no mouse. No capslock blinking (no kernel panic). System was actively in use. Required hard reset.

**Timeline:**
- Mar 22 13:11 - Boot (kernel 6.17.0-20, all three i915 params active)
- Mar 22–Apr 03 - Normal use, 13 days of uptime
- Apr 03 19:15 - Suspended (logind idle)
- Apr 04 17:55 - Resumed cleanly after 22.6h sleep
- Apr 04 18:33 - Chrome begins reporting Wayland presentation feedback errors every minute
- Apr 04 18:42 - Last log entry
- Apr 04 ~19:30 - Hard reset

**Root Cause:** gnome-shell compositor crash/freeze during active use, approximately 47 minutes after resume. No kernel panic (no capslock blink, no kdump written) — `i915.enable_dc=0` successfully prevented the previous kernel panic type. Chrome's repeated `wayland_frame_manager: The server has buggy presentation feedback` errors indicate the Wayland compositor (gnome-shell) was failing to respond to presentation protocol requests in the minutes before the hang. gnome-shell had already crashed once on Apr 2 during the same boot (crash dump in `/var/crash/`). A second crash on Apr 4 likely failed to auto-restart.

**Note:** This is a different crash type from all previous hangs. The i915 kernel params are working (no kernel-level errors). The problem is in userspace (gnome-shell on Wayland). After 13 days of uptime, gnome-shell accumulated state and became unstable.

**Fixes Applied:**
1. Fixed `post_hang_analysis.py` false positives: EC grep pattern, kdump/GPU hang false match, outdated recommendations

**Potential Workaround:**
- Periodic reboots (e.g., weekly) to reset gnome-shell state — avoids long-uptime accumulation
- No definitive fix yet; need more data

## Temperature Thresholds

| Temperature | Status | Action |
|------------|--------|--------|
| < 85°C | Normal | No action needed |
| 85-90°C | Warning | GUI notification, ensure good ventilation |
| 90-95°C | Critical | Blocking popup, close apps immediately |
| > 95°C | Extreme | System may hang, shut down to prevent damage |

## Key Limitations

- **i915 GPU driver instability**: Atomic update failures confirmed on kernel 6.17.0-19 (2026-03-20). `i915.enable_psr=0`, `i915.enable_dsb=0`, and `i915.enable_dc=0` are all required. Not a kernel-version-fixable issue at this time.
- **i915 resume instability**: Kernel panic ~25min after resume from s2idle (2026-03-22). Mitigated with `i915.enable_dc=0`. `linux-crashdump` installed for future panic capture.
- ~~**No fan control**~~: **RESOLVED** - EC fix restores BIOS fan control
- ~~**No thinkpad_acpi sensors**~~: **RESOLVED** - `/proc/acpi/ibm/thermal` and `/proc/acpi/ibm/fan` now available
- **thermald**: Still may not support Arrow Lake CPU (less critical now that BIOS handles fan automatically)

## Testing

When modifying monitoring scripts:
1. Test notification system: `notify-send "Test" "This is a test"`
2. Verify thermal zone access: `ls /sys/class/thermal/thermal_zone*/temp`
3. Check log file creation: `tail ~/.temp_monitor.log`
4. Ensure PID file cleanup on exit
5. Test with actual CPU load using `cpu_stress_test.py`

## Dependencies

- **Python 3**: Required for `cpu_stress_test.py` and `post_hang_analysis.py`
- **libnotify-bin**: Required for desktop notifications (`notify-send`)
- **zenity** (optional): Used for blocking critical temperature alerts
- **paplay** (optional): Plays alert sounds for critical warnings

Install missing dependencies:
```bash
sudo apt install libnotify-bin zenity pulseaudio-utils
```

## Documentation Files

- **README.md**: User-facing quick start guide with BIOS update status and current system state
- **SETUP_INSTRUCTIONS.md**: Detailed installation and troubleshooting for temperature monitor (legacy - EC now fixed)
- **Analysis_Process.md**: Technical investigation of the Feb 7, 2026 DSB crash (historical reference)
