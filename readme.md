# Inbox Zero AI

> AI-native Gmail triage — built for the **Code With Gemini** hackathon.

Inbox Zero connects to your Gmail inbox, runs every unread email through **Gemini 2.5 Flash**, and automatically decides what to keep and what to archive — so you never waste time on newsletters, job spam, or platform notifications again.

## Architecture

```
Gmail API
    └─► fetch_emails.py   fetch & cache unread emails → emails.json
             │
             ├─► monitor.py      AI queue worker (rate-limited to 4 RPM)
             │        └─► ai_agent.py   Gemini 2.5 Flash triage
             │
             └─► api.py          FastAPI REST backend
                      ├─  GET  /api/contacts
                      ├─  GET  /api/messages/{contact_id}
                      ├─  POST /api/actions/mark-read
                      ├─  POST /api/actions/refresh
                      └─  GET  /api/stats
```

The React frontend (generated with Lovable) consumes the FastAPI layer — no direct file I/O from the browser.

## Key Features

- **Gemini-powered triage** — keeps school emails, professor messages, and important notices; archives LinkedIn spam, newsletters, and promotional mail automatically
- **Buffer queue with rate-limiting** — processes one email every 15 s to stay within Gemini's free-tier 5 RPM cap; progress is persisted after every email so nothing is lost on a crash
- **Clean REST API** — FastAPI backend with CORS enabled, ready for any frontend framework
- **Conversational UI** — three-column layout (contacts / thread / AI analysis panel) styled after Spike and Linear

## Tech Stack

| Layer | Technology |
|---|---|
| AI | Google Gemini 2.5 Flash (`google-genai`) |
| Backend API | FastAPI + Uvicorn |
| Email | Gmail API v1, OAuth 2.0 |
| Frontend | React + Tailwind CSS (Lovable) |
| Data store | Local `emails.json` (file-based cache) |

## Quick Start

### 1. Google credentials

Create an OAuth 2.0 Client (Desktop app) in Google Cloud Console, download `credentials.json` to the project root, then run the one-time auth flow:

```bash
python auth.py
```

This generates `token.json`.

### 2. Environment variables

Create a `.env` file:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the backend API

```bash
python api.py
# API docs available at http://localhost:8000/docs
```

### 5. Run the AI queue worker (separate terminal)

```bash
python monitor.py
```

The worker fetches new emails, processes the pending queue through Gemini, and writes results back to `emails.json` in real time.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/contacts` | All unique senders with initials, message count, pending flag |
| GET | `/api/messages/{contact_id}` | All messages from one contact, newest first |
| POST | `/api/actions/mark-read` | Remove Gmail UNREAD label (`{ "message_id": "..." }`) |
| POST | `/api/actions/refresh` | Trigger a live Gmail fetch |
| GET | `/api/stats` | Summary counts (total / pending / kept / cleaned) |

## Triage Rules (System Instruction)

Gemini is instructed to **always keep**:
- Emails from `@unc.edu` / `@admissions.unc.edu`
- Anything mentioning Canvas, CS, Statistics, BME Lab, or Research

And to **archive**:
- LinkedIn job alerts and marketing emails
- Auto-generated weekly digests (Grammarly, Google, etc.)
- Newsletters, promotions, and platform onboarding emails
