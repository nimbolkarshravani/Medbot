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

