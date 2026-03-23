import requests

try:
    from ..config import Config
except ImportError:
    from config import Config


HIGH_RISK_CONDITIONS = {"rain", "thunderstorm", "storm", "snow"}
CAUTION_CONDITIONS = {"drizzle", "mist", "fog", "haze"}


def get_weather(city):
    if not city:
        return {
            "status": "fail",
            "source": "weather-service",
            "city": None,
            "condition": "Unknown",
            "risk_level": "unknown",
            "advisory": "City is required for weather validation.",
        }

    if not Config.WEATHER_API_KEY:
        return _fallback_weather(city, "WEATHER_API_KEY is not configured")

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={Config.WEATHER_API_KEY}"

    try:
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        payload = res.json()
        condition = payload.get("weather", [{}])[0].get("main", "Unknown")
        temperature = payload.get("main", {}).get("temp")

        return {
            "status": "success",
            "source": "openweather",
            "city": city,
            "condition": condition,
            "risk_level": _risk_level(condition),
            "temperature_c": round(temperature - 273.15, 1) if temperature is not None else None,
            "advisory": _advisory(condition),
        }
    except requests.RequestException as exc:
        return _fallback_weather(city, str(exc))


def _fallback_weather(city, reason):
    return {
        "status": "degraded",
        "source": "weather-fallback",
        "city": city,
        "condition": "Unknown",
        "risk_level": "unknown",
        "temperature_c": None,
        "advisory": "Weather API is unavailable, so the agent continued without a live weather gate.",
        "error": reason,
    }


def _risk_level(condition):
    normalized = (condition or "").lower()

    if normalized in HIGH_RISK_CONDITIONS:
        return "high"

    if normalized in CAUTION_CONDITIONS:
        return "medium"

    return "low"


def _advisory(condition):
    risk_level = _risk_level(condition)

    if risk_level == "high":
        return f"Current weather is {condition}; rescheduling or moving indoors is recommended."

    if risk_level == "medium":
        return f"Current weather is {condition}; confirm travel buffers before finalizing the meeting."

    return f"Current weather is {condition}; no weather-based scheduling block was detected."
