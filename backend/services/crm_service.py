from hashlib import sha1


def log_meeting(client, meeting_date, meeting_time, city):
    if not client:
        return {
            "status": "fail",
            "source": "mock-crm",
            "message": "Client name is required for CRM logging.",
        }

    token = f"{client}|{meeting_date}|{meeting_time}|{city}"
    meeting_id = f"CRM-{sha1(token.encode()).hexdigest()[:8].upper()}"

    return {
        "status": "success",
        "source": "mock-crm",
        "meeting_id": meeting_id,
        "client_name": client,
        "scheduled_for": {
            "date": meeting_date,
            "time": meeting_time,
            "city": city,
        },
        "message": f"Meeting logged for {client} on {meeting_date} at {meeting_time} in {city}.",
    }
