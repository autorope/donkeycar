#!/bin/bash

# Quick start script for Tornado deployment
# This is the main entry point for Pi users

echo "🚗 Starting Donkey Car Path Editor (Tornado)..."

# Check if this is the first run
if [ ! -f "server-tornado.py" ]; then
    echo "❌ Server files not found. Please run deployment first:"
    echo "   chmod +x deploy-pi-tornado.sh"
    echo "   ./deploy-pi-tornado.sh"
    exit 1
fi

# Check Python and Tornado
if ! python3 -c "import tornado" 2>/dev/null; then
    echo "❌ Tornado not found. Installing..."
    python3 -m pip install --user tornado
fi

# Start the server
echo "🚀 Starting server on port 5000..."
python3 server-tornado.py --port=5000