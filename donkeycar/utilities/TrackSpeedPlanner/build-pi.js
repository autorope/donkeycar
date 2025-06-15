#!/usr/bin/env node
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

console.log('🏗️  Building for Raspberry Pi...');

try {
  // Quick client build for Pi
  console.log('Building client assets...');
  const clientBuildCmd = 'npx vite build --minify=false --sourcemap=false';
  execSync(clientBuildCmd, { stdio: 'pipe', timeout: 60000 });
  
  // Server build with ESM fix
  console.log('Building server with ESM compatibility...');
  const serverBuildCmd = [
    'npx esbuild server/index.ts',
    '--platform=node',
    '--packages=external',
    '--bundle',
    '--format=esm',
    '--outdir=dist',
    '--banner:js="import{fileURLToPath}from\'url\';import{dirname}from\'path\';const __filename=fileURLToPath(import.meta.url);const __dirname=dirname(__filename);if(!import.meta.dirname)import.meta.dirname=__dirname;"'
  ].join(' ');
  
  execSync(serverBuildCmd, { stdio: 'pipe' });
  
  // Verify build
  const serverFile = 'dist/index.js';
  const clientDir = 'dist/public';
  
  if (!fs.existsSync(serverFile)) {
    throw new Error('Server build failed - no index.js found');
  }
  
  if (!fs.existsSync(clientDir)) {
    throw new Error('Client build failed - no public directory found');
  }
  
  console.log('✅ Build completed successfully');
  console.log(`📁 Server: ${serverFile} (${Math.round(fs.statSync(serverFile).size/1024)}KB)`);
  console.log(`📁 Client: ${clientDir}/ (${fs.readdirSync(clientDir).length} files)`);
  
} catch (error) {
  console.error('❌ Build failed:', error.message);
  process.exit(1);
}