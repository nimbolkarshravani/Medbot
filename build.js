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

const vars = {
  GEMINI_API_KEY:    process.env.GEMINI_API_KEY    || '',
  SUPABASE_URL:      process.env.SUPABASE_URL      || '',
  SUPABASE_ANON_KEY: process.env.SUPABASE_ANON_KEY || '',
};

let html = fs.readFileSync('index.html', 'utf8');

function esc(s) { return s.replace(/\\/g, '\\\\').replace(/'/g, "\\'"); }

html = html.replace("const GEMINI_API_KEY = '';",    `const GEMINI_API_KEY = '${esc(vars.GEMINI_API_KEY)}';`);
html = html.replace("const SUPABASE_URL = '';",      `const SUPABASE_URL = '${esc(vars.SUPABASE_URL)}';`);
html = html.replace("const SUPABASE_ANON_KEY = '';",  `const SUPABASE_ANON_KEY = '${esc(vars.SUPABASE_ANON_KEY)}';`);

fs.mkdirSync('dist', { recursive: true });
fs.writeFileSync('dist/index.html', html);

const injected = Object.entries(vars).filter(([, v]) => v).map(([k]) => k);
console.log(injected.length
  ? `✓ Injected: ${injected.join(', ')} → dist/index.html`
  : '⚠ No env vars set — app runs in local mode (manual API key, no auth)'
);
