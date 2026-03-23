from datetime import datetime, timedelta


BUSY_SLOTS = {"15:00", "17:00"}
WORKING_HOURS = set(range(9, 18))


def check_availability(meeting_date, meeting_time):
    if not meeting_date or not meeting_time:
        return {
            "status": "fail",
            "source": "mock-calendar",
            "available": False,
            "message": "Date and time are required for the calendar check.",
            "requested_slot": {
                "date": meeting_date,
                "time": meeting_time,
                "display": _format_slot(meeting_date, meeting_time),
            },
            "alternatives": [],
            "next_available": None,
        }

    requested_hour = int(meeting_time.split(":")[0])
    alternatives = _build_alternatives(meeting_date, meeting_time)

    if requested_hour not in WORKING_HOURS:
        return {
            "status": "fail",
            "source": "mock-calendar",
            "available": False,
            "message": "The requested slot is outside business hours (09:00 AM to 05:00 PM).",
            "requested_slot": {
                "date": meeting_date,
                "time": meeting_time,
                "display": _format_slot(meeting_date, meeting_time),
            },
            "alternatives": alternatives,
            "next_available": alternatives[0] if alternatives else None,
        }

    is_available = meeting_time not in BUSY_SLOTS

    return {
        "status": "success",
        "source": "mock-calendar",
        "available": is_available,
        "message": (
            "The requested calendar slot is available."
            if is_available
            else f"The requested slot {_format_time(meeting_time)} is already booked."
        ),
        "requested_slot": {
            "date": meeting_date,
            "time": meeting_time,
            "display": _format_slot(meeting_date, meeting_time),
        },
        "busy_slots": [_format_time(slot) for slot in sorted(BUSY_SLOTS)],
        "alternatives": alternatives,
        "next_available": alternatives[0] if alternatives else None,
    }


def _build_alternatives(meeting_date, meeting_time):
    try:
        base_slot = datetime.strptime(f"{meeting_date} {meeting_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        return []

    alternatives = []
    cursor = base_slot + timedelta(hours=1)

    while len(alternatives) < 3:
        candidate_time = cursor.strftime("%H:%M")
        if cursor.hour in WORKING_HOURS and candidate_time not in BUSY_SLOTS:
            alternatives.append({
                "date": cursor.strftime("%Y-%m-%d"),
                "time": candidate_time,
                "display": _format_slot(cursor.strftime("%Y-%m-%d"), candidate_time),
            })
        cursor += timedelta(hours=1)

    return alternatives


def _format_time(meeting_time):
    return datetime.strptime(meeting_time, "%H:%M").strftime("%I:%M %p")


def _format_slot(meeting_date, meeting_time):
    if not meeting_date or not meeting_time:
        return "Unavailable"

    slot = datetime.strptime(f"{meeting_date} {meeting_time}", "%Y-%m-%d %H:%M")
    return slot.strftime("%d %b %Y, %I:%M %p")
