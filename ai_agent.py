import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

_MODEL = "gemini-2.5-flash"

_SYSTEM_INSTRUCTION = """
You are an elite inbox triage assistant for a UNC Chapel Hill undergraduate student.
Analyze each email's sender and subject, then decide whether it has genuine value.

[MUST KEEP — highest priority, cannot be overridden]
- Sender domain contains @unc.edu or @admissions.unc.edu
- Sender or subject mentions Canvas (course platform)
- Subject or snippet contains any of: CS, Statistics, BME Lab, Research

[HIGH-VALUE → keep]
- Direct human communication (classmates, friends, professors, colleagues)
- Assignment notifications, course reminders, exam schedules, official school notices
- Important bills, bank notices, personal confirmations

[LOW-VALUE → read (archive)]
- LinkedIn or any job-board marketing / job-alert emails
- Auto-generated weekly reports (Grammarly, Google product digests, etc.)
- Newsletters, advertisements, promotional emails
- Welcome emails and platform onboarding messages

[OUTPUT FORMAT]
Return ONLY valid JSON with exactly these two fields, no extra text:
{
  "action": "keep" or "read",
  "summary": "One sentence summarising the email's core content (English)"
}
""".strip()


def analyze_email(sender: str, subject: str, snippet: str) -> dict:
    """
    Call Gemini 2.5 Flash to triage a single email.

    Args:
        sender:  Raw RFC 5322 From header value.
        subject: Email subject line.
        snippet: Short body preview text.

    Returns:
        Dict with 'action' ("keep" or "read") and 'summary' (English, one sentence).
        On any API failure, returns action="keep" to avoid accidentally discarding
        important mail.
    """
    user_content = f"Sender: {sender}\nSubject: {subject}\nSnippet: {snippet}"

    try:
        response = _client.models.generate_content(
            model=_MODEL,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
            ),
        )
        raw = response.text.strip()

        result = json.loads(raw)

        if "action" not in result or "summary" not in result:
            raise ValueError(f"Response JSON missing required fields: {result}")
        if result["action"] not in ("keep", "read"):
            raise ValueError(f"Invalid action value: {result['action']}")

        return result

    except Exception as e:
        print(f"WARNING: AI analysis failed for '{subject}' – defaulting to keep. Error: {e}")
        return {"action": "keep", "summary": "AI analysis failed – kept by default."}


if __name__ == "__main__":
    # Smoke test: one low-value and one high-value email
    test_cases = [
        {
            "sender":  "jobs-noreply@linkedin.com",
            "subject": "10 new jobs recommended for you",
            "snippet": "Based on your profile, we found these top job matches...",
        },
        {
            "sender":  "professor.smith@unc.edu",
            "subject": "Final project submission deadline reminder",
            "snippet": "Please submit your final project by Friday at 11:59 PM on Canvas...",
        },
    ]

    for case in test_cases:
        print(f"\nSubject : {case['subject']}")
        print(f"Sender  : {case['sender']}")
        result = analyze_email(case["sender"], case["subject"], case["snippet"])
        label  = "KEEP" if result["action"] == "keep" else "ARCHIVE"
        print(f"Decision: {label}")
        print(f"Summary : {result['summary']}")
