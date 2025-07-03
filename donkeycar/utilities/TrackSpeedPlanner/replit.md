# Donkey Car Path Data Visualizer & Editor

## Overview

This is a Python-based web application for visualizing and editing donkey car path data. The application allows users to upload CSV files containing path coordinates and speed values, visualize them on an interactive canvas, edit speed values through a control panel, and export modified data back to CSV format.

## System Architecture

The application uses a lightweight Python Tornado web server architecture optimized for Raspberry Pi deployment:

### Server Architecture
- **Runtime**: Python 3.6+ with Tornado web framework
- **Language**: Python with async/await support
- **Web Server**: Tornado (lightweight, efficient, great for embedded systems)
- **Static Files**: Single HTML file with embedded CSS/JavaScript
- **Data Processing**: Pure Python CSV parsing and generation

### Frontend Architecture
- **Technology**: Vanilla JavaScript with HTML5 Canvas
- **UI Components**: Custom CSS with responsive design
- **File Upload**: Drag-and-drop interface with validation
- **Visualization**: Interactive HTML5 canvas for path rendering
- **Controls**: Dynamic speed adjustment dropdowns

## Key Components

### Python Server Components
1. **Main Server** (`server-tornado.py`): Tornado web server handling all HTTP requests
2. **CSV Handler**: File upload and parsing functionality
3. **Static Handler**: Serves the web interface and assets
4. **Shutdown Handler**: Graceful server termination endpoint
5. **Health Check**: Server status monitoring

### Web Interface Components
1. **Upload Interface**: Drag-and-drop CSV file upload with validation
2. **Path Canvas**: Interactive HTML5 canvas for path visualization with point selection
3. **Speed Controls**: Dynamic speed adjustment interface for each path point
4. **Export Function**: CSV generation and download functionality
5. **Exit Control**: Clean server shutdown from web interface

## Data Flow

1. **File Upload**: Users drag/drop or select CSV files containing path data (x, y, speed coordinates)
2. **Data Parsing**: CSV content is parsed client-side into PathDataPoint objects
3. **Visualization**: Path data is rendered on HTML5 canvas with interactive point selection
4. **Speed Editing**: Users can modify speed values through dropdown controls
5. **Data Export**: Modified data can be exported back to CSV format for download

### Data Structure
```typescript
interface PathDataPoint {
  x: number;      // X coordinate
  y: number;      // Y coordinate  
  speed: number;  // Speed value (0.1 to 1.0)
  index: number;  // Sequence index
}
```

## External Dependencies

### Core Dependencies
- **Python 3.6+**: Required for async/await support and modern Python features
- **Tornado**: Lightweight web server framework (usually pre-installed on Pi)
- **Standard Library**: Uses only Python built-in modules for CSV processing

### Optional Dependencies
- **None**: The application is designed to run with minimal dependencies
- **Tornado Installation**: Automatically installed if not present via pip

### System Requirements
- **Raspberry Pi**: Compatible with all models (Pi Zero to Pi 5)
- **Python Version**: 3.6 or higher (standard on modern Pi images)
- **Memory**: Minimal RAM usage, suitable for Pi Zero
- **Storage**: Less than 1MB total application size

## Deployment Strategy

### Raspberry Pi Deployment (Primary)
- **Target Platform**: All Raspberry Pi models (Zero, 3B+, 4, 5)
- **Python Version**: 3.6+ (standard on modern Pi images)
- **Installation**: Automated via `deploy-pi-tornado.sh` script
- **Network Access**: Accessible on local network via Pi's IP address
- **Manual Start**: No auto-boot service, controlled via `trackeditor.sh`

### Deployment Process
1. **File Transfer**: Copy project files to Pi via SCP or direct download
2. **Dependency Check**: Automatically installs Tornado if not present
3. **Permission Setup**: Makes scripts executable
4. **Server Start**: Launch via `./trackeditor.sh` command
5. **Access**: Web interface available at `http://pi-ip:5000`

### Environment Configuration
- **Port Configuration**: Configurable via command line (default: 5000)
- **Host Binding**: Configured for 0.0.0.0 (accessible from network)
- **Static Assets**: Embedded in single HTML file for simplicity
- **No Database**: File-based operation, no persistent storage needed
- **Clean Shutdown**: Exit button and graceful termination support

## Changelog

```
Changelog:
- June 14, 2025. Initial setup
- June 14, 2025. Enhanced user interface:
  * Moved Export CSV button to upload area for better accessibility
  * Made file upload area more compact
  * Fixed CSV parsing to ensure proper speed value loading
  * Added visible speed display in speed controls sidebar
  * Improved speed dropdown formatting for better clarity
- June 14, 2025. Added Raspberry Pi deployment support:
  * Created Docker configuration for ARM compatibility
  * Added automated deployment script (deploy-pi.sh)
  * Configured systemd service for auto-start
  * Added comprehensive Pi deployment documentation
  * Updated server configuration for flexible host/port binding
- June 15, 2025. Fixed ESM import.meta.dirname production build issues:
  * Created build-simple.js for Pi-optimized builds with ESM polyfills
  * Added start-production.js with proper import.meta.dirname handling
  * Updated deploy-pi-simple.sh with multiple build script fallbacks
  * Created comprehensive README-RaspberryPi.md deployment guide
  * Resolved production build failures for Node.js ESM modules
- June 15, 2025. Modified deployment for manual start and added Exit functionality:
  * Removed auto-start systemd service configuration
  * Created start-server.py Python launcher for manual server control
  * Added Exit button to web interface header with clean shutdown
  * Implemented /api/shutdown route for graceful server termination
  * Updated deployment scripts to support manual-only server operation
  * Created uninstall-pi.sh script for clean removal of previous installations
  * Integrated automatic cleanup into deployment process
- June 23, 2025. Added Python Tornado server option for Raspberry Pi:
  * Created server-tornado.py as lightweight alternative to Node.js
  * Built complete HTML/CSS/JS interface in single static file
  * Added deploy-pi-tornado.sh for Python-only deployment
  * Implemented all CSV upload, editing, and export features in Python
  * Tested Tornado server with health checks and graceful shutdown
  * Created trackeditor.sh as main entry point for Pi users
  * Optimized for all Pi models including Pi Zero
  * Made Tornado the recommended deployment option
- July 3, 2025. Cleaned up project to use Tornado exclusively:
  * Removed all Node.js dependencies and configuration files
  * Removed Docker deployment files and scripts
  * Updated .gitignore for Python-only project
  * Simplified project structure to focus on Tornado server
  * Renamed start script to trackeditor.sh per user request
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
Deployment preference: Python-only using Tornado server (no Node.js dependencies).
```