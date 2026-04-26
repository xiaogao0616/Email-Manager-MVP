import re
import json
import streamlit as st
from fetch_emails import fetch_latest_emails

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Inbox Zero",
    page_icon="✉️",
    layout="wide",
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_emails() -> list:
    """Load emails.json; return empty list on missing file or parse error."""
    try:
        with open("emails.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        st.error("emails.json is malformed and could not be parsed.")
        return []


def extract_display_name(sender: str, max_len: int = 20) -> str:
    """
    Extract a human-readable name from a raw RFC 5322 sender string.
    Supports 'Name <email>', '"Name" <email>', and bare email addresses.
    Truncates to max_len characters.
    """
    match = re.match(r'^"?([^"<]+)"?\s*<.+>', sender.strip())
    if match:
        name = match.group(1).strip()
    else:
        email_match = re.search(r'[\w.+-]+@', sender)
        name = email_match.group(0).rstrip('@') if email_match else sender

    return name if len(name) <= max_len else name[:max_len] + "…"


def group_by_sender(emails: list) -> dict:
    """Group email list by raw sender string → {sender: [emails]}."""
    groups: dict[str, list] = {}
    for email in emails:
        # Support both English and legacy Chinese keys
        sender = email.get("sender", email.get("发件人", "(unknown)"))
        groups.setdefault(sender, []).append(email)
    return groups


def get_field(email: dict, en_key: str, cn_key: str, default: str = "") -> str:
    """Read a field that may be stored under either English or Chinese key."""
    return email.get(en_key, email.get(cn_key, default))


# ── Session state ─────────────────────────────────────────────────────────────
if "selected_sender" not in st.session_state:
    st.session_state.selected_sender = None

# ── Data ──────────────────────────────────────────────────────────────────────
emails  = load_emails()
grouped = group_by_sender(emails)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Contacts")
    st.caption(f"{len(grouped)} contacts  ·  {len(emails)} emails")
    st.divider()

    if not grouped:
        st.info("No contacts yet — click Refresh Inbox to fetch emails.")
    else:
        for sender in grouped:
            display = extract_display_name(sender)
            count   = len(grouped[sender])
            label   = f"{display}  `{count}`"
            btn_type = "primary" if st.session_state.selected_sender == sender else "secondary"
            if st.sidebar.button(label, key=sender, use_container_width=True, type=btn_type):
                st.session_state.selected_sender = sender
                st.rerun()

    st.divider()

    if st.button("Refresh Inbox", use_container_width=True):
        with st.spinner("Fetching latest emails…"):
            try:
                fetch_latest_emails()
                st.session_state["refresh_ok"] = True
                st.session_state.selected_sender = None
            except Exception as e:
                st.error(f"Fetch failed: {e}")
                st.session_state["refresh_ok"] = False
        st.rerun()

    if st.session_state.pop("refresh_ok", False):
        st.success("Inbox updated!")

# ── Main panel ────────────────────────────────────────────────────────────────
selected = st.session_state.selected_sender

if selected is None:
    st.markdown("<br>" * 6, unsafe_allow_html=True)
    st.markdown(
        "<h2 style='text-align:center;color:#888;'>"
        "Select a contact on the left to start reading.</h2>",
        unsafe_allow_html=True,
    )
else:
    display_name = extract_display_name(selected)
    st.header(f"Conversation with {display_name}")
    st.caption(selected)
    st.divider()

    for mail in grouped.get(selected, []):
        subject    = get_field(mail, "subject",    "主题",   "(no subject)")
        date       = get_field(mail, "raw_date",   "日期",   "")
        snippet    = get_field(mail, "snippet",    "摘要",   "")
        ai_summary = get_field(mail, "ai_summary", "summary", "")
        action     = mail.get("action", "")

        # Email bubble
        with st.chat_message("user"):
            st.markdown(f"**{subject}**")
            if date:
                st.caption(f"{date}")
            if snippet:
                st.markdown(snippet)

        # AI verdict bubble
        with st.chat_message("assistant", avatar="✨"):
            if action == "keep":
                badge = "✅ **AI: Important — kept**"
            elif action == "read":
                badge = "🗑️ **AI: Low value — archived**"
            elif action == "pending":
                badge = "⏳ **AI: Analysis pending…**"
            else:
                badge = "🤖 **AI Summary**"

            st.markdown(badge)
            summary_text = ai_summary if ai_summary else snippet
            if summary_text:
                st.markdown(summary_text)
