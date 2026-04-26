import json
import time
from datetime import datetime

from ai_agent import analyze_email
from fetch_emails import fetch_latest_emails, mark_as_read

_EMAILS_FILE     = 'emails.json'
_RATE_LIMIT_SLEEP = 15   # Gemini free tier: 5 RPM → 15 s between calls keeps us at ≤4 RPM
_IDLE_SLEEP       = 30   # seconds to wait when the pending queue is empty


def _now() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _load_emails() -> list:
    """Read emails.json; return empty list if file is missing or malformed."""
    try:
        with open(_EMAILS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_emails(emails: list) -> None:
    """Overwrite emails.json with the given list."""
    with open(_EMAILS_FILE, 'w', encoding='utf-8') as f:
        json.dump(emails, f, ensure_ascii=False, indent=4)


def _update_email_in_place(msg_id: str, action: str, ai_summary: str) -> None:
    """
    Reload the file, patch the target record, and immediately save.

    Writing on every email (rather than batching) means:
      - The frontend sees each decision in real time on next refresh.
      - A crash mid-queue loses at most the *current* email, not the whole run.
    """
    emails = _load_emails()
    for email in emails:
        if email.get('id') == msg_id:
            email['action']     = action
            email['ai_summary'] = ai_summary
            # Also update legacy Chinese key if present, for backward compat
            email['summary']    = ai_summary
            break
    _save_emails(emails)


def start_monitoring() -> None:
    """
    Main monitoring loop:
      1. Pull fresh emails from Gmail.
      2. Build a queue of all 'pending' records.
      3. Process each one with Gemini, persisting results immediately.
      4. If the queue is empty, wait _IDLE_SLEEP seconds then repeat.
    """
    print(f"[{_now()}] Inbox Zero monitor started  "
          f"(model: Gemini 2.5 Flash  |  rate-limit gap: {_RATE_LIMIT_SLEEP}s/email)")
    print("=" * 60)

    while True:
        # ── Step 1: Pull latest emails ────────────────────────────────
        print(f"\n[{_now()}] Fetching latest emails from Gmail...")
        try:
            fetch_latest_emails()
        except Exception as e:
            print(f"[{_now()}] ERROR: Could not fetch emails – {e}  (retrying in {_IDLE_SLEEP}s)")
            time.sleep(_IDLE_SLEEP)
            continue

        # ── Step 2: Build the pending queue ──────────────────────────
        all_emails = _load_emails()
        pending = [
            e for e in all_emails
            if e.get('action') == 'pending'
        ]

        if not pending:
            print(f"[{_now()}] No emails waiting for analysis. "
                  f"Checking again in {_IDLE_SLEEP}s.")
            print("=" * 60)
            time.sleep(_IDLE_SLEEP)
            continue

        print(f"[{_now()}] {len(pending)} email(s) queued for AI analysis.\n")

        # ── Step 3: Process queue with hard rate-limiting ─────────────
        kept = cleaned = 0

        for idx, email in enumerate(pending, start=1):
            # Support both new English keys and legacy Chinese keys
            subject = email.get('subject', email.get('主题',   '(no subject)'))
            sender  = email.get('sender',  email.get('发件人', '(unknown)'))
            snippet = email.get('snippet', email.get('摘要',   ''))
            msg_id  = email.get('id', '')

            print(f"  [{idx}/{len(pending)}]  {subject}  ←  {sender}")

            try:
                result     = analyze_email(sender, subject, snippet)
                action     = result.get('action',  'keep')
                ai_summary = result.get('summary', '')
            except Exception as e:
                print(f"    WARNING: AI analysis failed – defaulting to keep. Error: {e}")
                action, ai_summary = 'keep', 'AI analysis failed – kept by default.'

            # Persist immediately so progress survives crashes and the UI updates live
            _update_email_in_place(msg_id, action, ai_summary)

            if action == 'read':
                if msg_id:
                    try:
                        mark_as_read(msg_id)
                    except Exception as e:
                        print(f"    WARNING: Could not mark as read – {e}")
                print(f"    CLEANED  {ai_summary}")
                cleaned += 1
            else:
                print(f"    KEPT     {ai_summary}")
                kept += 1

            # Rate-limit gate – skip the sleep after the last item
            if idx < len(pending):
                print(f"    (rate-limit pause: {_RATE_LIMIT_SLEEP}s)")
                time.sleep(_RATE_LIMIT_SLEEP)

        print(f"\n[{_now()}] Round complete — kept: {kept}  cleaned: {cleaned}")
        print("=" * 60)


if __name__ == '__main__':
    start_monitoring()
