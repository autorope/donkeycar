# Tornado Python Server Deployment for Raspberry Pi

This is a Python-based alternative to the Node.js deployment, using the Tornado web server that's already available on most Raspberry Pi systems.

## Why Use Tornado Version? (Recommended)

- **No Node.js required**: Uses existing Python environment on Pi
- **Lightweight**: Better performance on all Pi models including Pi Zero
- **Minimal dependencies**: Only requires Python and Tornado (usually pre-installed)
- **Faster setup**: No compilation or build steps needed
- **Same functionality**: Full CSV upload, editing, and export features
- **Identical UI**: Same web interface as Node.js version
- **Better reliability**: Python's stability on embedded systems

## Quick Deployment

1. **Copy files to your Pi:**
   ```bash
   scp -r . pi@your-pi-ip:/home/pi/path-editor/
   ```

2. **SSH into your Pi and run Tornado deployment:**
   ```bash
   ssh pi@your-pi-ip
   cd /home/pi/path-editor
   chmod +x deploy-pi-tornado.sh
   ./deploy-pi-tornado.sh
   ```

3. **Start the server:**
   ```bash
   ./trackeditor.sh
   # OR
   python3 server-tornado.py
   ```

4. **Access your application:**
   Open browser: `http://your-pi-ip:5000`

## Features

- **CSV Upload**: Drag-and-drop or browse for path data files
- **Interactive Visualization**: Canvas-based path display with speed colors
- **Speed Editing**: Click points to adjust speed values (0.1-1.0)
- **CSV Export**: Download modified path data
- **Exit Button**: Clean server shutdown via web interface
- **Mobile Responsive**: Works on phones and tablets

## File Structure

```
path-editor/
├── server-tornado.py      # Main Tornado web server
├── start-tornado.py       # Startup script
├── deploy-pi-tornado.sh   # Deployment script
├── static/
│   └── index.html        # Complete web interface
└── uninstall-pi.sh       # Cleanup script
```

## Manual Setup

If the deployment script fails:

1. **Install dependencies:**
   ```bash
   python3 -m pip install --user tornado
   ```

2. **Run server directly:**
   ```bash
   python3 server-tornado.py --port=5000
   ```

## Server Options

The Tornado server supports command-line options:

```bash
python3 server-tornado.py --port=5000 --debug
```

Options:
- `--port=PORT`: Server port (default: 5000)
- `--debug`: Enable debug mode with auto-reload

## API Endpoints

- `GET /`: Main application interface
- `POST /api/upload`: CSV file upload
- `POST /api/export`: CSV file export
- `POST /api/shutdown`: Server shutdown
- `GET /api/health`: Health check

## Performance Notes

- **Raspberry Pi Zero/1**: Works but may be slow with large files
- **Raspberry Pi 2/3**: Good performance for typical donkey car paths
- **Raspberry Pi 4+**: Excellent performance, handles large datasets

## Troubleshooting

### Server Won't Start
```bash
# Check Python version (3.6+ required)
python3 --version

# Install Tornado if missing
python3 -m pip install --user tornado

# Check if port is in use
sudo netstat -tlnp | grep :5000
```

### Can't Access from Network
```bash
# Check Pi's IP address
hostname -I

# Test locally first
curl http://localhost:5000/api/health

# Check firewall (if enabled)
sudo ufw status
```

### Memory Issues
```bash
# Check available memory
free -h

# For large CSV files, consider splitting them
# Or use Pi 4 with more RAM
```

## Comparison with Node.js Version

| Feature | Tornado | Node.js |
|---------|---------|---------|
| Setup Time | Faster | Slower |
| Dependencies | Minimal | Many |
| Memory Usage | Lower | Higher |
| Performance | Good | Excellent |
| Compatibility | All Pi models | Pi 3+ recommended |

## Integration with Donkey Car

The Tornado version is ideal for donkey car integration:

1. **Lightweight**: Runs alongside other Pi services
2. **Quick Start**: No compilation, instant startup
3. **Reliable**: Python's stability on Pi systems
4. **Portable**: Easy to backup and restore

## Development

To modify the server:

1. Edit `server-tornado.py` for backend changes
2. Edit `static/index.html` for frontend changes
3. Restart server to see changes

The server includes auto-reload in debug mode:
```bash
python3 server-tornado.py --debug
```