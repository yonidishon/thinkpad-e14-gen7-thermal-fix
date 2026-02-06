# System Hang Analysis Report
**Date of Incident:** February 5, 2026, ~20:11 PM
**System:** ThinkPad E14 H255
**OS:** Ubuntu 24.04.3 LTS
**Kernel:** 6.14.0-37-generic
**CPU:** Intel Core Ultra 7 255H (Arrow Lake-P)
**GPU:** Intel Arrow Lake-P Integrated Graphics

---

## Summary
The system froze after running for approximately 10 hours (since 10:08 AM). The freeze occurred around 8:11 PM with no kernel panic, OOM killer activation, or error messages. The system simply stopped responding and required a hard reset.

---

## Key Findings

### 1. **Graphics Driver Issues (Most Likely Cause)**
**Severity: HIGH**

Multiple instances of GNOME Shell cursor update failures throughout the day:
```
Feb 04 17:11:51 - Cursor update failed: drmModeAtomicCommit: Invalid argument
Feb 05 06:29:32 - Cursor update failed: drmModeAtomicCommit: Invalid argument
Feb 05 10:58:57 - Cursor update failed: drmModeAtomicCommit: Invalid argument
Feb 05 12:13:57 - Cursor update failed: drmModeAtomicCommit: Invalid argument
Feb 05 15:00:34 - Cursor update failed: drmModeAtomicCommit: Invalid argument
Feb 05 16:03:56 - Cursor update failed: drmModeAtomicCommit: Invalid argument
```

**Analysis:**
- The i915 graphics driver (Intel) is failing atomic modesetting commits
- This is a known issue with newer Intel Arrow Lake processors and the i915 driver
- These failures accumulate and can eventually cause a complete graphics hang
- The hang occurred without any kernel error messages, typical of GPU driver deadlocks

### 2. **No Kernel Panic or OOM**
- No kernel panic detected
- No Out-of-Memory killer activation (contrary to initial detection)
- No CPU lockups or hard/soft lockups reported
- System had 30GB RAM with 20GB free at current boot

### 3. **ACPI/EC Errors**
**Severity: MEDIUM**

Multiple ACPI Embedded Controller (EC) errors at boot:
```
ACPI Error: Unknown class in reference - 0x00
ACPI Error: Aborting method _SB.PC00.LPCB.EC.ECRD due to previous error (AE_TYPE)
```

**Analysis:**
- ThinkPad ACPI interface cannot access thermal sensors properly
- May contribute to power management issues
- Could prevent proper thermal throttling monitoring

### 4. **Thermal Daemon Issues**
```
thermald: Unsupported cpu model or platform
thinkpad_acpi: ThinkPad ACPI EC access misbehaving, disabling thermal sensors access
```

**Analysis:**
- The thermal daemon doesn't support the Intel Core Ultra 7 255H (Arrow Lake)
- Hardware is too new for current thermal management software
- System cannot monitor temperatures properly

### 5. **No System Logs After Freeze**
- Last log entry: Feb 05 20:11:40 (routine rtkit messages)
- System hung shortly after with no warning messages
- Consistent with a graphics driver deadlock where the system freezes but doesn't crash

---

## Root Cause Assessment

**Primary Cause: Intel i915 Graphics Driver Hang**

The evidence strongly points to a graphics driver issue:
1. Repeated atomic commit failures throughout the day
2. New Arrow Lake-P hardware with potentially incomplete driver support
3. System freeze without kernel panic (GPU hang doesn't trigger kernel panic)
4. No alternative explanation in logs (no OOM, no hardware errors, no thermal issues)

---

## Recommendations

### Immediate Actions

1. **Update to Latest Kernel**
   ```bash
   # Check for newer kernel versions with better Arrow Lake support
   sudo apt update
   sudo apt install linux-generic-hwe-24.04

   # Or try the mainline kernel (6.15+ may have better Arrow Lake support)
   ```

2. **Install Latest Mesa Graphics Drivers**
   ```bash
   sudo add-apt-repository ppa:kisak/kisak-mesa
   sudo apt update
   sudo apt upgrade
   ```

3. **Update Intel Graphics Firmware**
   ```bash
   sudo apt install intel-microcode
   sudo update-initramfs -u
   ```

4. **Monitor GPU Issues**
   ```bash
   # Watch for DRM/i915 errors in real-time
   journalctl -f -k | grep -i "drm\|i915"

   # Check GPU state
   sudo cat /sys/kernel/debug/dri/0/i915_error_state
   ```

### Workarounds (If Issues Persist)

1. **Disable Hardware Cursor (Temporary Fix)**
   Create `/etc/X11/xorg.conf.d/20-intel.conf`:
   ```
   Section "Device"
       Identifier "Intel Graphics"
       Driver "modesetting"
       Option "SWcursor" "true"
   EndSection
   ```

2. **Switch to X11 Instead of Wayland**
   ```bash
   # Edit /etc/gdm3/custom.conf and uncomment:
   # WaylandEnable=false
   ```

3. **Limit PSR (Panel Self Refresh) - Known to Cause Issues**
   ```bash
   # Add kernel parameter
   sudo nano /etc/default/grub
   # Add to GRUB_CMDLINE_LINUX_DEFAULT:
   # i915.enable_psr=0

   sudo update-grub
   ```

4. **Enable GuC/HuC Firmware Submission**
   ```bash
   # Add to kernel parameters:
   # i915.enable_guc=3
   ```

### Long-term Solutions

1. **Consider Using Intel Graphics Backport PPA**
   ```bash
   sudo add-apt-repository ppa:oibaf/graphics-drivers
   sudo apt update && sudo apt upgrade
   ```

2. **Monitor for Kernel Updates**
   - Arrow Lake is very new (2025), driver support is still maturing
   - Kernel 6.15+ or 6.16+ will likely have much better support
   - Ubuntu 24.04.1 or 24.10 may include better drivers

3. **Install Temperature Monitoring**
   ```bash
   sudo apt install lm-sensors
   sudo sensors-detect
   sensors
   ```

4. **Check for BIOS Updates**
   - Visit Lenovo support site for ThinkPad E14 H255
   - Install any available BIOS/firmware updates
   - May include fixes for ACPI/EC issues

---

## Monitoring Commands

To monitor for future issues:

```bash
# Real-time graphics driver monitoring
journalctl -f -k | grep -i "drm\|i915\|gpu"

# Check for hangs
dmesg -w | grep -i "hung\|timeout\|gpu"

# Monitor memory
watch -n 1 free -h

# Check GPU status
sudo intel_gpu_top  # Install: sudo apt install intel-gpu-tools
```

---

## Additional Notes

- Your system has 30GB RAM, so memory is not the issue
- The CPU (Intel Core Ultra 7 255H) is from Intel's latest Arrow Lake generation
- This is cutting-edge hardware with Linux kernel driver support still catching up
- Most issues should resolve with kernel updates over the next few months

---

## Next Steps

1. Apply the immediate actions (kernel/mesa updates)
2. Try the PSR workaround (most likely to help)
3. Monitor system with the provided commands
4. If hangs continue, switch to X11 and disable hardware cursor
5. Check back for kernel updates regularly

---

**Report Generated:** 2026-02-06
**Script Location:** `/tmp/claude-1000/-home-yonatan-dev/425ba907-8282-403d-8da1-348bbc2b0e91/scratchpad/analyze_system_hang.py`
