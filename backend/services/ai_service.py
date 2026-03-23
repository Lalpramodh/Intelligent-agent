try:
    from ..config import Config
except ImportError:
    from config import Config

try:
    from groq import Groq
except ImportError:
    Groq = None


client = None


def get_client():
    global client

    if client is False:
        return None

    if client is None:
        if not Config.GROQ_API_KEY or Groq is None:
            client = False
            return None

        client = Groq(api_key=Config.GROQ_API_KEY)

    return client

def parse_with_groq(user_input):
    groq_client = get_client()

    if groq_client is None:
        raise RuntimeError("Groq client is not configured")

    prompt = f"""
    You are an AI assistant.

    Extract structured JSON from the user input.

    Rules:
    - intent must be one of: schedule, weather, other
    - Extract date, time, client_name, city
    - If missing, return null
    - Output STRICT JSON only (no explanation)

    Example:
    {{
      "intent": "schedule",
      "date": "tomorrow",
      "time": "4 PM",
      "client_name": "John",
      "city": "Hyderabad"
    }}

    Input:
    {user_input}
    """

    response = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return response.choices[0].message.content
