# Quick Start Guide - Raspberry Pi Deployment

## For Donkey Car Path Data Editor

### 1. Copy to Pi
```bash
scp -r . pi@your-pi-ip:/home/pi/path-editor/
```

### 2. Start Server
```bash
chmod +x trackeditor.sh
./trackeditor.sh
```

### 3. Access
Open browser: `http://your-pi-ip:5000`

### 4. Stop Server
- Use Exit button in web interface
- Or press Ctrl+C in terminal

---

## Features
- Upload CSV path files (drag & drop)
- Interactive path visualization
- Edit speed values by clicking points
- Export modified CSV files
- Works on all Pi models (Zero to Pi 5)

## Files Included
- `server-tornado.py` - Main Python server
- `trackeditor.sh` - Simple startup script  
- `deploy-pi-tornado.sh` - Installation script
- `static/index.html` - Complete web interface
- `uninstall-pi.sh` - Cleanup script

## Troubleshooting
- **Server won't start**: Check `python3 --version` (need 3.6+)
- **Can't access**: Use Pi's actual IP, not localhost
- **Tornado missing**: Run `python3 -m pip install --user tornado`