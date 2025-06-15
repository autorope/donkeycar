// ESM build shim for import.meta properties
import { fileURLToPath } from 'url';
import { dirname } from 'path';

global.__filename = fileURLToPath(import.meta.url);
global.__dirname = dirname(__filename);

// Polyfill for import.meta.dirname
if (!import.meta.dirname) {
  import.meta.dirname = __dirname;
}