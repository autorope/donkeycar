#!/usr/bin/env node
import { execSync } from 'child_process';
import fs from 'fs';

console.log('🏗️  Building for Raspberry Pi deployment...');

try {
  // Build client with reduced bundle size
  console.log('Building client (lightweight)...');
  execSync('npx vite build --target=es2020', { stdio: 'inherit' });
  
  // Build server with ESM polyfill
  console.log('Building server with ESM fixes...');
  execSync(`npx esbuild server/index.ts --platform=node --packages=external --bundle --format=esm --outdir=dist --banner:js="import{fileURLToPath}from'url';import{dirname}from'path';const __filename=fileURLToPath(import.meta.url);const __dirname=dirname(__filename);if(!import.meta.dirname)import.meta.dirname=__dirname;"`, { stdio: 'inherit' });
  
  // Verify build
  if (fs.existsSync('dist/index.js')) {
    console.log('✅ Build successful');
    console.log('📁 Files ready for deployment:');
    console.log('   - dist/index.js (server)');
    if (fs.existsSync('dist/public')) {
      console.log('   - dist/public/ (client)');
    }
  } else {
    throw new Error('Build failed - no output files found');
  }
} catch (error) {
  console.error('❌ Build failed:', error.message);
  process.exit(1);
}