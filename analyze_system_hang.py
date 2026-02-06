#!/usr/bin/env python3
"""
System Hang Analyzer for Ubuntu 24.04
Analyzes system logs to identify causes of system hangs/freezes
"""

import subprocess
import re
from datetime import datetime, timedelta
import json
import sys

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def run_command(cmd):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return f"Command timed out: {cmd}"
    except Exception as e:
        return f"Error running command: {e}"

def get_last_boot_time():
    """Get the time of last boot"""
    output = run_command("who -b")
    match = re.search(r'system boot\s+(.+)', output)
    if match:
        return match.group(1).strip()
    return "Unknown"

def get_previous_boot_time():
    """Get the time of previous boot before last"""
    output = run_command("journalctl --list-boots | tail -2 | head -1")
    if output:
        parts = output.split()
        if len(parts) >= 3:
            return f"{parts[2]} {parts[3]}"
    return "Unknown"

def check_kernel_panics():
    """Check for kernel panics"""
    print_header("Checking for Kernel Panics")

    # Check journalctl for panics
    output = run_command("journalctl -k -b -1 -p 0..2 --no-pager 2>/dev/null || journalctl -k -p 0..2 --no-pager | tail -100")

    if "kernel panic" in output.lower() or "oops" in output.lower():
        print_error("KERNEL PANIC or OOPS detected!")
        print("\nRelevant kernel messages:")
        for line in output.split('\n'):
            if any(keyword in line.lower() for keyword in ['panic', 'oops', 'bug:', 'rip:']):
                print(f"  {line}")
    else:
        print_success("No kernel panics detected in recent logs")

def check_oom_killer():
    """Check for Out of Memory (OOM) events"""
    print_header("Checking for Out of Memory (OOM) Events")

    output = run_command("journalctl -b -1 --no-pager 2>/dev/null | grep -i 'out of memory\\|oom\\|killed process' || journalctl --no-pager | grep -i 'out of memory\\|oom\\|killed process' | tail -50")

    if output.strip():
        print_error("OOM Killer was triggered!")
        print("\nProcesses killed by OOM:")
        for line in output.split('\n'):
            if 'killed process' in line.lower() or 'out of memory' in line.lower():
                print(f"  {line}")
    else:
        print_success("No OOM events detected")

def check_graphics_issues():
    """Check for GPU/Graphics driver issues"""
    print_header("Checking for Graphics/GPU Issues")

    # Check for GPU errors
    output = run_command("journalctl -b -1 --no-pager 2>/dev/null | grep -iE 'gpu|drm|amdgpu|radeon|nouveau|nvidia|i915' | grep -iE 'error|fail|timeout|hang|freeze' || journalctl --no-pager | grep -iE 'gpu|drm|amdgpu|radeon|nouveau|nvidia|i915' | grep -iE 'error|fail|timeout|hang|freeze' | tail -50")

    if output.strip():
        print_warning("Graphics-related errors detected:")
        for line in output.split('\n')[:20]:  # Show first 20 lines
            if line.strip():
                print(f"  {line}")
    else:
        print_success("No obvious graphics driver errors detected")

def check_hardware_errors():
    """Check for hardware errors (MCE, PCIe, etc.)"""
    print_header("Checking for Hardware Errors")

    # Check for MCE (Machine Check Exception)
    mce_output = run_command("journalctl -b -1 --no-pager 2>/dev/null | grep -i 'mce\\|machine check' || journalctl --no-pager | grep -i 'mce\\|machine check' | tail -20")

    if mce_output.strip():
        print_error("Machine Check Exceptions (MCE) detected - possible hardware failure!")
        for line in mce_output.split('\n')[:10]:
            if line.strip():
                print(f"  {line}")

    # Check for PCIe errors
    pcie_output = run_command("journalctl -b -1 --no-pager 2>/dev/null | grep -iE 'pcie.*error|AER|corrected error|uncorrected error' || journalctl --no-pager | grep -iE 'pcie.*error|AER|corrected error|uncorrected error' | tail -20")

    if pcie_output.strip():
        print_warning("PCIe errors detected:")
        for line in pcie_output.split('\n')[:10]:
            if line.strip():
                print(f"  {line}")

    # Check dmesg for hardware errors
    dmesg_output = run_command("dmesg -T | grep -iE 'error|fail' | grep -iE 'hardware|firmware' | tail -20")
    if dmesg_output.strip():
        print_warning("Hardware/firmware errors in dmesg:")
        for line in dmesg_output.split('\n')[:10]:
            if line.strip():
                print(f"  {line}")

    if not mce_output.strip() and not pcie_output.strip() and not dmesg_output.strip():
        print_success("No obvious hardware errors detected")

def check_thermal_issues():
    """Check for thermal/power issues"""
    print_header("Checking for Thermal/Power Issues")

    # Check for thermal throttling
    thermal_output = run_command("journalctl -b -1 --no-pager 2>/dev/null | grep -iE 'thermal|temperature|throttl|overheat' || journalctl --no-pager | grep -iE 'thermal|temperature|throttl|overheat' | tail -30")

    if thermal_output.strip():
        print_warning("Thermal-related messages found:")
        for line in thermal_output.split('\n')[:15]:
            if line.strip():
                print(f"  {line}")
    else:
        print_success("No thermal issues detected")

    # Check current thermal status
    print("\nCurrent thermal sensors:")
    sensors_output = run_command("sensors 2>/dev/null || echo 'sensors command not available (install lm-sensors)'")
    print(sensors_output)

def check_disk_errors():
    """Check for disk I/O errors"""
    print_header("Checking for Disk Errors")

    disk_output = run_command("journalctl -b -1 --no-pager 2>/dev/null | grep -iE 'I/O error|disk.*error|ata.*error|nvme.*error|blk.*error' || journalctl --no-pager | grep -iE 'I/O error|disk.*error|ata.*error|nvme.*error|blk.*error' | tail -30")

    if disk_output.strip():
        print_error("Disk I/O errors detected:")
        for line in disk_output.split('\n')[:15]:
            if line.strip():
                print(f"  {line}")
    else:
        print_success("No disk errors detected")

def check_suspend_resume():
    """Check for suspend/resume issues"""
    print_header("Checking for Suspend/Resume Issues")

    suspend_output = run_command("journalctl -b -1 --no-pager 2>/dev/null | grep -iE 'suspend|resume|sleep|hibernate' | tail -30 || journalctl --no-pager | grep -iE 'suspend|resume|sleep|hibernate' | tail -30")

    if suspend_output.strip():
        print_info("Suspend/Resume activity detected:")
        for line in suspend_output.split('\n')[:15]:
            if line.strip():
                print(f"  {line}")
    else:
        print_success("No suspend/resume activity detected")

def check_system_load():
    """Check system load and resource usage before crash"""
    print_header("Checking System Load Before Hang")

    # Try to get load average from previous boot
    load_output = run_command("journalctl -b -1 --no-pager 2>/dev/null | grep -i 'load average' | tail -20")
    if load_output.strip():
        print_info("System load information:")
        print(load_output)

    # Check for high CPU usage messages
    cpu_output = run_command("journalctl -b -1 --no-pager 2>/dev/null | grep -iE 'cpu.*stuck|rcu.*stall|soft lockup|hard lockup' || journalctl --no-pager | grep -iE 'cpu.*stuck|rcu.*stall|soft lockup|hard lockup' | tail -20")

    if cpu_output.strip():
        print_error("CPU lockup/stall detected:")
        for line in cpu_output.split('\n'):
            if line.strip():
                print(f"  {line}")

def check_last_messages():
    """Check the last messages before the system hung"""
    print_header("Last System Messages Before Hang")

    print_info("Last 50 messages from previous boot:")
    output = run_command("journalctl -b -1 --no-pager -n 50 2>/dev/null || journalctl --no-pager -n 100")
    print(output)

def get_system_info():
    """Display basic system information"""
    print_header("System Information")

    print(f"Hostname: {run_command('hostname').strip()}")
    print(f"Kernel: {run_command('uname -r').strip()}")
    print(f"OS: {run_command('lsb_release -d 2>/dev/null | cut -f2').strip() or 'Ubuntu 24.04'}")
    print(f"Last boot: {get_last_boot_time()}")
    print(f"Previous boot: {get_previous_boot_time()}")
    print(f"Uptime: {run_command('uptime -p').strip()}")

    # Get CPU info
    cpu_model = run_command("lscpu | grep 'Model name' | cut -d: -f2").strip()
    print(f"CPU: {cpu_model}")

    # Get GPU info
    gpu_info = run_command("lspci | grep -i vga").strip()
    print(f"GPU: {gpu_info}")

    # Get memory info
    mem_info = run_command("free -h | grep Mem").strip()
    print(f"Memory: {mem_info}")

def main():
    print(f"{Colors.BOLD}{Colors.MAGENTA}")
    print(r"""
    ╔═══════════════════════════════════════════════════════════╗
    ║          System Hang/Freeze Diagnostic Tool              ║
    ║                  Ubuntu 24.04                             ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    print(f"{Colors.END}")

    # Check if running with sufficient privileges
    if run_command("id -u").strip() != "0":
        print_warning("Not running as root. Some information may be limited.")
        print_info("For complete analysis, consider running with: sudo python3 analyze_system_hang.py\n")

    get_system_info()
    check_kernel_panics()
    check_oom_killer()
    check_hardware_errors()
    check_graphics_issues()
    check_thermal_issues()
    check_disk_errors()
    check_system_load()
    check_suspend_resume()
    check_last_messages()

    print_header("Analysis Complete")
    print_info("Review the findings above to identify the cause of the system hang.")
    print_info("Common causes:")
    print("  • OOM Killer: System ran out of memory")
    print("  • Graphics driver hang: GPU driver crashed or froze")
    print("  • CPU lockup: Hardware or driver caused CPU to hang")
    print("  • Thermal throttling: Overheating caused system to freeze")
    print("  • Hardware errors: Faulty RAM, disk, or other components")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Analysis interrupted by user.{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Error during analysis: {e}{Colors.END}")
        sys.exit(1)
