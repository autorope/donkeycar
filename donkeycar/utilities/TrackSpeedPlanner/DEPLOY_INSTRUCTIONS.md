# How to Deploy Path Data Visualizer on Raspberry Pi

## Step 1: Prepare Your Raspberry Pi

1. **Ensure you have Raspberry Pi OS installed** (Raspberry Pi 3B+ or newer recommended)
2. **Connect to your Pi** via SSH or use the desktop
3. **Update your system**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## Step 2: Transfer Project Files

Choose one of these methods to get the files on your Pi:

### Option A: Clone from Git (if you have a repository)
```bash
git clone [your-repository-url]
cd [project-directory]
```

### Option B: Transfer files manually
1. **Download all project files** from this Replit
2. **Use SCP to transfer** (from your computer):
   ```bash
   scp -r /path/to/project-files pi@[pi-ip-address]:/home/pi/path-editor
   ```
3. **Or use a USB drive** to copy files to `/home/pi/path-editor`

## Step 3: Automated Installation (Recommended)

1. **Navigate to your project directory** (wherever you copied the files):
   ```bash
   cd /path/to/your/project-files
   ```

2. **Make deployment script executable**:
   ```bash
   chmod +x deploy-pi-simple.sh
   ```

3. **Run the automated deployment**:
   ```bash
   ./deploy-pi-simple.sh
   ```

This script will:
- Install Node.js 18
- Install Docker (optional)
- Install project dependencies
- Build the application
- Create a systemd service
- Start the application automatically

## Step 4: Manual Installation (Alternative)

If you prefer manual control:

### Install Node.js
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### Install Dependencies and Build
```bash
cd /home/pi/path-editor
npm install
npm run build
```

### Create Systemd Service
```bash
sudo nano /etc/systemd/system/path-editor.service
```

Paste this content:
```ini
[Unit]
Description=Path Data Visualizer & Editor
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/path-editor
ExecStart=/usr/bin/node dist/index.js
Restart=always
RestartSec=5
Environment=NODE_ENV=production
Environment=PORT=5000

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable path-editor
sudo systemctl start path-editor
```

## Step 5: Docker Installation (Alternative)

For containerized deployment:

### Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker pi
```

### Install Docker Compose
```bash
sudo pip3 install docker-compose
```

### Start with Docker
```bash
cd /home/pi/path-editor
docker-compose up -d
```

## Step 6: Access Your Application

1. **Find your Pi's IP address**:
   ```bash
   hostname -I
   ```

2. **Open web browser** on any device on your network

3. **Navigate to**: `http://[pi-ip-address]:5000`
   - Example: `http://192.168.1.100:5000`

## Managing the Service

### Check Status
```bash
sudo systemctl status path-editor
```

### View Logs
```bash
sudo journalctl -u path-editor -f
```

### Restart Service
```bash
sudo systemctl restart path-editor
```

### Stop Service
```bash
sudo systemctl stop path-editor
```

## Troubleshooting

### Port Already in Use
```bash
sudo netstat -tlnp | grep :5000
sudo systemctl stop path-editor
sudo systemctl start path-editor
```

### Permission Issues
```bash
sudo chown -R pi:pi /home/pi/path-editor
```

### Out of Memory
```bash
# Increase swap space
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

## Network Access

### Local Network Access
- Application will be accessible from any device on your local network
- Use `http://[pi-ip]:5000` from phones, tablets, computers

### Internet Access (Optional)
1. **Configure port forwarding** on your router
2. **Forward external port to Pi port 5000**
3. **Access via**: `http://[your-public-ip]:5000`

**Security Note**: Only enable internet access if needed, and consider setting up HTTPS

## File Structure After Deployment

```
/home/pi/path-editor/
├── dist/                 # Built application
├── client/              # Frontend source
├── server/              # Backend source
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker Compose setup
├── deploy-pi.sh         # Deployment script
├── package.json         # Dependencies
└── README-RaspberryPi.md # Full documentation
```

Your Path Data Visualizer is now running on your Raspberry Pi and accessible from any device on your network!