#!/bin/bash

# Simple Raspberry Pi Deployment Script for Path Data Visualizer & Editor
# This version skips Docker and focuses on reliable Node.js deployment

set -e

echo "🔧 Setting up Path Data Visualizer on Raspberry Pi (Node.js only)..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo "✅ Node.js version: $(node --version)"
echo "✅ npm version: $(npm --version)"

# Use current directory as application directory
APP_DIR=$(pwd)
echo "📂 Using current directory: $APP_DIR"

# Check if we're in the right directory by looking for package.json
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found in current directory"
    echo "   Please navigate to the directory containing your project files first."
    echo "   Current directory: $APP_DIR"
    exit 1
fi

echo "✅ Found project files in: $APP_DIR"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Build the application with ESM fixes for Raspberry Pi
echo "🏗️  Building application..."
if [ -f "build-pi.js" ]; then
    echo "Using Pi-optimized build script..."
    node build-pi.js
elif [ -f "build-simple.js" ]; then
    echo "Using simple build script..."
    node build-simple.js
else
    echo "Building server with ESM compatibility..."
    npx esbuild server/index.ts --platform=node --packages=external --bundle --format=esm --outdir=dist --banner:js="import{fileURLToPath}from'url';import{dirname}from'path';const __filename=fileURLToPath(import.meta.url);const __dirname=dirname(__filename);if(!import.meta.dirname)import.meta.dirname=__dirname;"
    echo "Server build complete - client will be served from development assets"
fi

# Copy the production start script to dist directory
if [ -f "start-production.js" ]; then
    cp start-production.js dist/
    echo "✅ Copied production start script"
    START_SCRIPT="dist/start-production.js"
else
    echo "⚠️  start-production.js not found, using direct execution"
    START_SCRIPT="dist/index.js"
fi

# Check if build was successful
if [ ! -f "dist/index.js" ]; then
    echo "❌ Build failed - dist/index.js not found"
    exit 1
fi

echo "✅ Build completed successfully"

# Create systemd service for auto-start
echo "⚙️  Creating systemd service..."
cat > /tmp/path-editor.service << EOF
[Unit]
Description=Path Data Visualizer & Editor
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/node $APP_DIR/$START_SCRIPT
Restart=always
RestartSec=5
Environment=NODE_ENV=production
Environment=PORT=5000
Environment=HOST=0.0.0.0
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Move the service file with proper permissions
sudo mv /tmp/path-editor.service /etc/systemd/system/path-editor.service

# Enable and start the service
echo "🚀 Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable path-editor
sudo systemctl start path-editor

# Wait a moment for service to start
sleep 3

# Check service status
if sudo systemctl is-active --quiet path-editor; then
    echo "✅ Service started successfully!"
else
    echo "❌ Service failed to start. Checking logs..."
    sudo journalctl -u path-editor --no-pager -n 10
    exit 1
fi

# Get IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo ""
echo "🎉 Installation complete!"
echo ""
echo "🌐 Your Path Data Visualizer is now running at:"
echo "   http://$IP_ADDRESS:5000"
echo "   http://localhost:5000 (from the Pi itself)"
echo ""
echo "📊 Service management commands:"
echo "   sudo systemctl status path-editor   # Check status"
echo "   sudo systemctl restart path-editor  # Restart service"
echo "   sudo systemctl stop path-editor     # Stop service"
echo "   sudo journalctl -u path-editor -f   # View live logs"
echo ""
echo "🔧 To access from other devices on your network:"
echo "   Open a web browser and go to: http://$IP_ADDRESS:5000"