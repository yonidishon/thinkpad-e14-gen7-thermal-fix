#!/bin/bash
# Mesa Downgrade Script
# Downgrades Mesa 25.3.4 (kisak PPA) to Mesa 25.2.8 (Ubuntu stable)
#
# Reason: Mesa 25.3.4 has DSB (Display State Buffer) regression
# causing kernel panics when lid is closed without suspend

set -e  # Exit on error

echo "========================================"
echo "Mesa Downgrade Script"
echo "========================================"
echo ""
echo "This will downgrade Mesa from 25.3.4 (kisak) to 25.2.8 (Ubuntu stable)"
echo ""
echo "Reason:"
echo "  Mesa 25.3.4 has a DSB (Display State Buffer) bug that causes"
echo "  kernel panics when closing the laptop lid without suspending."
echo ""
echo "Evidence:"
echo "  - Crash occurred on first boot after Mesa 25.3.4 update (Feb 6)"
echo "  - DSB poll error appears on every boot with Mesa 25.3.4"
echo "  - Monitor configuration fails when lid closes"
echo "  - System eventually kernel panics (flashing CAPS LOCK)"
echo ""
echo "Packages to downgrade:"
echo "  - mesa-vulkan-drivers:  25.3.4~kisak1~n → 25.2.8-0ubuntu0.24.04.1"
echo "  - libegl-mesa0:         25.3.4~kisak1~n → 25.2.8-0ubuntu0.24.04.1"
echo "  - libgl1-mesa-dri:      25.3.4~kisak1~n → 25.2.8-0ubuntu0.24.04.1"
echo "  - mesa-va-drivers:      25.3.4~kisak1~n → 25.2.8-0ubuntu0.24.04.1"
echo "  - mesa-vdpau-drivers:   25.3.4~kisak1~n → 25.2.8-0ubuntu0.24.04.1"
echo "  - libglx-mesa0:         25.3.4~kisak1~n → 25.2.8-0ubuntu0.24.04.1"
echo "  - libgbm1:              25.3.4~kisak1~n → 25.2.8-0ubuntu0.24.04.1"
echo "  - mesa-libgallium:      25.3.4~kisak1~n → 25.2.8-0ubuntu0.24.04.1"
echo "  - xwayland:             24.1.6~kisak1~n → 23.2.6-1ubuntu0.8"
echo ""
echo "After downgrade, packages will be HELD to prevent auto-upgrade."
echo ""
echo "Press Ctrl+C to cancel, or Enter to continue..."
read

echo ""
echo "Step 1: Downgrading Mesa packages..."
echo "========================================"

sudo apt install --allow-downgrades \
  mesa-vulkan-drivers=25.2.8-0ubuntu0.24.04.1 \
  libegl-mesa0=25.2.8-0ubuntu0.24.04.1 \
  libgl1-mesa-dri=25.2.8-0ubuntu0.24.04.1 \
  mesa-va-drivers=25.2.8-0ubuntu0.24.04.1 \
  mesa-vdpau-drivers=25.2.8-0ubuntu0.24.04.1 \
  libglx-mesa0=25.2.8-0ubuntu0.24.04.1 \
  libgbm1=25.2.8-0ubuntu0.24.04.1 \
  mesa-libgallium=25.2.8-0ubuntu0.24.04.1 \
  xwayland=2:23.2.6-1ubuntu0.8

echo ""
echo "Step 2: Holding packages to prevent automatic upgrade..."
echo "========================================"

sudo apt-mark hold \
  mesa-vulkan-drivers \
  libegl-mesa0 \
  libgl1-mesa-dri \
  mesa-va-drivers \
  mesa-vdpau-drivers \
  libglx-mesa0 \
  libgbm1 \
  mesa-libgallium \
  xwayland

echo ""
echo "========================================"
echo "Downgrade Complete!"
echo "========================================"
echo ""
echo "Verification:"
apt list --installed 2>/dev/null | grep mesa-vulkan-drivers

echo ""
echo "Next steps:"
echo "  1. Reboot your system"
echo "  2. After reboot, check for DSB error:"
echo "     dmesg | grep -i 'DSB.*error'"
echo "     (Should return nothing)"
echo ""
echo "  3. Test lid close behavior"
echo "  4. Check for errors:"
echo "     journalctl -b 0 --no-pager | grep -i 'cursor.*failed'"
echo "     journalctl -b 0 --no-pager | grep -i 'monitor.*built-in'"
echo ""
echo "  5. To unhold packages later (when Mesa is fixed):"
echo "     sudo apt-mark unhold mesa-vulkan-drivers libegl-mesa0 libgl1-mesa-dri \\"
echo "       mesa-va-drivers mesa-vdpau-drivers libglx-mesa0 libgbm1 \\"
echo "       mesa-libgallium xwayland"
echo ""
echo "See Analysis_Process.md for full investigation details."
echo ""
