import json
import re
from datetime import date, datetime, timedelta

try:
    from ..services.ai_service import parse_with_groq
except ImportError:
    from services.ai_service import parse_with_groq


SCHEDULE_KEYWORDS = ("schedule", "book", "arrange", "meeting", "call", "appointment")
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def parse_input(user_input):
    ai_result = _parse_with_ai(user_input)
    rules_result = _parse_with_rules(user_input)

    if ai_result:
        merged = rules_result.copy()
        for key, value in ai_result.items():
            if value not in (None, "", "unknown"):
                merged[key] = value

        if ai_result.get("intent") in {"schedule", "weather", "other"}:
            merged["intent"] = ai_result["intent"]

        merged["extraction_method"] = "groq+rules"
        return merged

    return rules_result


def _parse_with_ai(user_input):
    try:
        response = parse_with_groq(user_input)
        response = response.strip().replace("```json", "").replace("```", "")
        parsed = json.loads(response)
        return _normalize_result(parsed, "groq")
    except Exception:
        return None


def _parse_with_rules(user_input):
    lower_input = user_input.lower()

    return {
        "intent": "schedule" if any(keyword in lower_input for keyword in SCHEDULE_KEYWORDS) else "unknown",
        "date": _extract_date(user_input),
        "time": _extract_time(user_input),
        "client_name": _extract_client_name(user_input),
        "city": _extract_city(user_input),
        "extraction_method": "rules",
    }


def _normalize_result(parsed, method):
    return {
        "intent": (parsed.get("intent") or "unknown").lower(),
        "date": _normalize_date(parsed.get("date")),
        "time": _normalize_time(parsed.get("time")),
        "client_name": _clean_value(parsed.get("client_name")),
        "city": _title_case(parsed.get("city")),
        "extraction_method": method,
    }


def _extract_date(user_input):
    lower_input = user_input.lower()
    today = date.today()

    if "day after tomorrow" in lower_input:
        return (today + timedelta(days=2)).isoformat()

    if "tomorrow" in lower_input:
        return (today + timedelta(days=1)).isoformat()

    if "today" in lower_input:
        return today.isoformat()

    iso_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", user_input)
    if iso_match:
        token = iso_match.group(0)
        try:
            return datetime.strptime(token, "%Y-%m-%d").date().isoformat()
        except ValueError:
            return None

    slash_match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", user_input)
    if slash_match:
        first, second, year = slash_match.groups()
        year = int(year)
        if year < 100:
            year += 2000

        month = int(first)
        day_value = int(second)

        if int(first) > 12:
            day_value = int(first)
            month = int(second)

        try:
            return date(year, month, day_value).isoformat()
        except ValueError:
            return None

    next_weekday_match = re.search(r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", lower_input)
    if next_weekday_match:
        weekday = WEEKDAYS[next_weekday_match.group(1)]
        days_ahead = (weekday - today.weekday()) % 7
        days_ahead = 7 if days_ahead == 0 else days_ahead
        return (today + timedelta(days=days_ahead)).isoformat()

    weekday_match = re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", lower_input)
    if weekday_match:
        weekday = WEEKDAYS[weekday_match.group(1)]
        days_ahead = (weekday - today.weekday()) % 7
        return (today + timedelta(days=days_ahead)).isoformat()

    month_name_match = re.search(
        r"\b([A-Za-z]{3,9}\s+\d{1,2}(?:,\s*\d{4})?|\d{1,2}\s+[A-Za-z]{3,9}(?:\s+\d{4})?)\b",
        user_input,
    )
    if not month_name_match:
        return None

    token = month_name_match.group(0).replace(",", "")
    for fmt in ("%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y", "%B %d", "%b %d", "%d %B", "%d %b"):
        try:
            parsed_date = datetime.strptime(token, fmt)
            if "%Y" not in fmt:
                parsed_date = parsed_date.replace(year=today.year)
            return parsed_date.date().isoformat()
        except ValueError:
            continue

    return None


def _extract_time(user_input):
    am_pm_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", user_input, re.IGNORECASE)
    if am_pm_match:
        hours, minutes, meridiem = am_pm_match.groups()
        minutes = minutes or "00"
        return _normalize_time(f"{hours}:{minutes} {meridiem}")

    twenty_four_match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", user_input)
    if twenty_four_match:
        return _normalize_time(twenty_four_match.group(0))

    return None


def _extract_client_name(user_input):
    match = re.search(
        r"\b(?:with|for)\s+([A-Za-z][A-Za-z0-9&.\-\s]*?)(?=\s+(?:on|at|in|today|tomorrow|next|this)\b|[,.!?]|$)",
        user_input,
        re.IGNORECASE,
    )
    if not match:
        return None

    return _title_case(match.group(1))


def _extract_city(user_input):
    match = re.search(
        r"\bin\s+([A-Za-z][A-Za-z.\-\s]*?)(?=\s+(?:on|at|with|for|today|tomorrow|next|this)\b|[,.!?]|$)",
        user_input,
        re.IGNORECASE,
    )
    if not match:
        return None

    return _title_case(match.group(1))


def _normalize_date(value):
    if value is None:
        return None

    return _extract_date(str(value))


def _normalize_time(value):
    if value is None:
        return None

    token = str(value).strip().lower().replace(".", "")
    token = re.sub(r"(?<=\d)(am|pm)$", r" \1", token)

    for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
        try:
            return datetime.strptime(token, fmt).strftime("%H:%M")
        except ValueError:
            continue

    return None


def _clean_value(value):
    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def _title_case(value):
    cleaned = _clean_value(value)
    return cleaned.title() if cleaned else None
