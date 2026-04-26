"""
Inbox Zero – FastAPI Backend
Exposes a clean REST API over the local emails.json cache so any frontend
(React, Next.js, v0.dev-generated UI, etc.) can consume structured data
without touching the filesystem directly.
"""

import hashlib
import json
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from fetch_emails import fetch_latest_emails, mark_as_read

_EMAILS_FILE = "emails.json"

app = FastAPI(
    title="Inbox Zero API",
    version="1.0.0",
    description="AI-powered Gmail triage backend – Code With Gemini Hackathon",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_emails() -> list:
    try:
        with open(_EMAILS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _contact_id(sender: str) -> str:
    """Stable 12-char hex ID derived from the raw sender string."""
    return hashlib.md5(sender.encode()).hexdigest()[:12]


def _parse_sender(sender: str) -> tuple[str, str]:
    """
    Split a raw RFC 5322 sender string into (display_name, email_address).
    Handles: 'Name <addr>', '"Name" <addr>', and bare email addresses.
    """
    match = re.match(r'^"?([^"<]+)"?\s*<([^>]+)>', sender.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip()
    email_match = re.search(r'[\w.+-]+@[\w.-]+', sender)
    email = email_match.group(0) if email_match else sender
    return email.split("@")[0], email


def _initials(display_name: str) -> str:
    """Generate 2-character initials from a display name."""
    parts = display_name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return display_name[:2].upper() if display_name else "?"


def _to_iso(raw_date: str) -> Optional[str]:
    try:
        return parsedate_to_datetime(raw_date).isoformat()
    except Exception:
        return None


def _normalize(email: dict) -> dict:
    """
    Map legacy Chinese field names to English equivalents so the rest of
    the codebase only deals with one schema regardless of file vintage.
    """
    return {
        "id":         email.get("id", ""),
        "sender":     email.get("sender",  email.get("发件人", "")),
        "subject":    email.get("subject", email.get("主题",   "")),
        "raw_date":   email.get("raw_date",email.get("日期",   "")),
        "snippet":    email.get("snippet", email.get("摘要",   "")),
        "action":     email.get("action",  "pending"),
        "ai_summary": email.get("ai_summary", email.get("summary", "")),
    }


# ── Pydantic response models ──────────────────────────────────────────────────

class ContactOut(BaseModel):
    id: str
    display_name: str
    email_address: str
    initials: str
    message_count: int
    has_pending: bool
    latest_timestamp: Optional[str] = None
    latest_subject: str


class MessageOut(BaseModel):
    id: str
    sender: str
    display_name: str
    initials: str
    subject: str
    snippet: str
    ai_summary: str
    action: str                  # "keep" | "read" | "pending"
    timestamp: Optional[str] = None
    raw_date: str


class MarkReadRequest(BaseModel):
    message_id: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/contacts", response_model=list[ContactOut])
def get_contacts():
    """
    Return all unique senders as contact cards, sorted by most-recent message.
    Each card includes initials (for avatar generation) and a pending flag
    so the frontend can show an unprocessed-email badge.
    """
    emails = [_normalize(e) for e in _load_emails()]

    groups: dict[str, list] = {}
    for email in emails:
        cid = _contact_id(email["sender"])
        groups.setdefault(cid, []).append(email)

    contacts: list[ContactOut] = []
    for cid, msgs in groups.items():
        display_name, email_addr = _parse_sender(msgs[0]["sender"])
        latest_msg = max(msgs, key=lambda m: _to_iso(m["raw_date"]) or "")

        contacts.append(ContactOut(
            id=cid,
            display_name=display_name,
            email_address=email_addr,
            initials=_initials(display_name),
            message_count=len(msgs),
            has_pending=any(m["action"] == "pending" for m in msgs),
            latest_timestamp=_to_iso(latest_msg["raw_date"]),
            latest_subject=latest_msg["subject"],
        ))

    contacts.sort(key=lambda c: c.latest_timestamp or "", reverse=True)
    return contacts


@app.get("/api/messages/{contact_id}", response_model=list[MessageOut])
def get_messages(contact_id: str):
    """
    Return all messages belonging to a specific contact, sorted
    newest-first. contact_id is the 12-char hex from GET /api/contacts.
    """
    emails = [_normalize(e) for e in _load_emails()]
    msgs = [e for e in emails if _contact_id(e["sender"]) == contact_id]

    if not msgs:
        raise HTTPException(status_code=404, detail="Contact not found.")

    out: list[MessageOut] = []
    for m in msgs:
        display_name, _ = _parse_sender(m["sender"])
        out.append(MessageOut(
            id=m["id"],
            sender=m["sender"],
            display_name=display_name,
            initials=_initials(display_name),
            subject=m["subject"],
            snippet=m["snippet"],
            ai_summary=m["ai_summary"],
            action=m["action"],
            timestamp=_to_iso(m["raw_date"]),
            raw_date=m["raw_date"],
        ))

    out.sort(key=lambda m: m.timestamp or "", reverse=True)
    return out


@app.post("/api/actions/mark-read")
def action_mark_read(body: MarkReadRequest):
    """
    Mark a single email as read via the Gmail API (removes the UNREAD label).
    Accepts { "message_id": "<gmail_id>" }.
    """
    try:
        mark_as_read(body.message_id)
        return {"ok": True, "message_id": body.message_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/refresh")
def action_refresh():
    """
    Trigger a live Gmail fetch to pull the latest unread emails into
    emails.json. Returns the new total count.
    """
    try:
        fetch_latest_emails()
        return {"ok": True, "total": len(_load_emails())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
def get_stats():
    """
    Summary statistics for the dashboard header strip:
    total / pending / kept / cleaned / unique senders.
    """
    emails = [_normalize(e) for e in _load_emails()]
    cleaned = sum(1 for e in emails if e["action"] == "read")
    return {
        "total":    len(emails),
        "pending":  sum(1 for e in emails if e["action"] == "pending"),
        "kept":     sum(1 for e in emails if e["action"] == "keep"),
        "cleaned":  cleaned,
        "archived": cleaned,   # alias so frontends using either name both work
        "senders":  len({_contact_id(e["sender"]) for e in emails}),
    }


# ── Dev entry-point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
