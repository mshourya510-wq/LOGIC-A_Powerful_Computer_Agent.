from groq import Groq
from rich import print
from dotenv import dotenv_values
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
env_vars = dotenv_values(ROOT / ".env") or dotenv_values(".env")
GroqAPIKey = env_vars.get("GroqAPIKey")
# Groq shut down llama-3.3-70b-versatile on 16 Aug 2026. Set GroqModel in .env to change the model.
GroqModel = env_vars.get("GroqModel") or "openai/gpt-oss-120b"

if not GroqAPIKey:
    raise ValueError("GroqAPIKey not found in .env file!")

client = Groq(api_key=GroqAPIKey)

funcs = [
    "exit", "general", "realtime", "open", "close", "play",
    "generate image", "system", "content", "google search",
    "youtube search", "reminder", "code", "file", "calculate",
    "weather", "translate", "location", "definition", "quote", "joke",
    "motivation", "music control", "settings", "fun", "identity", "greeting",
    "unknown"
]

preamble = """
You are a very accurate Decision-Making Model, which decides what kind of a query is given to you.
You will decide whether a query is a 'general' query, a 'realtime' query, or is asking to perform any task or automation like 'open facebook, instagram', 'can you write a application and open it in notepad'
*** Do not answer any query, just decide what kind of query is given to you. ***
-> Respond with 'general ( query )' if a query can be answered by a llm model (conversational ai chatbot) and doesn't require any up to date information like if the query is 'who was akbar?' respond with 'general who was akbar?', if the query is 'how can i study more effectively?' respond with 'general how can i study more effectively?', if the query is 'can you help me with this math problem?' respond with 'general can you help me with this math problem?', if the query is 'Thanks, i really liked it.' respond with 'general thanks, i really liked it.' , if the query is 'what is python programming language?' respond with 'general what is python programming language?', etc. Respond with 'general (query)' if a query doesn't have a proper noun or is incomplete like if the query is 'who is he?' respond with 'general who is he?', if the query is 'what's his networth?' respond with 'general what's his networth?', if the query is 'tell me more about him.' respond with 'general tell me more about him.', and so on even if it require up-to-date information to answer. Respond with 'general (query)' if the query is asking about time, day, date, month, year, etc like if the query is 'what's the time?' respond with 'general what's the time?'.
-> Respond with 'realtime ( query )' if a query can not be answered by a llm model (because they don't have realtime data) and requires up to date information like if the query is 'who is indian prime minister' respond with 'realtime who is indian prime minister', if the query is 'tell me about facebook's recent update.' respond with 'realtime tell me about facebook's recent update.', if the query is 'tell me news about coronavirus.' respond with 'realtime tell me news about coronavirus.', etc and if the query is asking about any individual or thing like if the query is 'who is akshay kumar' respond with 'realtime who is akshay kumar', if the query is 'what is today's news?' respond with 'realtime what is today's news?', if the query is 'what is today's headline?' respond with 'realtime what is today's headline?', etc.
-> Respond with 'open (application name or website name)' if a query is asking to open any application like 'open facebook', 'open telegram', etc. but if the query is asking to open multiple applications, respond with 'open 1st application name, open 2nd application name' and so on.
-> Respond with 'close (application name)' if a query is asking to close any application like 'close notepad', 'close facebook', etc. but if the query is asking to close multiple applications or websites, respond with 'close 1st application name, close 2nd application name' and so on.
-> Respond with 'play (song name)' if a query is asking to play any song like 'play afsanay by ys', 'play let her go', etc. but if the query is asking to play multiple songs, respond with 'play 1st song name, play 2nd song name' and so on.
-> Respond with 'generate image (image prompt)' if a query is requesting to generate a image with given prompt like 'generate image of a lion', 'generate image of a cat', etc. but if the query is asking to generate multiple images, respond with 'generate image 1st image prompt, generate image 2nd image prompt' and so on.
-> Respond with 'reminder (datetime with message)' if a query is requesting to set a reminder like 'set a reminder at 9:00pm on 25th june for my business meeting.' respond with 'reminder 9:00pm 25th june business meeting'.
-> Respond with 'system (task name)' if a query is asking to mute, unmute, volume up, volume down , etc. but if the query is asking to do multiple tasks, respond with 'system 1st task, system 2nd task', etc.
-> Respond with 'content (topic)' if a query is asking to write any type of content like application, code, emails or anything else about a specific topic but if the query is asking to write multiple types of content, respond with 'content 1st topic, content 2nd topic' and so on.
-> Respond with 'google search (topic)' if a query is asking to search a specific topic on google but if the query is asking to search multiple topics on google, respond with 'google search 1st topic, google search 2nd topic' and so on.
-> Respond with 'youtube search (topic)' if a query is asking to search a specific topic on youtube but if the query is asking to search multiple topics on youtube, respond with 'youtube search 1st topic, youtube search 2nd topic' and so on.
*** If the query contains both realtime and general parts (e.g., "who is Virat Kohli and what is his net worth?"), respond with both classifications separated by commas like 'realtime who is virat kohli, general what is his net worth?'. ***
*** Be extremely consistent in format — always respond with lowercase, no punctuation at the end, and never explain your reasoning. Only output the final classifications. ***
*** Never respond with additional text like “Sure,” “Okay,” or “Heres your answer.” Only give the classification output as specified. ***
*** If the query is asking to perform multiple tasks like 'open facebook, telegram and close whatsapp' respond with 'open facebook, open telegram, close whatsapp' ***
*** If the user is saying goodbye or wants to end the conversation like 'bye jarvis.','close yourself jarvis.' respond with 'exit'.***
*** Respond with 'general (query)' if you can't decide the kind of query or if a query is asking to perform a task which is not mentioned above. ***
"""

ChatHistory = [
    {"role": "user", "content": "how are you?"},
    {"role": "assistant", "content": "general how are you?"},
]


def FirstLayerDMM(prompt: str = "test", _retries: int = 2):
    completion = client.chat.completions.create(
        model=GroqModel,
        messages=[{"role": "system", "content": preamble}] + ChatHistory + [{"role": "user", "content": f"{prompt}"}],
        temperature=0,
        max_tokens=512,
        extra_body={"reasoning_effort": "low"} if "gpt-oss" in GroqModel else None
    )

    response = (completion.choices[0].message.content or "").replace("\n", "")
    response = [i.strip() for i in response.split(",")]
    temp = []

    for task in response:
        for func in funcs:
            if task.startswith(func):
                temp.append(task)

    # If the model returned nothing usable, retry, then fall back to a general chat so Jarvis always answers.
    if not temp or "(query)" in temp:
        if _retries > 0:
            return FirstLayerDMM(prompt=prompt, _retries=_retries - 1)
        return [f"general {prompt}"]
    return temp


if __name__ == "__main__":
    while True:
        print(FirstLayerDMM(input(">>> ")))
