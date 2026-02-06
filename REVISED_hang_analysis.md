# REVISED System Hang Analysis Report
**CRITICAL UPDATE: ACPI/EC Issues Are Likely a Contributing Factor**

---

## Summary - Compound Failure

The system hang appears to be caused by **TWO separate but related issues**:

1. **ACPI/EC Communication Failure** → No thermal monitoring or fan control
2. **Intel i915 Graphics Driver Issues** → Unstable GPU on new Arrow Lake hardware

**Combined Effect:** System silently overheats over hours → GPU becomes unstable → i915 driver hangs → Complete freeze

---

## Critical Finding: No Thermal Management

Your system has **complete thermal management failure**:

```
thinkpad_acpi: ThinkPad ACPI EC access misbehaving, disabling thermal sensors access
thinkpad_acpi: fan status and control unavailable
thermald: Unsupported cpu model or platform
thermald: Thermald can't run on this platform
```

### What This Means:
- ✗ System **cannot read CPU/GPU temperatures**
- ✗ System **cannot control fan speed**
- ✗ Thermal daemon **cannot run** (doesn't support Arrow Lake)
- ✗ **No active thermal management whatsoever**

### Why This Causes Hangs:
1. System runs for hours without thermal monitoring
2. CPU/GPU temperatures rise unchecked
3. No fan speed adjustment possible
4. Overheated GPU → i915 driver becomes unstable
5. Combined with existing i915 cursor commit issues → Complete freeze

---

## Known Bug: ThinkPad E14 Gen 7 ACPI/EC Issue

This is a **documented bug** affecting ThinkPad E14 Gen 7:
- Bug report exists for fan/thermal sensor access failures
- ACPI EC read/write operations fail with AE_TYPE errors
- Affects multiple E14 Gen 7 units running Linux
- Root cause: Non-standard EC firmware implementation by Lenovo

---

## REVISED Priority Actions

### **HIGHEST PRIORITY: Fix ACPI/EC Errors**

1. **Check and Update BIOS/EC Firmware**
   ```bash
   # Check current BIOS version
   sudo dmidecode -t bios | grep -E "Vendor|Version|Release Date"

   # Your current version from logs:
   # BIOS: R30ET38W(1.12)
   # EC: R30HT38W
   ```

   **Action:** Visit Lenovo support and download latest BIOS/EC firmware:
   - Go to: https://pcsupport.lenovo.com
   - Enter model: ThinkPad E14 Gen 7 (21SX005CIV)
   - Download and install latest BIOS update
   - **This often fixes EC communication issues**

2. **Try ACPI Kernel Parameter Workarounds**
   ```bash
   sudo nano /etc/default/grub
   ```

   Add to `GRUB_CMDLINE_LINUX_DEFAULT`:
   ```
   acpi_ec_no_wakeup acpi_enforce_resources=lax
   ```

   Then:
   ```bash
   sudo update-grub
   sudo reboot
   ```

3. **Manually Monitor Temperatures** (Until Fixed)

   Since thinkpad_acpi can't read temps, try alternative methods:
   ```bash
   # Check if coretemp works (CPU package temp)
   cat /sys/class/thermal/thermal_zone*/temp
   cat /sys/class/thermal/thermal_zone*/type

   # Install and use alternative monitoring
   sudo apt install i7z
   sudo i7z  # Shows CPU temps even without thinkpad_acpi

   # Monitor in real-time
   watch -n 1 'cat /sys/class/thermal/thermal_zone*/temp | awk "{print \$1/1000 \" C\"}"'
   ```

### **HIGH PRIORITY: Mitigate Graphics Issues**

4. **Disable PSR (Panel Self Refresh)**
   ```bash
   sudo nano /etc/default/grub
   ```
   Add `i915.enable_psr=0` to kernel parameters
   ```bash
   sudo update-grub
   sudo reboot
   ```

5. **Update Kernel and Graphics Stack**
   ```bash
   sudo apt update
   sudo apt install linux-generic-hwe-24.04 intel-microcode
   sudo add-apt-repository ppa:kisak/kisak-mesa
   sudo apt update && sudo apt upgrade
   ```

### **MEDIUM PRIORITY: Improve Thermal Handling**

6. **Install Laptop Mode Tools** (Alternative Power Management)
   ```bash
   sudo apt install laptop-mode-tools
   sudo systemctl enable laptop-mode
   sudo systemctl start laptop-mode
   ```

7. **Force CPU Frequency Scaling Governor**
   ```bash
   # Use conservative governor to reduce heat
   echo "conservative" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

   # Make permanent:
   sudo apt install cpufrequtils
   echo 'GOVERNOR="conservative"' | sudo tee /etc/default/cpufrequtils
   ```

8. **Manual Fan Control Workaround**

   Since EC fan control doesn't work, you can't adjust fan manually, but you can:
   - Keep laptop elevated for better airflow
   - Use laptop cooling pad
   - Avoid blocking vents
   - Work in cooler environment

---

## Monitoring Strategy (Until Fixed)

Run this script to monitor temperatures continuously:

```bash
#!/bin/bash
# Save as: ~/monitor_temps.sh

while true; do
    clear
    echo "=== Temperature Monitor ==="
    echo ""

    # Show all thermal zones
    for zone in /sys/class/thermal/thermal_zone*; do
        if [ -f "$zone/temp" ]; then
            type=$(cat "$zone/type" 2>/dev/null || echo "unknown")
            temp=$(cat "$zone/temp" 2>/dev/null)
            temp_c=$((temp / 1000))
            echo "$type: ${temp_c}°C"
        fi
    done

    echo ""
    echo "Fan control: UNAVAILABLE (EC error)"
    echo "Thermal daemon: UNAVAILABLE (unsupported CPU)"
    echo ""

    # Alert if too hot
    for zone in /sys/class/thermal/thermal_zone*; do
        temp=$(cat "$zone/temp" 2>/dev/null)
        temp_c=$((temp / 1000))
        if [ "$temp_c" -gt 85 ]; then
            echo "⚠️  WARNING: Temperature above 85°C! Risk of hang!"
        fi
    done

    sleep 2
done
```

Make executable and run:
```bash
chmod +x ~/monitor_temps.sh
~/monitor_temps.sh
```

---

## Testing the Fix

After applying BIOS update and kernel parameters:

1. **Check if EC access works:**
   ```bash
   dmesg | grep -i thinkpad_acpi
   # Should NOT show "EC access misbehaving"
   ```

2. **Check thermal sensors:**
   ```bash
   sudo apt install lm-sensors
   sudo sensors-detect  # Say YES to all
   sensors
   # Should show fan speeds and temperatures
   ```

3. **Verify fan control:**
   ```bash
   # Check if fan control is available
   ls -la /proc/acpi/ibm/fan
   cat /proc/acpi/ibm/fan
   ```

4. **Monitor for cursor errors:**
   ```bash
   journalctl -f -k | grep -i "cursor\|drm"
   # Should NOT show repeated cursor update failures
   ```

---

## Expected Outcomes

### If BIOS Update Fixes EC Issues:
- ✓ Thermal sensors will work
- ✓ Fan control will be available
- ✓ thermald may start working (if updated for Arrow Lake)
- ✓ System stability will improve significantly
- ✓ Hangs may stop entirely or become very rare

### If Only Graphics Fixes Applied:
- ✓ PSR disabled should reduce i915 cursor errors
- ✓ Newer kernel may have better Arrow Lake support
- ⚠ Still at risk from thermal issues without monitoring

### Best Case (Both Fixed):
- ✓ Full thermal management restored
- ✓ Graphics driver stability improved
- ✓ System should run stable for days/weeks

---

## If Issues Persist After All Fixes

If hangs continue even after BIOS update + kernel update + PSR disabled:

1. **Consider switching to X11** (instead of Wayland)
   ```bash
   sudo nano /etc/gdm3/custom.conf
   # Uncomment: WaylandEnable=false
   ```

2. **Report bug to Lenovo** with ACPI/EC errors
   - Reference: ThinkPad E14 Gen 7 Linux compatibility issue
   - Include: `dmesg | grep -i acpi` output

3. **Report bug to kernel developers**
   - Intel i915 driver issues with Arrow Lake
   - Include: `dmesg | grep -i i915` output

4. **Last resort:** Downgrade to X11 + software cursor
   ```bash
   # /etc/X11/xorg.conf.d/20-intel.conf
   Section "Device"
       Identifier "Intel Graphics"
       Driver "modesetting"
       Option "SWcursor" "true"
   EndSection
   ```

---

## Summary

Your system hang is likely caused by:
1. **Primary:** ACPI/EC firmware bug → No thermal management → Silent overheating
2. **Secondary:** i915 graphics driver instability on new Arrow Lake hardware
3. **Combined:** Overheated GPU + unstable driver = freeze after hours of use

**Fix priority:**
1. BIOS/EC firmware update (most important)
2. Kernel parameters for ACPI workarounds
3. Disable PSR for i915 stability
4. Monitor temperatures manually until fixed

---

**Report Updated:** 2026-02-06
**References:**
- Lenovo Forums: ThinkPad E14 Gen 7 ACPI/EC errors documented
- Kernel Bug #220796: thinkpad-acpi fan not working on E14 Gen 7
- Known issue with non-standard EC firmware on ThinkPad E series
