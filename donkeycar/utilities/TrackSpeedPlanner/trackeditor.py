#!/usr/bin/env python3
"""
Donkey Car Path Data Visualizer & Editor - Tornado Server
Python-based web server for Raspberry Pi deployment
"""

import os
import json
import csv
import io
import sys
import signal
import socket
from pathlib import Path
from typing import List, Dict, Any

import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.options import define, options

# Configuration
define("port", default=5000, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode")

class PathDataPoint:
    """Path data point structure matching the original schema"""
    def __init__(self, x: float, y: float, speed: float, index: int):
        self.x = x
        self.y = y
        self.speed = speed
        self.index = index
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'x': self.x,
            'y': self.y,
            'speed': self.speed,
            'index': self.index
        }

class MainHandler(tornado.web.RequestHandler):
    """Serve the main HTML page"""
    
    def get(self):
        print("Serving main page")
        self.render("static/index.html")

class StaticFileHandler(tornado.web.StaticFileHandler):
    """Custom static file handler with proper headers"""
    
    def set_default_headers(self):
        self.set_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.set_header("Pragma", "no-cache")
        self.set_header("Expires", "0")

class CSVUploadHandler(tornado.web.RequestHandler):
    """Handle CSV file uploads and parsing"""
    
    def post(self):
        try:
            if not self.request.files.get('file'):
                self.set_status(400)
                self.write({'error': 'No file uploaded'})
                return
            
            file_data = self.request.files['file'][0]
            filename = file_data['filename']
            content = file_data['body'].decode('utf-8')
            
            # Parse CSV content
            path_data = self.parse_csv(content)
            
            self.write({
                'filename': filename,
                'data': [point.to_dict() for point in path_data],
                'count': len(path_data)
            })
            
        except Exception as e:
            self.set_status(400)
            self.write({'error': str(e)})
    
    def parse_csv(self, content: str) -> List[PathDataPoint]:
        """Parse CSV content into PathDataPoint objects"""
        points = []
        lines = content.strip().split('\n')
        
        # Check if first line looks like headers
        first_line = lines[0].lower()
        has_headers = any(col in first_line for col in ['x', 'y', 'speed', 'pos_x', 'pos_y'])
        
        if has_headers:
            # Use DictReader for CSV with headers
            reader = csv.DictReader(io.StringIO(content))
            for i, row in enumerate(reader):
                try:
                    x = float(row.get('x', row.get('X', row.get('pos_x', row.get('pos_X', 0)))))
                    y = float(row.get('y', row.get('Y', row.get('pos_y', row.get('pos_Y', 0)))))
                    speed = float(row.get('speed', row.get('Speed', row.get('throttle', 0.5))))
                    
                    # Ensure speed is within valid range
                    speed = max(0.1, min(1.0, speed))
                    
                    points.append(PathDataPoint(x, y, speed, i))
                    
                except (ValueError, KeyError) as e:
                    print(f"Error parsing row {i}: {e}")
                    continue
        else:
            # Parse as raw CSV values (x, y, speed)
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                try:
                    values = [v.strip() for v in line.split(',')]
                    if len(values) >= 2:
                        x = float(values[0])
                        y = float(values[1])
                        speed = float(values[2]) if len(values) > 2 else 0.5
                        
                        # Ensure speed is within valid range
                        speed = max(0.1, min(1.0, speed))
                        
                        points.append(PathDataPoint(x, y, speed, i))
                        
                except (ValueError, IndexError) as e:
                    print(f"Error parsing line {i}: {e}")
                    continue
        
        return points

class CSVSaveHandler(tornado.web.RequestHandler):
    """Handle saving CSV files back to Pi directory"""
    
    def post(self):
        try:
            data = json.loads(self.request.body)
            path_data = data.get('pathData', [])
            filename = data.get('filename')
            
            if not path_data:
                self.set_status(400)
                self.write({'error': 'No path data provided'})
                return
                
            if not filename:
                self.set_status(400)
                self.write({'error': 'No filename provided'})
                return
            
            # Generate CSV content
            csv_content = self.generate_csv(path_data)
            
            # Save to Pi directory
            file_path = os.path.join(os.getcwd(), filename)
            with open(file_path, 'w', newline='') as f:
                f.write(csv_content)
            
            self.write({'success': True, 'message': f'File saved to {filename}'})
            
        except Exception as e:
            self.set_status(400)
            self.write({'error': str(e)})
    
    def generate_csv(self, path_data: List[Dict]) -> str:
        """Generate CSV content from path data"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        for point in path_data:
            writer.writerow([point['x'], point['y'], point['speed']])
        
        return output.getvalue()

class CSVExportHandler(tornado.web.RequestHandler):
    """Handle CSV export functionality"""
    
    def post(self):
        try:
            data = json.loads(self.request.body)
            path_data = data.get('pathData', [])
            filename = data.get('filename', 'modified_path_data.csv')
            
            # Generate CSV content
            csv_content = self.generate_csv(path_data)
            
            self.set_header('Content-Type', 'text/csv')
            self.set_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.write(csv_content)
            
        except Exception as e:
            self.set_status(400)
            self.write({'error': str(e)})
    
    def generate_csv(self, path_data: List[Dict]) -> str:
        """Generate CSV content from path data"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['x', 'y', 'speed'])
        
        # Write data rows
        for point in path_data:
            writer.writerow([point['x'], point['y'], point['speed']])
        
        return output.getvalue()

class ShutdownHandler(tornado.web.RequestHandler):
    """Handle graceful script shutdown"""
    
    def post(self):
        print("Script shutdown requested via web interface")
        self.write({'message': 'Python script stopping...'})
        
        # Schedule script exit after response is sent
        tornado.ioloop.IOLoop.current().call_later(1.0, self.exit_script)
    
    def exit_script(self):
        print("Python script exiting gracefully")
        import sys
        sys.exit(0)

class HealthHandler(tornado.web.RequestHandler):
    """Health check endpoint"""
    
    def get(self):
        self.write({'status': 'ok', 'server': 'tornado'})

class FileListHandler(tornado.web.RequestHandler):
    """List CSV files in the current directory"""
    
    def get(self):
        try:
            current_dir = Path(__file__).parent
            csv_files = []
            
            # Get all CSV files in the current directory
            for file_path in current_dir.glob("*.csv"):
                csv_files.append({
                    'name': file_path.name,
                    'size': file_path.stat().st_size,
                    'modified': file_path.stat().st_mtime
                })
            
            # Sort by name
            csv_files.sort(key=lambda x: x['name'])
            
            self.write({
                'files': csv_files,
                'directory': str(current_dir)
            })
            
        except Exception as e:
            self.set_status(500)
            self.write({'error': str(e)})

class ServerFileHandler(tornado.web.RequestHandler):
    """Load CSV file from server directory"""
    
    def post(self):
        try:
            data = json.loads(self.request.body)
            filename = data.get('filename', '')
            
            if not filename.endswith('.csv'):
                self.set_status(400)
                self.write({'error': 'Invalid file type'})
                return
            
            current_dir = Path(__file__).parent
            file_path = current_dir / filename
            
            if not file_path.exists() or not file_path.is_file():
                self.set_status(404)
                self.write({'error': 'File not found'})
                return
            
            # Read and parse the CSV file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            path_data = self.parse_csv(content)
            
            self.write({
                'filename': filename,
                'data': [point.to_dict() for point in path_data],
                'count': len(path_data)
            })
            
        except Exception as e:
            self.set_status(400)
            self.write({'error': str(e)})
    
    def parse_csv(self, content: str) -> List[PathDataPoint]:
        """Parse CSV content into PathDataPoint objects"""
        points = []
        lines = content.strip().split('\n')
        
        # Check if first line looks like headers
        first_line = lines[0].lower()
        has_headers = any(col in first_line for col in ['x', 'y', 'speed', 'pos_x', 'pos_y'])
        
        if has_headers:
            # Use DictReader for CSV with headers
            reader = csv.DictReader(io.StringIO(content))
            for i, row in enumerate(reader):
                try:
                    x = float(row.get('x', row.get('X', row.get('pos_x', row.get('pos_X', 0)))))
                    y = float(row.get('y', row.get('Y', row.get('pos_y', row.get('pos_Y', 0)))))
                    speed = float(row.get('speed', row.get('Speed', row.get('throttle', 0.5))))
                    
                    # Ensure speed is within valid range
                    speed = max(0.1, min(1.0, speed))
                    
                    points.append(PathDataPoint(x, y, speed, i))
                    
                except (ValueError, KeyError) as e:
                    print(f"Error parsing row {i}: {e}")
                    continue
        else:
            # Parse as raw CSV values (x, y, speed)
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                try:
                    values = [v.strip() for v in line.split(',')]
                    if len(values) >= 2:
                        x = float(values[0])
                        y = float(values[1])
                        speed = float(values[2]) if len(values) > 2 else 0.5
                        
                        # Ensure speed is within valid range
                        speed = max(0.1, min(1.0, speed))
                        
                        points.append(PathDataPoint(x, y, speed, i))
                        
                except (ValueError, IndexError) as e:
                    print(f"Error parsing line {i}: {e}")
                    continue
        
        return points

def get_local_ip():
    """Get the local IP address of the Pi"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\nReceived signal {signum}. Shutting down gracefully...")
    tornado.ioloop.IOLoop.current().stop()

def make_app():
    """Create the Tornado application"""
    static_path = Path(__file__).parent / "static"
    
    return tornado.web.Application([
        (r"/api/upload", CSVUploadHandler),
        (r"/api/save", CSVSaveHandler),
        (r"/api/export", CSVExportHandler),
        (r"/api/shutdown", ShutdownHandler),
        (r"/api/health", HealthHandler),
        (r"/api/files", FileListHandler),
        (r"/api/loadfile", ServerFileHandler),
        (r"/static/(.*)", StaticFileHandler, {"path": str(static_path)}),
        (r"/", MainHandler),
        (r"/(.*)", tornado.web.StaticFileHandler, {"path": str(static_path), "default_filename": "index.html"}),
    ], debug=options.debug)

def main():
    """Main application entry point"""
    tornado.options.parse_command_line()
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start the application
    app = make_app()
    app.listen(options.port, address="0.0.0.0")
    
    ip = get_local_ip()
    print(f"🚀 Donkey Car Path Editor (Tornado) starting...")
    print(f"📱 Access at: http://{ip}:{options.port}")
    print(f"📱 Local: http://localhost:{options.port}")
    print("🛑 Press Ctrl+C or use Exit button to stop")
    print("=" * 60)
    
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")

if __name__ == "__main__":
    main()
    