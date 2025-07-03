#!/bin/bash

# Tornado-based Raspberry Pi deployment script for Path Data Visualizer & Editor
# Uses Python instead of Node.js for better Pi compatibility

set -e

echo "🐍 Setting up Path Data Visualizer on Raspberry Pi (Python/Tornado)..."

# Clean up any previous installation
if [ -f "uninstall-pi.sh" ]; then
    echo "🧹 Cleaning up previous installation..."
    chmod +x uninstall-pi.sh
    ./uninstall-pi.sh
    echo ""
fi

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip
fi

echo "✅ Python version: $(python3 --version)"

# Install Tornado if not available
echo "📦 Installing Python dependencies..."
if ! python3 -c "import tornado" 2>/dev/null; then
    python3 -m pip install --user tornado
    echo "✅ Tornado installed"
else
    echo "✅ Tornado already available"
fi

# Make scripts executable
chmod +x server-tornado.py

# Create startup script
echo "⚙️ Creating startup script..."
cat > start-tornado.py << 'EOF'
#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path

def main():
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Check if server file exists
    if not Path("server-tornado.py").exists():
        print("❌ server-tornado.py not found")
        sys.exit(1)
    
    # Run the tornado server
    try:
        subprocess.run([sys.executable, "server-tornado.py", "--port=5000"])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")

if __name__ == "__main__":
    main()
EOF

chmod +x start-tornado.py

# Get IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo ""
echo "✅ Installation complete!"
echo ""
echo "🚀 To start the server, run:"
echo "   ./trackeditor.sh"
echo "   # OR"
echo "   python3 server-tornado.py"
echo ""
echo "📱 Server will be accessible at:"
echo "   http://$IP_ADDRESS:5000"
echo "   http://localhost:5000 (from the Pi itself)"
echo ""
echo "🛑 To stop the server:"
echo "   Use the Exit button in the web interface"
echo "   Or press Ctrl+C in the terminal"
echo ""
echo "🐍 This version uses Python/Tornado (no Node.js required)"