# Donkey Car Path Data Visualizer & Editor

A web-based tool for visualizing and editing Donkey Car path data CSV files. This application provides an intuitive interface to load, visualize, and modify speed values for autonomous vehicle path planning.

## Features

### 🎯 **Interactive Path Visualization**
- Canvas-based path display with automatic scaling and centering
- Color-coded speed visualization (red = slow, green = fast)
- Click-to-select path points with visual feedback
- Real-time updates as you modify speed values

### 📁 **Flexible File Operations**
- **Pi Directory Access**: Browse and load CSV files directly from the server directory
- **Upload from Browser**: Drag-and-drop or click to upload CSV files from your computer
- **Dual Save Options**: 
  - Save back to Pi directory (for server files)
  - Download to local machine (for uploaded files)

### ⚡ **Speed Editing**
- Individual speed controls for each path point
- Speed range: 0.1 to 1.0 in 0.1 increments
- Auto-scroll to selected point's controls
- Instant visual feedback on canvas

### 📱 **Responsive Design**
- Works on desktop, tablet, and mobile devices
- Adaptive layout that adjusts to screen size
- Touch-friendly controls for mobile editing

## Quick Start

### 1. Start the Server
```bash
# Default port (note: avoid port 5000 on macOS due to AirPlay conflict)
python trackeditor.py --port=8080

# With debug mode
python trackeditor.py --port=8080 --debug
```

### 2. Access the Application
Open your browser and navigate to:
- **Local**: http://localhost:8080
- **Network**: http://[your-ip]:8080

### 3. Load Path Data
Choose one of these methods:
- **From Pi Directory**: Use the dropdown to select existing CSV files
- **Upload File**: Drag & drop or click the upload area

### 4. Edit and Save
- Click on path points to select them
- Adjust speed values using the right panel controls
- Save your changes back to the Pi or download locally

## Server Configuration

### Command Line Options
```bash
python trackeditor.py --help
```

Available options:
- `--port=PORT`: Server port (default: 5000, recommend 8080 on macOS)
- `--debug`: Enable debug mode with detailed logging

### API Endpoints
- `GET /`: Main application interface
- `GET /api/health`: Server health check
- `GET /api/files`: List CSV files in server directory
- `POST /api/upload`: Upload CSV file from browser
- `POST /api/loadfile`: Load CSV file from server directory
- `POST /api/save`: Save modifications back to server
- `POST /api/export`: Download modified CSV file
- `POST /api/shutdown`: Graceful server shutdown

## CSV File Format

The application supports CSV files with the following formats:

### With Headers (Recommended)
```csv
x,y,speed
10.5,20.3,0.8
11.2,21.0,0.7
12.1,22.5,0.9
```

### Alternative Headers
Also supports: `pos_x,pos_y,throttle` and `X,Y,Speed`

### Without Headers
```csv
10.5,20.3,0.8
11.2,21.0,0.7
12.1,22.5,0.9
```

**Notes:**
- Speed values are automatically clamped to 0.1-1.0 range
- Missing speed values default to 0.5
- Invalid rows are skipped with console warnings

## File Structure

```
TrackSpeedPlanner/
├── trackeditor.py          # Main Tornado web server
├── static/
│   └── index.html         # Complete web interface (HTML/CSS/JS)
├── test_path.csv          # Sample CSV file
└── attached_assets/       # Additional CSV files
```

## Requirements

- **Python 3.6+**
- **Tornado web framework**
You should run this out of your donkey environment which has python=3.11 with 
tornado installed. The above is only relevant when running out of another 
environment. Please see next section for that.

### Installation
```bash
# Install Tornado if not available
pip install tornado

# Or with conda
conda install tornado
```

## Technical Details

### Visualization Engine
- **Canvas Size**: 800x600 pixels (responsive)
- **Auto-scaling**: Automatically fits path data to canvas
- **Color Coding**: RGB interpolation based on speed values
- **Selection Radius**: 15-pixel click detection around points

### Performance
- **Raspberry Pi Zero/1**: Suitable for small to medium paths
- **Raspberry Pi 2/3**: Good performance for typical donkey car paths  
- **Raspberry Pi 4+**: Excellent performance with large datasets
- **Desktop/Laptop**: Handles very large path files efficiently

### Browser Compatibility
- Modern browsers with HTML5 Canvas support
- Chrome, Firefox, Safari, Edge
- Mobile browsers on iOS and Android

## Troubleshooting

### Server Won't Start
```bash
# Check Python version
python --version  # Should be 3.6+

# Install Tornado
pip install tornado

# Check port availability (especially on macOS)
lsof -i :5000  # If in use, try different port
python trackeditor.py --port=8080
```

### Can't Access from Network
```bash
# Check your IP address
hostname -I        # Linux/Pi
ipconfig          # Windows  
ifconfig          # macOS

# Test locally first
curl http://localhost:8080/api/health
```

### File Upload Issues
- Ensure files have `.csv` extension
- Check file format matches expected CSV structure
- Large files may take time to process on slower hardware

### Port 5000 Conflicts (macOS)
macOS uses port 5000 for AirPlay. Use an alternative port:
```bash
python trackeditor.py --port=8080
```

## Integration with Donkey Car

This tool is designed to work with Donkey Car path planning:

1. **Record Paths**: Use Donkey Car to record driving paths
2. **Edit Speeds**: Load and modify speed profiles using this tool
3. **Deploy**: Save edited paths back to your Donkey Car for autonomous driving

## Development

### Server Development
- Edit `trackeditor.py` for backend changes
- Supports hot reload in debug mode: `--debug`

### Frontend Development  
- Edit `static/index.html` for UI changes
- Contains all HTML, CSS, and JavaScript in a single file
- Refresh browser to see changes

### Adding Features
The application uses a RESTful API design. To add new functionality:
1. Create new handler class in `trackeditor.py`
2. Add route to `make_app()` function
3. Implement frontend calls in `static/index.html`

## License

This tool is part of the Donkey Car project and follows the same open-source principles.