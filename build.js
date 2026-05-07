const fs = require('fs');

const apiKey = process.env.GEMINI_API_KEY || '';

let html = fs.readFileSync('index.html', 'utf8');
html = html.replace(
  "const GEMINI_API_KEY = '';",
  `const GEMINI_API_KEY = '${apiKey}';`
);

fs.mkdirSync('dist', { recursive: true });
fs.writeFileSync('dist/index.html', html);

console.log(apiKey ? '✓ GEMINI_API_KEY injected into dist/index.html' : '⚠ GEMINI_API_KEY not set — key field will be shown to users');
