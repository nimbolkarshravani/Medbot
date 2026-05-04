# MedBot · AI Medical Report Analyzer

MedBot is a privacy-first web app that turns complex medical reports into clear, plain-English summaries. Upload a PDF or TXT report, and MedBot automatically redacts personal information before sending it to Google Gemini for analysis — giving you an easy-to-understand breakdown in seconds.

---

## Features

- **Drag-and-drop upload** — supports PDF and TXT medical reports (up to 20 MB)
- **Automatic PII redaction** — strips names, phone numbers, email addresses, SSNs, MRNs, dates of birth, physical addresses, and facility names before any data leaves your browser
- **Privacy consent flow** — real-time anonymized preview with highlighted redactions; three explicit consent checkboxes before analysis proceeds
- **AI-powered analysis** — powered by Google Gemini 2.5 Flash via the v1beta API
- **Health score** — animated severity ring (1–10) with an overall health label
- **Categorized findings** — color-coded as 🔴 Critical, 🟡 Warning, or 🟢 Normal (up to 6 findings)
- **Top 3 recommended actions** — specific, actionable next steps in plain English
- **Zero backend** — everything runs client-side; no data is stored or transmitted to any server other than Google's Gemini API
- **Single HTML file** — no build tools, no dependencies to install; open directly in any browser

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI framework | React 18 (via CDN) |
| JSX transform | Babel Standalone (via CDN) |
| PDF extraction | PDF.js 3.11 (via CDN) |
| AI analysis | Google Gemini 2.5 Flash (v1beta REST API) |
| Styling | Vanilla CSS — glassmorphism, CSS animations, custom properties |
| Deployment | Static file — Vercel, GitHub Pages, Netlify, or any web server |

---

## Setup

### 1. Get a free Gemini API key

1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click **Create API key**
4. Copy the generated key (starts with `AIza…`)

Google AI Studio offers a free tier with generous usage limits — no credit card required.

### 2. Run the app

No installation needed. Just open `index.html` in your browser:

```bash
# Clone the repo
git clone https://github.com/nimbolkarshravani/Medbot.git
cd Medbot

# Open directly (macOS)
open index.html

# Open directly (Linux)
xdg-open index.html

# Or serve locally (optional)
npx serve .
```

### 3. Deploy to Vercel (recommended)

1. Push the repo to GitHub
2. Go to [vercel.com](https://vercel.com) → **Add New → Project**
3. Import your GitHub repo
4. No framework or build settings needed — Vercel detects it as a static site automatically
5. Click **Deploy**

Your app will be live at a `*.vercel.app` URL instantly.

---

## Usage Guide

1. **Enter your Gemini API key** in the password field at the top of the app. The key stays in your browser and is never stored.
2. **Upload a report** by dragging and dropping a PDF or TXT file onto the upload area, or click to browse.
3. **Review the privacy preview** — a modal will show your report with all detected PII highlighted and redacted. Check the three consent boxes to confirm you understand what's being sent for analysis.
4. **Wait for analysis** — MedBot extracts text, anonymizes it, and sends it to Gemini. This typically takes 5–15 seconds.
5. **Read your results** — you'll see:
   - An overall health score (1–10) with a summary sentence
   - Key findings sorted by severity
   - Three concrete recommended actions
6. Click **Analyze Another** to start over with a new report.

---

## Disclaimer

**MedBot is for educational and informational purposes only.**

The analysis provided by MedBot does not constitute medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional before making any decisions based on your medical reports. Do not disregard professional medical advice or delay seeking it because of information provided by this tool.

MedBot is not a licensed medical device and has not been evaluated by any regulatory authority.
