#!/usr/bin/env python3
"""
Post-Hang Analysis Script for ThinkPad E14 Gen 7 (21SX005CIV)
==============================================================
Run this script IMMEDIATELY after a hard reset to capture and analyze
logs from the previous boot that caused the hang.

Focuses on the known failure modes:
  1. i915 GPU driver hangs (Arrow Lake-P / Core Ultra 7 255H)
  2. ACPI/EC thermal management failure
  3. Extended idle lock screen GPU freezes

Usage:
    sudo python3 post_hang_analysis.py              # Full analysis with root
    python3 post_hang_analysis.py                   # Limited analysis without root
    sudo python3 post_hang_analysis.py --save       # Save report to file
    sudo python3 post_hang_analysis.py --json       # Output JSON for programmatic use
"""

import subprocess
import re
import sys
import os
import json
from datetime import datetime


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'


class PostHangAnalyzer:
    def __init__(self, json_output=False):
        self.json_output = json_output
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "system_info": {},
            "boot_info": {},
            "findings": [],
            "gpu_events": [],
            "gpu_events_near_hang": True,
            "thermal_events": [],
            "lid_events": [],
            "gdm_auth_failures": 0,
            "gdm_events_near_hang": False,
            "gdm_triggered_by_lid_open": False,
            "last_activity": None,
            "hang_window": {},
            "root_cause": None,
            "severity": None,
        }

    def run_cmd(self, cmd, timeout=30):
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return ""
        except Exception:
            return ""

    def print_header(self, text):
        if not self.json_output:
            print(f"\n{Colors.BOLD}{Colors.CYAN}{'─'*70}{Colors.END}")
            print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.END}")
            print(f"{Colors.BOLD}{Colors.CYAN}{'─'*70}{Colors.END}")

    def print_finding(self, severity, text):
        if not self.json_output:
            icons = {"error": f"{Colors.RED}[CRITICAL]", "warning": f"{Colors.YELLOW}[WARNING]",
                      "info": f"{Colors.BLUE}[INFO]", "ok": f"{Colors.GREEN}[OK]"}
            icon = icons.get(severity, icons["info"])
            print(f"  {icon} {text}{Colors.END}")
        self.report["findings"].append({"severity": severity, "message": text})

    def print_detail(self, text):
        if not self.json_output:
            print(f"    {Colors.DIM}{text}{Colors.END}")

    # ── System Information ──────────────────────────────────────────────

    def collect_system_info(self):
        self.print_header("System Information")

        info = {
            "hostname": self.run_cmd("hostname"),
            "kernel": self.run_cmd("uname -r"),
            "cmdline": self.run_cmd("cat /proc/cmdline"),
            "cpu": self.run_cmd("lscpu | grep 'Model name' | cut -d: -f2").strip(),
            "gpu": self.run_cmd("lspci | grep -i vga"),
            "memory": self.run_cmd("free -h | grep Mem | awk '{print $2}'"),
            "sleep_mode": self.run_cmd("cat /sys/power/mem_sleep 2>/dev/null"),
            "is_root": os.geteuid() == 0 if hasattr(os, 'geteuid') else False,
        }
        self.report["system_info"] = info

        if not self.json_output:
            print(f"  Hostname:   {info['hostname']}")
            print(f"  Kernel:     {info['kernel']}")
            print(f"  CPU:        {info['cpu']}")
            print(f"  GPU:        {info['gpu']}")
            print(f"  Memory:     {info['memory']}")
            print(f"  Sleep mode: {info['sleep_mode']}")

        if not info["is_root"]:
            self.print_finding("warning",
                "Not running as root - some data (dmesg) will be unavailable. "
                "Use: sudo python3 post_hang_analysis.py")

        # Verify kernel parameters
        cmdline = info["cmdline"]
        params_check = {
            "i915.enable_psr=0": "Panel Self Refresh disabled",
            "i915.enable_dsb=0": "Display State Buffer disabled",
            "i915.enable_dc=0": "Display C-states disabled",
        }
        for param, desc in params_check.items():
            if param in cmdline:
                self.print_finding("ok", f"Kernel param: {param} ({desc})")
            else:
                self.print_finding("warning", f"Missing kernel param: {param} ({desc})")

    # ── Boot History ────────────────────────────────────────────────────

    def analyze_boot_history(self):
        self.print_header("Boot History Analysis")

        boots_raw = self.run_cmd("journalctl --list-boots 2>/dev/null")
        if not self.json_output:
            print(f"  Recent boots:")
            for line in (boots_raw or "").split('\n')[-5:]:
                if line.strip():
                    print(f"    {line.strip()}")

        # Parse previous boot timestamps
        prev_boot_first = self.run_cmd(
            "journalctl -b -1 --no-pager -o short-iso 2>/dev/null | head -1 | awk '{print $1}'"
        )
        prev_boot_last = self.run_cmd(
            "journalctl -b -1 --no-pager -o short-iso 2>/dev/null | tail -1 | awk '{print $1}'"
        )
        current_boot_first = self.run_cmd(
            "journalctl -b 0 --no-pager -o short-iso 2>/dev/null | head -1 | awk '{print $1}'"
        )

        self.report["boot_info"] = {
            "previous_boot_start": prev_boot_first,
            "previous_boot_last_log": prev_boot_last,
            "current_boot_start": current_boot_first,
        }

        if prev_boot_last and current_boot_first:
            try:
                fmt = "%Y-%m-%dT%H:%M:%S%z"
                # Handle various timestamp formats
                last_ts = prev_boot_last.split('.')[0]
                curr_ts = current_boot_first.split('.')[0]
                # Try parsing with timezone
                for f in [fmt, "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        t_last = datetime.fromisoformat(last_ts)
                        t_curr = datetime.fromisoformat(curr_ts)
                        gap = t_curr - t_last
                        self.report["hang_window"] = {
                            "last_log": prev_boot_last,
                            "reboot": current_boot_first,
                            "gap_seconds": gap.total_seconds(),
                            "gap_human": str(gap),
                        }
                        self.print_finding("info",
                            f"Last log before hang: {prev_boot_last}")
                        self.print_finding("info",
                            f"Reboot after hang:    {current_boot_first}")
                        self.print_finding("warning",
                            f"Unresponsive gap: {gap} (system was frozen)")
                        break
                    except ValueError:
                        continue
            except Exception:
                pass

        # Calculate previous boot uptime
        if prev_boot_first and prev_boot_last:
            try:
                t_start = datetime.fromisoformat(prev_boot_first.split('.')[0])
                t_end = datetime.fromisoformat(prev_boot_last.split('.')[0])
                uptime = t_end - t_start
                self.report["boot_info"]["uptime_before_hang"] = str(uptime)
                self.print_finding("info", f"System was up for {uptime} before hanging")
            except Exception:
                pass

    # ── i915 / GPU Analysis ─────────────────────────────────────────────

    def analyze_gpu_events(self):
        self.print_header("i915 GPU / Graphics Analysis")

        # Get hang timestamp to classify "near hang" vs "hours before"
        hang_ts = self.report.get("hang_window", {}).get("last_log", "")

        # Cursor update failures
        cursor_errors = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | grep -i 'cursor update failed'"
        )
        if cursor_errors:
            lines = [l for l in cursor_errors.split('\n') if l.strip()]
            self.print_finding("warning",
                f"Cursor update failures: {len(lines)} occurrence(s)")
            for line in lines:
                self.print_detail(line.strip())
                self.report["gpu_events"].append({
                    "type": "cursor_update_failure", "message": line.strip()
                })
            # Check if any failures occurred within 60 minutes of the hang
            if hang_ts:
                try:
                    t_hang = datetime.fromisoformat(hang_ts.split('.')[0])
                    near_hang = False
                    for line in lines:
                        m = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
                        if m:
                            t_err = datetime.fromisoformat(m.group(1))
                            if hasattr(t_hang, 'tzinfo') and t_hang.tzinfo:
                                import pytz
                                t_err = t_err.replace(tzinfo=t_hang.tzinfo)
                            if abs((t_hang - t_err).total_seconds()) < 3600:
                                near_hang = True
                                break
                    self.report["gpu_events_near_hang"] = near_hang
                    if not near_hang:
                        self.print_detail("  ↳ All cursor failures occurred >1hr before hang (may not be direct cause)")
                except Exception:
                    self.report["gpu_events_near_hang"] = True  # assume worst case

        # Atomic update failures
        atomic_errors = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | grep -i 'atomic update failure'"
        )
        if atomic_errors:
            lines = [l for l in atomic_errors.split('\n') if l.strip()]
            self.print_finding("error",
                f"i915 atomic update failures: {len(lines)} occurrence(s)")
            for line in lines:
                self.print_detail(line.strip())
                self.report["gpu_events"].append({
                    "type": "atomic_update_failure", "message": line.strip()
                })

        # DSB errors
        dsb_errors = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | grep -i 'DSB.*error'"
        )
        if dsb_errors:
            lines = [l for l in dsb_errors.split('\n') if l.strip()]
            self.print_finding("error",
                f"DSB poll errors: {len(lines)} occurrence(s) - check i915.enable_dsb=0")
            for line in lines:
                self.print_detail(line.strip())
                self.report["gpu_events"].append({
                    "type": "dsb_error", "message": line.strip()
                })

        # GPU hangs / resets (exclude boot-time gpu-manager, vgaarb, and kdump
        # kexec setup — kdump command line contains "i915...reset_devices" which
        # would otherwise match the i915.*reset pattern)
        gpu_hangs = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | "
            "grep -iE 'GPU HANG|GPU hang detected|gpu reset|drm.*hang|i915.*hang|i915.*reset|GuC.*error' | "
            "grep -v 'gpu-manager.service' | grep -v 'vgaarb' | grep -v 'kdump'"
        )
        if gpu_hangs:
            lines = [l for l in gpu_hangs.split('\n') if l.strip()]
            if lines:
                self.print_finding("error", f"GPU hang/reset events: {len(lines)}")
                for line in lines:
                    self.print_detail(line.strip())
                    self.report["gpu_events"].append({
                        "type": "gpu_hang_reset", "message": line.strip()
                    })

        # General DRM errors
        drm_errors = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | "
            "grep -E '\\[drm\\].*ERROR|\\[drm\\].*error'"
        )
        if drm_errors:
            lines = [l for l in drm_errors.split('\n') if l.strip()]
            self.print_finding("warning", f"DRM errors: {len(lines)} occurrence(s)")
            for line in lines[:10]:
                self.print_detail(line.strip())

        # dmesg GPU errors (requires root)
        if self.report["system_info"].get("is_root"):
            dmesg_gpu = self.run_cmd(
                "dmesg | grep -iE 'i915.*error|drm.*error|gpu.*hang'"
            )
            if dmesg_gpu:
                self.print_finding("warning", "Current boot also has GPU errors (ongoing issue)")

        if not cursor_errors and not atomic_errors and not dsb_errors and not gpu_hangs:
            self.print_finding("ok", "No GPU errors found in previous boot logs")

    # ── ACPI / Thermal Analysis ─────────────────────────────────────────

    def analyze_thermal(self):
        self.print_header("ACPI / Thermal Analysis")

        # ACPI EC errors — match kernel-level EC failures only.
        # Patterns are anchored to kernel source to avoid false positives from
        # gnome-shell GJS messages (which contain "object" → "ec" + "access").
        ec_errors = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | "
            "grep -iE 'kernel:.*thinkpad_acpi.*misbehav|kernel:.*ACPI.*EC.*(fail|error)|"
            "thinkpad_acpi:.*EC.*access'"
        )
        if ec_errors:
            lines = [l for l in ec_errors.split('\n') if l.strip()]
            self.print_finding("error",
                f"ACPI/EC communication failure: {len(lines)} errors")
            for line in lines[:5]:
                self.report["thermal_events"].append({
                    "type": "acpi_ec_failure", "message": line.strip()
                })

        # thermald status
        thermald = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | grep -i thermald"
        )
        if thermald:
            if "Deactivated" in thermald or "exit" in thermald.lower():
                self.print_finding("warning", "thermald started but exited (unsupported CPU)")

        # Check current temperatures
        self.print_header("Current Thermal Status")
        temp_zones = self.run_cmd("cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null")
        if temp_zones:
            temps = []
            for t in temp_zones.split('\n'):
                if t.strip():
                    try:
                        temp_c = int(t.strip()) / 1000
                        temps.append(temp_c)
                    except ValueError:
                        pass
            if temps:
                max_temp = max(temps)
                avg_temp = sum(temps) / len(temps)
                self.print_finding("info",
                    f"Current temps: max={max_temp:.0f}C, avg={avg_temp:.0f}C "
                    f"(zones: {', '.join(f'{t:.0f}C' for t in temps)})")
                if max_temp > 85:
                    self.print_finding("warning", f"Current temperature is HIGH: {max_temp:.0f}C")

    # ── Lid / Suspend / Idle Analysis ───────────────────────────────────

    def analyze_idle_state(self):
        self.print_header("Lid / Suspend / Idle State Analysis")

        # Lid events
        lid_events = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | grep -i 'lid'"
        )
        if lid_events:
            lines = [l for l in lid_events.split('\n') if l.strip()]
            last_lid_event = None
            for line in lines:
                ts_match = re.match(r'^(\w+ \d+ \d+:\d+:\d+)', line)
                ts_str = ts_match.group(1) if ts_match else "unknown"
                if "closed" in line.lower():
                    self.print_detail(f"{ts_str} - Lid CLOSED")
                    last_lid_event = {"time": ts_str, "state": "closed"}
                elif "opened" in line.lower():
                    self.print_detail(f"{ts_str} - Lid OPENED")
                    last_lid_event = {"time": ts_str, "state": "opened"}
                self.report["lid_events"].append(line.strip())

            if last_lid_event:
                self.print_finding("info",
                    f"Last lid event: {last_lid_event['state']} at {last_lid_event['time']}")
                if last_lid_event["state"] == "closed":
                    self.print_finding("warning",
                        "Lid was CLOSED when system hung - lock screen was active on external display")

        # Suspend/resume events
        suspend_events = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | "
            "grep -iE 'PM: suspend|PM: resume|Suspending system|suspend entry|suspend exit'"
        )
        if suspend_events and suspend_events.strip():
            self.print_finding("info", "Suspend/resume events detected:")
            for line in suspend_events.split('\n')[:10]:
                self.print_detail(line.strip())
        else:
            self.print_finding("warning",
                "System NEVER suspended (s2idle not triggered) - ran continuously")

        # Check for sleep inhibitors blocking IdleAction
        inhibitors = self.run_cmd(
            "systemd-inhibit --list --no-legend 2>/dev/null | grep -i sleep"
        )
        if inhibitors:
            lines = [l for l in inhibitors.split('\n') if l.strip()]
            self.print_finding("warning",
                f"Sleep inhibitors active: {len(lines)} — these block IdleAction=suspend")
            for line in lines[:5]:
                self.print_detail(line.strip())
            self.print_detail(
                "Fix: add IdleActionIgnoreInhibitors=yes to /etc/systemd/logind.conf")

        # Check if system was idle (no user login activity)
        user_activity = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | "
            "grep -iE 'pam_unix.*session opened.*uid=1000|gdm.*session|unlock'"
        )
        if user_activity:
            lines = [l for l in user_activity.split('\n') if l.strip()]
            last_activity = lines[-1] if lines else None
            if last_activity:
                self.report["last_activity"] = last_activity.strip()
                self.print_finding("info", f"Last user activity: {last_activity.strip()[:80]}")

    # ── GDM / Auth Service Analysis ──────────────────────────────────────

    def analyze_gdm_auth(self):
        self.print_header("GDM / Authentication Service Analysis")

        # GDM auth failures — several patterns:
        #  1. gnome-shell loses DBus connection to GDM (Gio.IOErrorEnum)
        #  2. gdm3 assertion failures on display add/remove (GDM_IS_REMOTE_DISPLAY)
        #  3. gdm-session-worker exits unexpectedly
        gdm_errors = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | "
            "grep -E '"
            "Gio.IOErrorEnum.*connection.*closed|"
            "GDM_IS_REMOTE_DISPLAY.*failed|"
            "gdm3.*assertion.*failed|"
            "gdm-session-worker.*error|"
            "authPrompt|unlockDialog.*error"
            "'"
        )
        gdm_lines = [l for l in (gdm_errors or "").split('\n') if l.strip()]

        if gdm_lines:
            self.print_finding("error",
                f"GDM auth service failures: {len(gdm_lines)} occurrence(s)")
            self.print_detail("Lock screen may be rendered but keyboard/mouse input is rejected")
            self.print_detail("(Mouse cursor still moves because compositor is running)")
            for line in gdm_lines[:5]:
                self.print_detail(line.strip())
            self.report["gdm_auth_failures"] = len(gdm_lines)
            self.report["gdm_auth_lines"] = [l.strip() for l in gdm_lines[:10]]
        else:
            self.print_finding("ok", "No GDM auth service failures detected")
            self.report["gdm_auth_failures"] = 0

        # Check if GDM errors occurred near the hang (not just at boot time)
        # Boot-time GDM assertion errors are common and harmless; only flag if near hang
        hang_ts = self.report.get("hang_window", {}).get("last_log", "")
        gdm_events_near_hang = bool(gdm_lines)  # default: assume relevant if errors exist
        if gdm_lines and hang_ts:
            try:
                t_hang = datetime.fromisoformat(hang_ts.split('.')[0])
                near = False
                for line in gdm_lines:
                    m = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
                    if m:
                        t_err = datetime.fromisoformat(m.group(1))
                        if hasattr(t_hang, 'tzinfo') and t_hang.tzinfo:
                            t_err = t_err.replace(tzinfo=t_hang.tzinfo)
                        if abs((t_hang - t_err).total_seconds()) < 7200:  # 2 hours
                            near = True
                            break
                gdm_events_near_hang = near
                if not near:
                    self.print_detail(
                        "  ↳ All GDM errors >2hr before hang (likely boot-time, not the hang cause)")
            except Exception:
                pass
        elif not gdm_lines:
            gdm_events_near_hang = False
        self.report["gdm_events_near_hang"] = gdm_events_near_hang

        # Check if GDM failures started immediately after a lid-open event
        if gdm_lines and self.report.get("lid_events"):
            lid_open_raw = self.run_cmd(
                "journalctl -b -1 --no-pager -o short-iso 2>/dev/null | grep -i 'lid.*open'"
            )
            gdm_first_raw = self.run_cmd(
                "journalctl -b -1 --no-pager -o short-iso 2>/dev/null | "
                "grep -E 'Gio.IOErrorEnum.*connection.*closed|GDM_IS_REMOTE_DISPLAY.*failed|gdm3.*assertion.*failed' | head -1"
            )
            if lid_open_raw and gdm_first_raw:
                try:
                    lid_lines = [l for l in lid_open_raw.split('\n') if l.strip()]
                    last_lid_open_ts = None
                    for ll in lid_lines:
                        m = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', ll)
                        if m:
                            last_lid_open_ts = datetime.fromisoformat(m.group(1))
                    m2 = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', gdm_first_raw.strip())
                    if last_lid_open_ts and m2:
                        gdm_first_ts = datetime.fromisoformat(m2.group(1))
                        diff = abs((gdm_first_ts - last_lid_open_ts).total_seconds())
                        if diff < 60:
                            self.print_finding("warning",
                                f"GDM auth failure began {diff:.0f}s after lid open — "
                                "lid open triggered display reconfiguration that broke GDM DBus connection")
                            self.report["gdm_triggered_by_lid_open"] = True
                except Exception:
                    pass

    # ── Kernel / CPU Analysis ───────────────────────────────────────────

    def analyze_kernel_cpu(self):
        self.print_header("Kernel / CPU Lockup Analysis")

        # RCU stalls
        rcu_stalls = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | grep -i 'rcu.*stall'"
        )
        if rcu_stalls and rcu_stalls.strip():
            self.print_finding("error", "RCU stalls detected - indicates CPU lockup")
            for line in rcu_stalls.split('\n')[:5]:
                self.print_detail(line.strip())

        # Soft/hard lockups (exclude boot-time "NMI watchdog: Enabled" message)
        lockups = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | "
            "grep -iE 'soft lockup|hard lockup|watchdog.*detected.*lockup' | "
            "grep -v 'NMI watchdog: Enabled'"
        )
        if lockups and lockups.strip():
            self.print_finding("error", "CPU lockup detected by watchdog")
            for line in lockups.split('\n')[:5]:
                self.print_detail(line.strip())

        # Kernel panics (priority 0=emerg, 1=alert only; skip 2=crit to avoid gnome-shell false positives)
        panics = self.run_cmd(
            "journalctl -b -1 -k --no-pager -p 0..1 2>/dev/null"
        )
        if panics and panics.strip() and "No entries" not in panics:
            lines = [l for l in panics.split('\n') if l.strip()]
            if lines:
                self.print_finding("error", f"Critical kernel messages: {len(lines)}")
                for line in lines[:10]:
                    self.print_detail(line.strip())
        else:
            self.print_finding("ok", "No kernel panics or critical messages logged")
            self.print_detail("(Note: hard GPU lockups freeze the kernel before it can log)")

        # OOM (match actual kill events, not the oomd service starting)
        oom = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | "
            "grep -iE 'out of memory|oom-kill|killed process.*anon-rss' | "
            "grep -v 'systemd-oomd.service\\|oomd.socket\\|systemd-oomd'"
        )
        if oom and oom.strip():
            self.print_finding("error", "OOM killer was triggered")
            for line in oom.split('\n')[:5]:
                self.print_detail(line.strip())
        else:
            self.print_finding("ok", "No OOM events")

    # ── Network Instability (context) ───────────────────────────────────

    def analyze_network_churn(self):
        self.print_header("Network Interface Churn (USB Dock)")

        # Count network route changes
        route_changes = self.run_cmd(
            "journalctl -b -1 --no-pager 2>/dev/null | "
            "grep -c 'policy: set.*as default for IPv4'"
        )
        try:
            n_routes = int(route_changes) if route_changes else 0
        except ValueError:
            n_routes = 0

        if n_routes > 20:
            self.print_finding("warning",
                f"Excessive network route changes: {n_routes} (USB ethernet flapping)")
            self.print_detail("Each route change triggers NetworkManager dispatcher + vmnetBridge updates")
            self.print_detail("This generates periodic GPU compositor updates on the lock screen")
        elif n_routes > 0:
            self.print_finding("info", f"Network route changes: {n_routes}")

    # ── Last Messages Before Hang ───────────────────────────────────────

    def show_last_messages(self):
        self.print_header("Last 20 Log Entries Before Hang")

        output = self.run_cmd(
            "journalctl -b -1 --no-pager -n 20 2>/dev/null"
        )
        if output:
            for line in output.split('\n'):
                if line.strip():
                    self.print_detail(line.strip())

    # ── Root Cause Determination ────────────────────────────────────────

    def determine_root_cause(self):
        self.print_header("Root Cause Determination")

        gpu_errors = len(self.report["gpu_events"])
        gpu_errors_near_hang = self.report.get("gpu_events_near_hang", True)
        gdm_failures = self.report.get("gdm_auth_failures", 0)
        gdm_triggered_by_lid = self.report.get("gdm_triggered_by_lid_open", False)
        has_acpi_failure = any(
            e["type"] == "acpi_ec_failure" for e in self.report["thermal_events"]
        )
        has_no_panic = not any(
            f["severity"] == "error" and "panic" in f["message"].lower()
            for f in self.report["findings"]
        )
        has_no_lockup_log = not any(
            f["severity"] == "error" and ("lockup" in f["message"].lower() or "stall" in f["message"].lower())
            for f in self.report["findings"]
        )

        # Determine root cause — order matters: check specific causes first
        if any(f["severity"] == "error" and "oom" in f["message"].lower() for f in self.report["findings"]):
            cause = "System ran out of memory (OOM). Processes were killed, possibly leading to system instability."
            severity = "HIGH"
            recommendations = [
                "Check for memory leaks in running applications",
                "Increase swap space",
                "Monitor memory usage with 'free -h' and 'top'",
            ]
        elif any(f["severity"] == "error" and "lockup" in f["message"].lower() for f in self.report["findings"]):
            cause = "CPU lockup detected. A driver or kernel bug caused a CPU to become unresponsive."
            severity = "CRITICAL"
            recommendations = [
                "Check dmesg for the specific driver causing the lockup",
                "Update kernel to latest available version",
                "Report to kernel bugzilla with lockup details",
            ]
        elif gdm_failures > 0 and self.report.get("gdm_events_near_hang", True) and (gpu_errors == 0 or not gpu_errors_near_hang):
            # GDM auth failure: lock screen unresponsive but mouse still works
            # GPU errors exist but are hours old — not the direct cause
            if gdm_triggered_by_lid:
                cause = (
                    "GDM AUTHENTICATION SERVICE FAILURE triggered by lid open / display reconfiguration. "
                    "When the lid was opened, a display hotplug event caused gnome-shell to lose its "
                    "DBus connection to the GDM auth service. The lock screen continued rendering "
                    "(mouse cursor still moved) but could not accept keyboard or click input because "
                    "the authentication backend was dead. This is NOT an i915 GPU hard hang — the GPU "
                    "was functioning normally."
                )
            else:
                cause = (
                    "GDM AUTHENTICATION SERVICE FAILURE. gnome-shell lost its DBus connection to the "
                    "GDM auth service, leaving the lock screen in an unresponsive state. "
                    "The GPU compositor kept running (mouse cursor moved) but keyboard/click input "
                    "was rejected because the authentication backend was dead. "
                    "This is NOT an i915 GPU hard hang."
                )
            severity = "HIGH"
            recommendations = [
                "Root cause: GDM/gnome-shell DBus auth connection failure, NOT a GPU hang",
                "Workaround: Configure auto-suspend via logind (not just GNOME settings) so the "
                "system suspends before GDM can fail — see logind.conf IdleAction",
                "Workaround: Avoid leaving system on lock screen for extended periods (>several hours)",
                "Investigate: USB dock reconnection or lid-open display reconfiguration triggers GDM restart",
                "Long-term: Monitor https://gitlab.gnome.org/GNOME/gnome-shell/-/issues for GDM DBus fixes",
                "Note: i915 cursor failures earlier in the session are a separate, pre-existing issue",
            ]
        elif gpu_errors > 0 and gpu_errors_near_hang and has_no_panic and has_no_lockup_log:
            cause = (
                "i915 GPU HARD HANG during extended idle operation. "
                "The cursor/atomic update failures were precursors. "
                "The GPU eventually entered an unrecoverable state, "
                "freezing the entire system including input and journald. "
                "No kernel panic was logged because the freeze is at the hardware/driver level."
            )
            severity = "HIGH"
            recommendations = [
                "This is a known i915 driver bug with Arrow Lake-P (Meteor Lake) GPUs",
                "Kernel params i915.enable_psr=0 and i915.enable_dsb=0 reduce but don't eliminate the issue",
                "WORKAROUND: Configure system to suspend when idle instead of showing lock screen indefinitely",
                "WORKAROUND: Set logind IdleAction=suspend and IdleActionSec=20min (bypasses clamshell inhibitor)",
                "LONG-TERM: Update to newer kernel with i915 fixes when available",
                "MONITOR: Run the temperature monitor to catch thermal events that compound GPU instability",
            ]
        else:
            never_suspended = any(
                "NEVER suspended" in f.get("message", "") for f in self.report["findings"]
            )
            if never_suspended and gpu_errors > 0:
                cause = (
                    "EXTENDED IDLE GPU HANG (probable). The system ran continuously without "
                    "suspending — sleep inhibitors blocked IdleAction=suspend — while having "
                    "i915 GPU instability earlier in the session. After extended lock screen "
                    "operation the GPU likely entered an unrecoverable state. Journald froze "
                    "with the GPU, so no errors were logged near the hang."
                )
                severity = "HIGH"
                recommendations = [
                    "IMMEDIATE FIX: Add IdleActionIgnoreInhibitors=yes to /etc/systemd/logind.conf",
                    "Run 'systemd-inhibit --list' to see what is blocking sleep",
                    "Known blockers on this system: Google Antigravity, GNOME Shell, gsd-power",
                    "Reboot after logind.conf change (never restart systemd-logind on Wayland)",
                    "This is the same root cause as the 2026-03-09 and 2026-03-17 hangs",
                    "LONG-TERM: Update to newer kernel with i915 fixes when available",
                ]
            else:
                cause = (
                    "Unable to determine exact root cause. "
                    "The system froze without logging a clear error. "
                    "Possible causes: gnome-shell compositor crash (Wayland — if compositor dies, "
                    "input becomes unresponsive even if kernel is fine), silent kernel lockup "
                    "at hardware/driver level, or i915 driver freeze without panic."
                )
                severity = "MEDIUM"
                recommendations = [
                    "Check /var/crash/ for crash dumps: ls /var/crash/",
                    "If gnome-shell crashed, consider reducing session uptime (reboot after ~7 days)",
                    "Check for BIOS/firmware updates for this ThinkPad model",
                    "If capslock LED was blinking: kernel panic — check /var/crash/ for kdump",
                    "If capslock LED was NOT blinking: likely gnome-shell or userspace freeze",
                ]

        if has_acpi_failure:
            cause += " ACPI/EC kernel-level errors detected — EC may be malfunctioning."
            recommendations.append(
                "ACPI/EC errors found — check if BIOS update resolves them"
            )

        self.report["root_cause"] = cause
        self.report["severity"] = severity

        if not self.json_output:
            print(f"\n  {Colors.BOLD}Severity: ", end="")
            if severity == "CRITICAL":
                print(f"{Colors.RED}{severity}{Colors.END}")
            elif severity == "HIGH":
                print(f"{Colors.YELLOW}{severity}{Colors.END}")
            else:
                print(f"{Colors.BLUE}{severity}{Colors.END}")

            print(f"\n  {Colors.BOLD}Root Cause:{Colors.END}")
            # Word wrap the cause
            words = cause.split()
            line = "    "
            for word in words:
                if len(line) + len(word) > 75:
                    print(line)
                    line = "    " + word
                else:
                    line += " " + word if line.strip() else "    " + word
            if line.strip():
                print(line)

            print(f"\n  {Colors.BOLD}Recommendations:{Colors.END}")
            for i, rec in enumerate(recommendations, 1):
                print(f"    {i}. {rec}")

        self.report["recommendations"] = recommendations

    # ── Report Generation ───────────────────────────────────────────────

    def save_report(self, filepath=None):
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "reports",
                f"hang_report_{timestamp}.json"
            )

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w') as f:
            json.dump(self.report, f, indent=2, default=str)

        if not self.json_output:
            print(f"\n  {Colors.GREEN}Report saved to: {filepath}{Colors.END}")

        return filepath

    # ── Main ────────────────────────────────────────────────────────────

    def run(self, save=False):
        if not self.json_output:
            print(f"{Colors.BOLD}{Colors.MAGENTA}")
            print("  ┌─────────────────────────────────────────────────────────────┐")
            print("  │        Post-Hang Analysis - ThinkPad E14 Gen 7             │")
            print("  │        Arrow Lake-P / Core Ultra 7 255H                    │")
            print("  └─────────────────────────────────────────────────────────────┘")
            print(f"{Colors.END}")

        # Check if previous boot data exists
        check = self.run_cmd("journalctl -b -1 --no-pager -n 1 2>/dev/null")
        if not check or not check.strip():
            if not self.json_output:
                print(f"  {Colors.RED}No previous boot logs found.{Colors.END}")
                print(f"  This can happen if:")
                print(f"    - journalctl persistent storage is not enabled")
                print(f"    - The system was rebooted multiple times since the hang")
                print(f"  To enable persistent logs: sudo mkdir -p /var/log/journal")
            return

        self.collect_system_info()
        self.analyze_boot_history()
        self.analyze_gpu_events()
        self.analyze_thermal()
        self.analyze_idle_state()
        self.analyze_gdm_auth()
        self.analyze_kernel_cpu()
        self.analyze_network_churn()
        self.show_last_messages()
        self.determine_root_cause()

        if save or self.json_output:
            self.save_report()

        if self.json_output:
            print(json.dumps(self.report, indent=2, default=str))

        if not self.json_output:
            print(f"\n{Colors.BOLD}{Colors.CYAN}{'─'*70}{Colors.END}")
            print(f"  {Colors.DIM}Run with --save to save report, --json for machine-readable output{Colors.END}")
            print(f"{Colors.BOLD}{Colors.CYAN}{'─'*70}{Colors.END}\n")


def main():
    save = "--save" in sys.argv
    json_output = "--json" in sys.argv

    analyzer = PostHangAnalyzer(json_output=json_output)
    analyzer.run(save=save)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Analysis interrupted.{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}")
        sys.exit(1)
