import json
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Hard cap: fetch at most 100 emails per call to prevent historical data floods
_HARD_LIMIT = 100

# Time window: only retrieve emails from the last N days
_DAYS_WINDOW = 7


def _build_service():
    """Load local token.json and return an authorized Gmail service object."""
    creds = Credentials.from_authorized_user_file('token.json')
    return build('gmail', 'v1', credentials=creds)


def _load_existing_emails() -> dict:
    """
    Read emails.json and return a dict keyed by email ID for O(1) dedup.
    Handles both legacy Chinese-key records and current English-key records.
    Returns an empty dict if the file is missing or malformed.
    """
    try:
        with open('emails.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {item['id']: item for item in data if 'id' in item}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def fetch_latest_emails() -> None:
    """
    Pull unread emails from the last 7 days (max 100, no pagination) and
    merge them into emails.json.

    Dual-limit strategy:
      - Time filter : Gmail query  after:YYYY/MM/DD
      - Count cap   : maxResults=100, no nextPageToken traversal

    Existing records are preserved as-is so AI analysis results are never
    overwritten.  New records are initialised with action='pending' so the
    monitor queue picks them up automatically.
    """
    service = _build_service()

    since_date = (datetime.now() - timedelta(days=_DAYS_WINDOW)).strftime('%Y/%m/%d')
    query = f"is:unread after:{since_date}"

    print(f"Querying Gmail: {query}  (limit {_HARD_LIMIT})")

    results = service.users().messages().list(
        userId='me',
        maxResults=_HARD_LIMIT,
        q=query,
    ).execute()

    messages = results.get('messages', [])

    if not messages:
        print(f"No unread emails found in the last {_DAYS_WINDOW} days.")
        return

    print(f"Found {len(messages)} matching emails. Fetching details...")

    existing = _load_existing_emails()
    new_count = 0

    for msg in messages:
        msg_id = msg['id']

        # Skip already-known emails to preserve any existing AI fields
        if msg_id in existing:
            continue

        txt = service.users().messages().get(userId='me', id=msg_id).execute()

        headers = txt['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(no subject)')
        sender  = next((h['value'] for h in headers if h['name'] == 'From'),    '(unknown sender)')
        date    = next((h['value'] for h in headers if h['name'] == 'Date'),    '(unknown date)')
        snippet = txt.get('snippet', '')

        existing[msg_id] = {
            "id":         msg_id,
            "sender":     sender,
            "subject":    subject,
            "raw_date":   date,
            "snippet":    snippet,
            "action":     "pending",                  # awaiting AI analysis
            "ai_summary": "Waiting for AI analysis…",
        }
        new_count += 1

    merged = list(existing.values())
    with open('emails.json', 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=4)

    print(f"Done: +{new_count} new  /  {len(merged)} total  →  emails.json saved.")


def mark_as_read(message_id: str) -> None:
    """
    Remove the UNREAD label from a Gmail message.

    Args:
        message_id: The Gmail message ID (the 'id' field in emails.json).
    """
    service = _build_service()

    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()

    print(f"Marked as read: {message_id}")


if __name__ == '__main__':
    # Smoke test: fetch recent emails and print the first record
    print(">>> Step 1: Fetching unread emails from the last 7 days (max 100)")
    fetch_latest_emails()

    with open('emails.json', 'r', encoding='utf-8') as f:
        emails = json.load(f)

    if not emails:
        print("No emails found. Exiting.")
    else:
        first = emails[0]
        print(f"\n>>> Step 2: First email record")
        print(f"    Subject : {first.get('subject', first.get('主题', 'N/A'))}")
        print(f"    Sender  : {first.get('sender',  first.get('发件人', 'N/A'))}")
        print(f"    Date    : {first.get('raw_date',first.get('日期', 'N/A'))}")
        print(f"    Status  : {first.get('action', 'N/A')}")

        print(f"\n>>> Step 3: Marking first email as read")
        mark_as_read(first['id'])
