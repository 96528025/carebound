"""Extract appointments from email text and build a Google Maps route link.

Two modes, matching the rest of CareBound:
- If ANTHROPIC_API_KEY is set, Claude extracts structured appointments and
  resolves relative dates like "next Tuesday" into real ISO datetimes.
- Otherwise a light regex fallback runs so the demo still works offline.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from urllib.parse import quote_plus


@dataclass
class Appointment:
    title: str
    location: str | None = None
    start: str | None = None  # ISO 8601, e.g. 2026-07-01T15:00:00
    end: str | None = None
    maps_url: str | None = None
    source: str = "regex"

    def to_dict(self) -> dict:
        return asdict(self)


def claude_configured() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def build_maps_url(origin: str | None, destination: str | None) -> str | None:
    """Google Maps directions link. No API key needed; opens in any browser."""
    if not destination:
        return None
    params = ["api=1", f"destination={quote_plus(destination)}"]
    if origin:
        params.append(f"origin={quote_plus(origin)}")
    params.append("travelmode=transit")
    return "https://www.google.com/maps/dir/?" + "&".join(params)


def extract_appointments(email_text: str, origin: str | None = None) -> list[Appointment]:
    """Return appointments found in the email text, each with a maps link."""
    if not email_text or not email_text.strip():
        return []
    appointments: list[Appointment] = []
    if claude_configured():
        try:
            appointments = _extract_with_claude(email_text)
        except Exception:
            appointments = []
    if not appointments:
        appointments = _extract_with_regex(email_text)
    for appt in appointments:
        appt.maps_url = build_maps_url(origin, appt.location)
        if appt.start and not appt.end:
            appt.end = _plus_one_hour(appt.start)
    return appointments


def _extract_with_claude(email_text: str) -> list[Appointment]:
    import anthropic

    client = anthropic.Anthropic()
    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    today = datetime.now().strftime("%Y-%m-%d (%A)")
    prompt = (
        "You extract appointments from an email. "
        f"Today is {today}. Resolve relative dates such as 'next Tuesday' into absolute dates.\n"
        "Return ONLY a JSON array, no prose. Each item must be an object with keys:\n"
        '  "title": short description of the appointment (string)\n'
        '  "location": full street address or place name, or null if none\n'
        '  "start": ISO 8601 local datetime like 2026-07-01T15:00:00, or null\n'
        '  "end": ISO 8601 local datetime, or null\n'
        "If the email has no appointment, return [].\n\n"
        "Email:\n"
        f"{email_text}"
    )
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in message.content if getattr(block, "type", "") == "text")
    data = json.loads(_first_json_array(text))
    results: list[Appointment] = []
    for item in data:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        results.append(
            Appointment(
                title=str(item.get("title")).strip(),
                location=(item.get("location") or None),
                start=(item.get("start") or None),
                end=(item.get("end") or None),
                source="claude",
            )
        )
    return results


def _first_json_array(text: str) -> str:
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return "[]"
    return text[start : end + 1]


def _extract_with_regex(email_text: str) -> list[Appointment]:
    """Best-effort offline fallback. Looks for one appointment in the text."""
    # A full US-style address: "505 Parnassus Ave, San Francisco, CA",
    # optionally with a place name in front ("UCSF Medical Center, 505 ...").
    location = None
    # Street address starting at the house number: "505 Parnassus Ave, San Francisco, CA".
    addr = re.search(
        r"\d{1,6}\s+[A-Za-z0-9.\- ]+?,\s*[A-Za-z .]+?,\s*[A-Z]{2}\b",
        email_text,
    )
    if addr:
        location = addr.group(0).strip().rstrip(".")

    time_match = re.search(r"\b(\d{1,2}(:\d{2})?\s*(?:AM|PM|am|pm))\b", email_text)
    start = _guess_datetime(time_match.group(1), email_text) if time_match else None

    # Prefer the email Subject line as the title, else a keyword phrase.
    title = "Appointment"
    subject = re.search(r"Subject:\s*(.+)", email_text)
    if subject:
        title = subject.group(1).strip()[:80]
    else:
        kw = re.search(r"(appointment[^.\n]*|follow-up[^.\n]*|check-?in[^.\n]*|visit[^.\n]*|session[^.\n]*)", email_text, re.IGNORECASE)
        if kw:
            title = kw.group(1).strip()[:80]

    if not (location or start):
        return []
    return [Appointment(title=title, location=location, start=start, source="regex")]


def _guess_datetime(time_str: str, email_text: str) -> str | None:
    """Very rough: today (or 'tomorrow'/'next <weekday>') + parsed clock time."""
    base = datetime.now().replace(second=0, microsecond=0)
    lower = email_text.lower()
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if "tomorrow" in lower:
        base = base + timedelta(days=1)
    else:
        for i, name in enumerate(weekdays):
            if name in lower:
                ahead = (i - base.weekday()) % 7
                ahead = ahead or 7  # "next <weekday>" -> upcoming, not today
                base = base + timedelta(days=ahead)
                break
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)", time_str)
    if not m:
        return None
    hour = int(m.group(1)) % 12
    if m.group(3).lower() == "pm":
        hour += 12
    minute = int(m.group(2) or 0)
    return base.replace(hour=hour, minute=minute).strftime("%Y-%m-%dT%H:%M:%S")


def _plus_one_hour(start_iso: str) -> str | None:
    try:
        dt = datetime.fromisoformat(start_iso)
    except ValueError:
        return None
    return (dt + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
