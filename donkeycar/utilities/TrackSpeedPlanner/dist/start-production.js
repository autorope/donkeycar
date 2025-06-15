import { fileURLToPath } from 'url';
import { dirname } from 'path';

// Fix import.meta.dirname for production builds
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Polyfill import.meta.dirname globally
if (typeof import.meta.dirname === 'undefined') {
  import.meta.dirname = __dirname;
}

// Now import and run the main application
import('./index.js');