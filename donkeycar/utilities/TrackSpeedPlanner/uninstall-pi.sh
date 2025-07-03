#!/bin/bash

echo "🧹 Uninstalling Path Data Visualizer & Editor..."

# Stop and disable the systemd service if it exists
if systemctl is-active --quiet path-editor 2>/dev/null; then
    echo "🛑 Stopping running service..."
    sudo systemctl stop path-editor
fi

if systemctl is-enabled --quiet path-editor 2>/dev/null; then
    echo "❌ Disabling auto-start service..."
    sudo systemctl disable path-editor
fi

# Remove systemd service file
if [ -f "/etc/systemd/system/path-editor.service" ]; then
    echo "🗑️  Removing systemd service..."
    sudo rm -f /etc/systemd/system/path-editor.service
    sudo systemctl daemon-reload
fi

# Get current directory for cleanup
CURRENT_DIR=$(pwd)
APP_DIR="$HOME/path-editor"

# If we're in the app directory, clean it up
if [[ "$CURRENT_DIR" == *"path-editor"* ]]; then
    echo "🧹 Cleaning up application files..."
    
    # Remove build artifacts
    rm -rf dist/ node_modules/ .next/ 2>/dev/null
    
    # Remove generated files
    rm -f start-server.sh start-server.py 2>/dev/null
    
    echo "✅ Current directory cleaned"
else
    # Clean up the typical installation directory
    if [ -d "$APP_DIR" ]; then
        echo "🗑️  Removing application directory: $APP_DIR"
        rm -rf "$APP_DIR"
    fi
fi

# Check for any running Node.js processes on port 5000
echo "🔍 Checking for running processes..."
PIDS=$(lsof -ti:5000 2>/dev/null)
if [ ! -z "$PIDS" ]; then
    echo "🛑 Stopping processes on port 5000..."
    sudo kill -TERM $PIDS 2>/dev/null || true
    sleep 2
    # Force kill if still running
    PIDS=$(lsof -ti:5000 2>/dev/null)
    if [ ! -z "$PIDS" ]; then
        sudo kill -KILL $PIDS 2>/dev/null || true
    fi
fi

echo ""
echo "✅ Uninstall complete!"
echo ""
echo "The system is now clean and ready for a fresh installation."
echo "You can now run the deployment script safely:"
echo "   ./deploy-pi-simple.sh"