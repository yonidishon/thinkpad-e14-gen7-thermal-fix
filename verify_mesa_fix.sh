#!/bin/bash
# Verification Script for Mesa Downgrade
# Run this after downgrading Mesa and rebooting

echo "========================================"
echo "Mesa Downgrade Verification"
echo "========================================"
echo ""

# Check 1: Mesa Version
echo "1. Checking Mesa Version"
echo "========================================"
mesa_version=$(apt list --installed 2>/dev/null | grep mesa-vulkan-drivers)
echo "$mesa_version"

if echo "$mesa_version" | grep -q "25.2.8"; then
    echo "✓ Mesa successfully downgraded to 25.2.8"
elif echo "$mesa_version" | grep -q "25.3.4"; then
    echo "✗ Mesa is still at 25.3.4 - downgrade may have failed"
else
    echo "? Mesa version unexpected - please review"
fi
echo ""

# Check 2: XWayland Version
echo "2. Checking XWayland Version"
echo "========================================"
xwayland_version=$(apt list --installed 2>/dev/null | grep "^xwayland/")
echo "$xwayland_version"

if echo "$xwayland_version" | grep -q "23.2.6"; then
    echo "✓ XWayland successfully downgraded to 23.2.6"
elif echo "$xwayland_version" | grep -q "24.1"; then
    echo "✗ XWayland is still at 24.1.x - downgrade may have failed"
else
    echo "? XWayland version unexpected - please review"
fi
echo ""

# Check 3: DSB Error
echo "3. Checking for DSB Error"
echo "========================================"
dsb_errors=$(sudo dmesg 2>&1 | grep -i "DSB.*error")

if [ -z "$dsb_errors" ]; then
    echo "✓ No DSB errors found - issue appears fixed!"
else
    echo "✗ DSB error still present:"
    echo "$dsb_errors"
    echo ""
    echo "This suggests the issue persists. Consider:"
    echo "  - Disabling DSB with kernel parameter: i915.enable_dsb=0"
    echo "  - Switching to X11 instead of Wayland"
fi
echo ""

# Check 4: i915 Initialization
echo "4. Checking i915 Driver Initialization"
echo "========================================"
sudo dmesg 2>&1 | grep "i915.*drm.*Initialized" | head -1
echo ""

# Check 5: Monitor Configuration
echo "5. Checking for Monitor Configuration Errors"
echo "========================================"
monitor_errors=$(journalctl -b 0 --no-pager 2>/dev/null | grep -i "monitor.*built-in.*no configuration")

if [ -z "$monitor_errors" ]; then
    echo "✓ No monitor configuration errors found"
else
    echo "⚠ Monitor configuration errors detected:"
    echo "$monitor_errors" | head -5
fi
echo ""

# Check 6: Cursor Update Errors
echo "6. Checking for Cursor Update Errors"
echo "========================================"
cursor_errors=$(journalctl -b 0 --no-pager 2>/dev/null | grep -i "cursor.*failed.*drm")

if [ -z "$cursor_errors" ]; then
    echo "✓ No cursor update errors found"
else
    echo "⚠ Cursor update errors detected:"
    echo "$cursor_errors" | head -5
fi
echo ""

# Check 7: Package Hold Status
echo "7. Checking Package Hold Status"
echo "========================================"
held_packages=$(apt-mark showhold 2>/dev/null | grep -E "mesa|xwayland")

if [ -n "$held_packages" ]; then
    echo "✓ Packages are held to prevent auto-upgrade:"
    echo "$held_packages"
else
    echo "⚠ Packages are NOT held - may auto-upgrade on next update"
    echo "To hold packages, run:"
    echo "  sudo apt-mark hold mesa-vulkan-drivers libegl-mesa0 libgl1-mesa-dri \\"
    echo "    mesa-va-drivers mesa-vdpau-drivers libglx-mesa0 libgbm1 \\"
    echo "    mesa-libgallium xwayland"
fi
echo ""

# Summary
echo "========================================"
echo "Verification Summary"
echo "========================================"
echo ""
echo "Next Steps:"
echo ""
echo "1. Test lid close behavior:"
echo "   - Close laptop lid (while on AC power)"
echo "   - Wait 10-30 seconds"
echo "   - Open lid and check if system responds normally"
echo ""
echo "2. Monitor system logs during lid close:"
echo "   journalctl -f"
echo ""
echo "3. Check for kernel panics after extended use:"
echo "   - Let system run overnight with lid open"
echo "   - Check temperature logs: tail -f ~/.temp_monitor.log"
echo ""
echo "4. If issues persist, consider:"
echo "   - Switching to X11 (instead of Wayland)"
echo "   - Disabling DSB: i915.enable_dsb=0 in GRUB"
echo "   - Reporting bug to Mesa/i915 developers"
echo ""
