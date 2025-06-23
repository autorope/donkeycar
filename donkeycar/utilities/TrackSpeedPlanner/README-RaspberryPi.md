# Raspberry Pi Deployment Guide

This guide helps you deploy the Path Data Visualizer & Editor on a Raspberry Pi for donkey car applications.

## Prerequisites

- Raspberry Pi 3B+ or newer (recommended: Pi 4 with 4GB+ RAM)
- Raspberry Pi OS (64-bit recommended)
- Internet connection
- SSH access to your Pi

## Quick Deployment

1. **Copy files to your Pi:**
   ```bash
   scp -r . pi@your-pi-ip:/home/pi/path-editor/
   ```

2. **SSH into your Pi and run deployment:**
   ```bash
   ssh pi@your-pi-ip
   cd /home/pi/path-editor
   chmod +x deploy-pi-simple.sh
   ./deploy-pi-simple.sh
   ```

   *Note: The deployment script automatically cleans up any previous installation.*

## Reinstalling or Updating

If you need to reinstall or had a previous version installed:

1. **Clean uninstall (optional):**
   ```bash
   chmod +x uninstall-pi.sh
   ./uninstall-pi.sh
   ```

2. **Then run the deployment script normally**

The deployment script automatically handles cleanup, but you can manually uninstall first if needed.

3. **Start the server manually:**
   ```bash
   python3 start-server.py
   ```

4. **Access your application:**
   Open a browser and go to: `http://your-pi-ip:5000`

## What the deployment script does:

- Installs Node.js 20 if not present
- Installs project dependencies
- Builds the application with ESM compatibility fixes
- Creates manual start scripts (no auto-start on boot)
- Provides both Python and shell script options

## Manual Setup (if script fails)

1. **Install Node.js 20:**
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
   sudo apt-get install -y nodejs
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Build application:**
   ```bash
   node build-simple.js
   ```

4. **Start manually:**
   ```bash
   python3 start-server.py
   # OR
   NODE_ENV=production PORT=5000 node dist/start-production.js
   ```

## Starting the Server

- **Python launcher:** `python3 start-server.py` (recommended)
- **Shell script:** `./start-server.sh` 
- **Direct Node.js:** `NODE_ENV=production PORT=5000 node dist/start-production.js`

## Network Access

The application runs on port 5000 and is accessible from:
- Local Pi: `http://localhost:5000`
- Network: `http://[pi-ip-address]:5000`
- Find your Pi's IP: `hostname -I`

## Troubleshooting

### Build Errors
- Ensure you have at least 1GB free space
- Check Node.js version: `node --version` (should be 20+)
- Clear npm cache: `npm cache clean --force`

### Service Won't Start
- Check logs: `sudo journalctl -u path-editor -n 50`
- Verify build files exist: `ls -la dist/`
- Check permissions: `ls -la dist/start-production.js`

### Can't Access from Network
- Check firewall: `sudo ufw status`
- Verify Pi's IP: `hostname -I`
- Test locally first: `curl http://localhost:5000`

## Performance Notes

- Raspberry Pi 3B+: Works well for basic editing
- Raspberry Pi 4 (4GB+): Recommended for best performance
- Consider using an SSD for better I/O performance
- Large CSV files (>10MB) may load slowly on older Pis

## Donkey Car Integration

Once deployed, your donkey car can:
1. Upload recorded path data via the web interface
2. Edit speed profiles for different track sections
3. Download modified CSV files for car deployment
4. Access the editor remotely during testing sessions