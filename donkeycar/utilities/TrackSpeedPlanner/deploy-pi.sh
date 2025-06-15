#!/bin/bash

# Raspberry Pi Deployment Script for Path Data Visualizer & Editor
# Run this script on your Raspberry Pi to set up the application

set -e

echo "🔧 Setting up Path Data Visualizer on Raspberry Pi..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "📦 Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Check if Docker is installed (optional but recommended)
if ! command -v docker &> /dev/null; then
    echo "🐳 Attempting to install Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    if sudo sh get-docker.sh; then
        sudo usermod -aG docker $USER
        echo "✅ Docker installed successfully"
        echo "⚠️  Please log out and back in for Docker permissions to take effect"
        
        # Install Docker Compose if Docker installation succeeded
        if ! command -v docker-compose &> /dev/null; then
            echo "📦 Installing Docker Compose..."
            if command -v pip3 &> /dev/null; then
                sudo pip3 install docker-compose
            else
                echo "⚠️  pip3 not found, skipping Docker Compose installation"
            fi
        fi
    else
        echo "⚠️  Docker installation failed, continuing with Node.js only deployment"
        echo "   This is normal and the application will still work perfectly"
    fi
fi

# Create application directory
APP_DIR="/home/$USER/path-editor"
mkdir -p $APP_DIR
cd $APP_DIR

echo "📂 Application will be installed in: $APP_DIR"

# Install dependencies
if [ -f "package.json" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

# Build the application
if [ -f "package.json" ]; then
    echo "🏗️  Building application..."
    npm run build
fi

# Create systemd service for auto-start
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/path-editor.service > /dev/null <<EOF
[Unit]
Description=Path Data Visualizer & Editor
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/node dist/index.js
Restart=always
RestartSec=5
Environment=NODE_ENV=production
Environment=PORT=5000

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable path-editor
sudo systemctl start path-editor

echo "✅ Installation complete!"
echo ""
echo "🌐 Your Path Data Visualizer is now running on:"
echo "   http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "📊 Service commands:"
echo "   sudo systemctl status path-editor   # Check status"
echo "   sudo systemctl restart path-editor  # Restart service"
echo "   sudo systemctl stop path-editor     # Stop service"
echo "   sudo systemctl logs -f path-editor  # View logs"
echo ""
echo "🔧 Alternative Docker deployment:"
echo "   docker-compose up -d               # Start with Docker"
echo "   docker-compose down                # Stop Docker containers"