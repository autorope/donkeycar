#!/usr/bin/env node

import { build } from 'vite';
import { build as esbuild } from 'esbuild';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import fs from 'fs/promises';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

console.log('🏗️  Building client...');

// Build client with Vite
await build();

console.log('🏗️  Building server...');

// Build server with esbuild and proper ESM handling
await esbuild({
  entryPoints: ['server/index.ts'],
  bundle: true,
  platform: 'node',
  format: 'esm',
  outdir: 'dist',
  external: ['express', 'fs', 'path', 'http', 'url'],
  banner: {
    js: `
import { fileURLToPath } from 'url';
import { dirname } from 'path';
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Polyfill import.meta.dirname for production builds
if (typeof import.meta === 'undefined') {
  global.import = { meta: {} };
}
if (typeof import.meta.dirname === 'undefined') {
  import.meta.dirname = __dirname;
}
`
  }
});

// Copy the public directory to dist if it exists
try {
  await fs.access('dist/public');
  console.log('✅ Client build found in dist/public');
} catch {
  console.log('❌ Client build not found, make sure Vite build succeeded');
}

console.log('✅ Production build complete');
console.log('📁 Built files:');
console.log('   - dist/index.js (server)');
console.log('   - dist/public/ (client)');
console.log('');
console.log('🚀 Start with: NODE_ENV=production node dist/index.js');