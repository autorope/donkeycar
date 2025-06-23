#!/usr/bin/env python3
"""
Donkey Car Path Editor Server Launcher
Simple Python script to start the Node.js server manually
"""

import subprocess
import sys
import os
import socket
from pathlib import Path

def get_local_ip():
    """Get the local IP address of the Pi"""
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def check_build():
    """Check if the application is built"""
    if not Path("dist/index.js").exists():
        print("❌ Application not built. Please run deployment script first:")
        print("   ./deploy-pi-simple.sh")
        return False
    return True

def main():
    print("🚀 Starting Donkey Car Path Editor...")
    
    # Check if built
    if not check_build():
        sys.exit(1)
    
    # Get IP address
    ip = get_local_ip()
    
    print(f"📱 Server will be accessible at:")
    print(f"   http://{ip}:5000")
    print(f"   http://localhost:5000 (from this Pi)")
    print()
    print("🛑 Press Ctrl+C or use the Exit button in web interface to stop")
    print("=" * 60)
    
    try:
        # Set environment variables and start server
        env = os.environ.copy()
        env.update({
            'NODE_ENV': 'production',
            'PORT': '5000',
            'HOST': '0.0.0.0'
        })
        
        # Start the Node.js server
        if Path("dist/start-production.js").exists():
            cmd = ["node", "dist/start-production.js"]
        else:
            cmd = ["node", "dist/index.js"]
            
        subprocess.run(cmd, env=env)
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()