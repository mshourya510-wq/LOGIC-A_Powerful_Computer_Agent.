import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from groq import Groq
from json import load, dump
import datetime
from dotenv import dotenv_values
import re
from pathlib import Path

# Load environment variables
ROOT = Path(__file__).resolve().parent.parent
env_vars = dotenv_values(ROOT / ".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
GroqAPIKey = env_vars.get("GroqAPIKey")
# Groq shut down llama-3.3-70b-versatile on 16 Aug 2026. Set GroqModel in .env to change the model.
GroqModel = env_vars.get("GroqModel") or "openai/gpt-oss-120b"

client = Groq(api_key=GroqAPIKey)

System = f"""Hello, I am {Username}, and you are {Assistantname}, 
an advanced AI with real-time data access.
Always answer clearly, directly, and in one to two line.
No disclaimers, no filler sentences.
"""

# Ensure chat log exists
try:
    with open(ROOT / "Data" / "ChatLog.json", "r", encoding="utf-8") as f:
        messages = load(f)
except:
    with open(ROOT / "Data" / "ChatLog.json", "w", encoding="utf-8") as f:
        dump([], f)
    messages = []

def fetch_text(url):
    """Scrape text from a webpage."""
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        text = " ".join(p.get_text() for p in soup.find_all("p"))
        return text[:1500]
    except Exception:
        return ""

def extract_money_values(text):
    """Finds money values like $491 billion in text."""
    pattern = r"\$ ?\d{1,3}(?:[,\.]?\d{3})*(?: ?billion| ?million)?"
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    return matches[0] if matches else None


def get_web_data(query):
    """Improved: Fetches current info, focusing on finance and current year."""
    query = f"{query} current {datetime.datetime.now().year}"
    data = ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        for r in results:
            if "href" in r:
                scraped = fetch_text(r["href"])
                data += scraped
    except Exception as e:
        data = f"[Search error: {e}]"

    money = extract_money_values(data)
    if money:
        data = f"The latest reported value is around {money}.\n" + data
    return data or "[No data found]"


def Information():
    now = datetime.datetime.now()
    return f"Date: {now.strftime('%d %B %Y')} | Time: {now.strftime('%I:%M %p')} | Day: {now.strftime('%A')}"

def clean_answer(answer):
    """Normalize whitespace without dropping later sentences or useful citations."""
    return re.sub(r"[ \t]+", " ", str(answer)).strip()

def handle_local_questions(prompt):
    """Instant answers for local time/date/day."""
    now = datetime.datetime.now()
    lower = re.sub(r"[^a-z0-9']+", " ", prompt.lower()).strip()
    if re.search(r"\b(what time is it|what's the time|what is the time|current time|tell me the time)\b", lower):
        return f"The current time is {now.strftime('%I:%M %p')}."
    elif re.search(r"\b(what's the date|what is the date|today's date|current date|tell me the date)\b", lower):
        return f"Today's date is {now.strftime('%d %B %Y')}."
    elif re.search(r"\b(what day is it|what day is today|what's the day|what is the day|which day is it)\b", lower):
        return f"Today is {now.strftime('%A')}."
    return None

def RealtimeSearchEngine(prompt):
    global messages

    # Instant local responses
    local_response = handle_local_questions(prompt)
    if local_response:
        return local_response

    with open(ROOT / "Data" / "ChatLog.json", "r", encoding="utf-8") as f:
        messages = load(f)

    messages.append({"role": "user", "content": prompt})
    live_data = get_web_data(prompt)

    conversation = [
        {"role": "system", "content": System},
        {"role": "system", "content": Information()},
        {"role": "user", "content": f"Question: {prompt}\n\nWeb data:\n{live_data}"}
    ]

    completion = client.chat.completions.create(
        model=GroqModel,
        messages=conversation,
        temperature=0.3,
        max_tokens=1024,
        top_p=1,
        extra_body={"reasoning_effort": "low"} if "gpt-oss" in GroqModel else None
    )

    answer = (completion.choices[0].message.content or "").strip()
    messages.append({"role": "assistant", "content": answer})

    with open(ROOT / "Data" / "ChatLog.json", "w", encoding="utf-8") as f:
        dump(messages, f, indent=4)

    return clean_answer(answer)

if __name__ == "__main__":
    while True:
        prompt = input("Enter what I have to do, Sir: ")
        print(RealtimeSearchEngine(prompt))
