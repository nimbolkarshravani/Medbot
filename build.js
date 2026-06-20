// build.js — injects env vars into the (already pre-compiled) index.html.
// NO external dependencies, NO Babel: this step cannot fail on Vercel.
// index.html is committed fully compiled (JSX -> React.createElement, no Babel CDN).
// To re-generate index.html after editing the JSX source, run: node compile.js

const fs = require('fs');
const path = require('path');

// Load .env file if it exists (local development)
const envPath = path.join(__dirname, '.env');
if (fs.existsSync(envPath)) {
  fs.readFileSync(envPath, 'utf8')
    .split('\n')
    .forEach(line => {
      const [key, ...rest] = line.split('=');
      if (key && rest.length) process.env[key.trim()] = rest.join('=').trim();
    });
}

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || '';

let html = fs.readFileSync('index.html', 'utf8');

function esc(s) { return s.replace(/\\/g, '\\\\').replace(/'/g, "\\'"); }

html = html.replace("const GEMINI_API_KEY = '';", `const GEMINI_API_KEY = '${esc(GEMINI_API_KEY)}';`);

fs.mkdirSync('dist', { recursive: true });
fs.writeFileSync('dist/index.html', html);

console.log(GEMINI_API_KEY
  ? '✓ Injected GEMINI_API_KEY → dist/index.html'
  : '⚠ No GEMINI_API_KEY — user will enter it manually'
);
