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

const apiKey = process.env.GEMINI_API_KEY || '';

let html = fs.readFileSync('index.html', 'utf8');
html = html.replace(
  "const GEMINI_API_KEY = '';",
  `const GEMINI_API_KEY = '${apiKey}';`
);

fs.mkdirSync('dist', { recursive: true });
fs.writeFileSync('dist/index.html', html);

console.log(apiKey
  ? '✓ GEMINI_API_KEY injected into dist/index.html'
  : '⚠ GEMINI_API_KEY not set — key field will be shown to users'
);
