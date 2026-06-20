// compile.js — regenerates the committed index.html from the JSX source
// (index.src.html). Run locally after editing JSX:  node compile.js
// Requires devDependencies (@babel/core). NOT used by the Vercel build.

const fs = require('fs');
const babel = require('@babel/core');

let html = fs.readFileSync('index.src.html', 'utf8');

const re = /<script type="text\/babel">([\s\S]*?)<\/script>/;
const m = html.match(re);
if (!m) { console.error('No <script type="text/babel"> block found in index.src.html'); process.exit(1); }

const out = babel.transformSync(m[1], {
  plugins: [['@babel/plugin-transform-react-jsx', { runtime: 'classic' }]],
  filename: 'app.jsx',
});

html = html.replace(m[0], `<script>${out.code}<\/script>`);
html = html.replace(/\s*<script src="https:\/\/unpkg\.com\/@babel\/standalone\/babel\.min\.js"><\/script>/, '');

fs.writeFileSync('index.html', html);
console.log('✓ Compiled index.src.html → index.html (Babel-free)');
