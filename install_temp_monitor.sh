#!/bin/bash
# Quick installation script for temperature monitor

set -e

echo "========================================"
echo "ThinkPad E14 Temperature Monitor Setup"
echo "========================================"
echo ""

# Check if running in graphical environment
if [ -z "$DISPLAY" ]; then
    echo "Warning: No graphical display detected."
    echo "The GUI notifications may not work without a display."
    echo ""
fi

# Ensure notify-send is available
if ! command -v notify-send &> /dev/null; then
    echo "Installing libnotify-bin for desktop notifications..."
    sudo apt update
    sudo apt install -y libnotify-bin
fi

# Ask user which method they prefer
echo "Choose installation method:"
echo "  1) Systemd user service (recommended - runs in background)"
echo "  2) Autostart desktop entry (runs when you log in)"
echo "  3) Cancel"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "Installing as systemd user service..."
        mkdir -p ~/.config/systemd/user
        cp temp-monitor.service ~/.config/systemd/user/
        systemctl --user daemon-reload
        systemctl --user enable temp-monitor.service
        systemctl --user start temp-monitor.service

        echo ""
        echo "✓ Temperature monitor installed and started!"
        echo ""
        echo "Check status with:"
        echo "  systemctl --user status temp-monitor.service"
        echo ""
        echo "View logs with:"
        echo "  journalctl --user -u temp-monitor.service -f"
        echo "  tail -f ~/.temp_monitor.log"
        echo ""
        echo "Disable with:"
        echo "  systemctl --user stop temp-monitor.service"
        echo "  systemctl --user disable temp-monitor.service"
        ;;

    2)
        echo ""
        echo "Installing as autostart application..."
        mkdir -p ~/.config/autostart
        cp temp-monitor.desktop ~/.config/autostart/

        # Start it now
        echo "Starting monitor now..."
        ./temp_monitor_gui.sh &

        echo ""
        echo "✓ Temperature monitor installed!"
        echo ""
        echo "It will start automatically when you log in."
        echo ""
        echo "View logs with:"
        echo "  tail -f ~/.temp_monitor.log"
        echo ""
        echo "Disable with:"
        echo "  rm ~/.config/autostart/temp-monitor.desktop"
        echo "  pkill -f temp_monitor_gui.sh"
        ;;

    3)
        echo "Installation cancelled."
        exit 0
        ;;

    *)
        echo "Invalid choice. Installation cancelled."
        exit 1
        ;;
esac

echo ""
echo "Testing notification system..."
notify-send -u normal "Temperature Monitor" "Installation complete! You will receive alerts if temperature exceeds 85°C."

echo ""
echo "Done! See SETUP_INSTRUCTIONS.md for full documentation."
