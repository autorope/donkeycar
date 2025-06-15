# Path Data Visualizer & Editor

## Overview

This is a full-stack web application for visualizing and editing donkey car path data. The application allows users to upload CSV files containing path coordinates and speed values, visualize them on an interactive canvas, edit speed values through a control panel, and export modified data back to CSV format.

## System Architecture

The application follows a modern full-stack architecture with a clear separation between client and server:

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Routing**: Wouter (lightweight React router)
- **UI Library**: Radix UI components with Tailwind CSS styling (shadcn/ui)
- **State Management**: React Query (@tanstack/react-query) for server state
- **Styling**: Tailwind CSS with custom CSS variables for theming
- **Build Tool**: Vite for fast development and optimized builds

### Backend Architecture
- **Runtime**: Node.js with Express.js framework
- **Language**: TypeScript with ES modules
- **Database ORM**: Drizzle ORM configured for PostgreSQL
- **Database Provider**: Neon Database (@neondatabase/serverless)
- **Development**: Hot module replacement via Vite middleware

### Data Storage Solutions
- **Primary Database**: PostgreSQL (configured via Drizzle)
- **Development Storage**: In-memory storage implementation for rapid prototyping
- **Schema Management**: Drizzle Kit for migrations and schema management

## Key Components

### Frontend Components
1. **PathEditor** (`/client/src/pages/path-editor.tsx`): Main application page coordinating file upload, canvas display, and speed controls
2. **FileUpload** (`/client/src/components/file-upload.tsx`): Drag-and-drop CSV file upload with validation
3. **PathCanvas** (`/client/src/components/path-canvas.tsx`): Interactive HTML5 canvas for path visualization with point selection
4. **SpeedControls** (`/client/src/components/speed-controls.tsx`): Dynamic speed adjustment interface for each path point

### Backend Components
1. **Storage Interface** (`/server/storage.ts`): Abstracted storage layer with in-memory implementation
2. **Route Registration** (`/server/routes.ts`): Express route configuration (currently minimal)
3. **Vite Integration** (`/server/vite.ts`): Development server setup with HMR support

### Shared Components
1. **Database Schema** (`/shared/schema.ts`): Drizzle ORM schema definitions for users and path points
2. **Type Definitions**: Shared TypeScript interfaces for path data structures

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

### Core Framework Dependencies
- **React Ecosystem**: React, React DOM, React Query for state management
- **UI Components**: Comprehensive Radix UI component library
- **Styling**: Tailwind CSS with class-variance-authority for component variants
- **Database**: Drizzle ORM with Neon serverless PostgreSQL driver
- **Validation**: Zod schema validation with Drizzle integration

### Development Dependencies
- **Build Tools**: Vite with React plugin and TypeScript support
- **Code Quality**: TypeScript compiler with strict configuration
- **Replit Integration**: Custom Vite plugins for Replit environment

### Notable Integrations
- **Wouter**: Lightweight client-side routing
- **React Hook Form**: Form handling with Zod resolvers
- **Date-fns**: Date manipulation utilities
- **Lucide React**: Icon library for UI components

## Deployment Strategy

### Development Environment
- **Platform**: Replit with Node.js 20, Web, and PostgreSQL 16 modules
- **Development Server**: Vite dev server on port 5000 with Express backend
- **Hot Reload**: Automatic reloading for both client and server code
- **Database**: PostgreSQL instance provisioned through Replit

### Production Deployment Options

#### Replit Production
- **Build Process**: 
  1. Vite builds client-side React application to `dist/public`
  2. esbuild bundles server-side Express application to `dist/index.js`
- **Deployment Target**: Autoscale deployment on Replit
- **Port Configuration**: Internal port 5000 mapped to external port 80

#### Raspberry Pi Deployment
- **Supported Platforms**: Raspberry Pi 3B+ or newer recommended
- **Node.js Version**: 18+ required for ARM compatibility
- **Deployment Methods**:
  1. **Direct Node.js**: Using systemd service for auto-start
  2. **Docker**: Containerized deployment with docker-compose
- **Installation**: Automated via `deploy-pi.sh` script
- **Network Access**: Accessible on local network via Pi's IP address
- **Auto-Start**: Systemd service ensures application starts on boot

### Environment Configuration
- **Database URL**: Required environment variable for PostgreSQL connection
- **Session Management**: PostgreSQL-backed sessions with connect-pg-simple
- **Static Assets**: Served through Express with Vite middleware in development
- **Port Configuration**: Configurable via PORT environment variable (default: 5000)
- **Host Binding**: Configurable via HOST environment variable (default: 0.0.0.0)

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
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```