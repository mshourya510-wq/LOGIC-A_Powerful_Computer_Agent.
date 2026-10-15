# Import required libraries
from pathlib import Path
from urllib.parse import quote_plus
import re
from AppOpener import close, open as appopen  # Import functions to open and close apps.
from webbrowser import open as webopen  # Import web browser functionality.
from pywhatkit import search, playonyt  # Import functions for Google search and YouTube playback.
from dotenv import dotenv_values  # Import dotenv to manage environment variables.
from bs4 import BeautifulSoup  # Import BeautifulSoup for parsing HTML content.
from rich import print  # Import rich for styled console output.
from groq import Groq  # Import Groq for AI chat functionalities.
import webbrowser  # Import webbrowser for opening URLs.
import subprocess  # Import subprocess for interacting with the system.
import requests  # Import requests for making HTTP requests.
import keyboard  # Import keyboard for keyboard-related actions.
import asyncio  # Import asyncio for asynchronous programming.
import os  # Import os for operating system functionalities.

# Load environment variables from the .env file.
ROOT = Path(__file__).resolve().parent.parent
env_vars = dotenv_values(ROOT / ".env")
GroqAPIKey = env_vars.get("GroqAPIKey")  # Retrieve the Groq API key.
# Groq shut down llama-3.3-70b-versatile on 16 Aug 2026. Set GroqModel in .env to change the model.
GroqModel = env_vars.get("GroqModel") or "openai/gpt-oss-120b"

# Define CSS classes for parsing specific elements in HTML content.
classes = ["zCubwf", "hgKElc", "LTKOO SY7ric", "ZoLCW", "gsrt vk_bk FzvWSb YwPhnf", "pclqee",
           "tw-Data-text tw-text-small tw-ta", "IZ6rdc", "OSUr6d LTKOO", "VLzY6d", "webanswers-webanswers_table__webanswers-table",
           "dDoNo ikb4Bb gsrt", "sXLlae", "LWkfKe", "VQF4g", "w3vBbe", "kno-rdesc", "SPZz6b"]

# Define a user-agent for making web requests.
useragent = 'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'

# Initialize the Groq client using the Groq API key.
client = Groq(api_key=GroqAPIKey)


# Predefined professional responses for user interactions.
professional_responses = [
    "Your satisfaction is my top priority; feel free to reach out if there's anything else I can help you with.",
    "I'm at your service for any additional questions or support you may need—don't hesitate to ask."
]

# List to store chatbot messages.
messages = []

# System message to provide context to the chatbot.
SystemChatBot = [{"role": "system", "content": f"Hello, I am {env_vars.get('Username', 'User')}, You're a content writer. You have to write content like letters, code, applications, essays, notes, songs, poems, and other requested content."}]


# Function to perform a Google search.
def GoogleSearch(Topic):
    search(Topic)  # Use pywhatkit's search function to perform a Google search.
    return True  # Indicate success.


# Function to generate content using AI and save it to a file.
def Content(Topic):

    # Nested function to open a file in Notepad.
    def OpenNotepad(File):
        default_text_editor = "notepad.exe"  # Default text editor.
        subprocess.Popen([default_text_editor, File])  # Open the file in Notepad.

    # Nested function to generate content using the AI chatbot.
    def ContentWriterAI(prompt):
        if not messages:
            messages.append(SystemChatBot[0])
        messages.append({"role": "user", "content": f"{prompt}"})

        completion = client.chat.completions.create(
            model=GroqModel,  # Specify the AI model.
            messages=messages,
            max_tokens=2048,  # Limit the maximum tokens in the response.
            temperature=0.7,  # Adjust response randomness.
            top_p=1,  # Use nucleus sampling for response diversity.
            stream=True,  # Enable streaming response.
            stop=None,  # Allow the model to determine stopping conditions.
            extra_body={"reasoning_effort": "low"} if "gpt-oss" in GroqModel else None
        )

        Answer = ""  # Initialize an empty string for the response.

        # Process streamed response chunks.
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:  # Check for content in the current chunk.
                Answer += chunk.choices[0].delta.content  # Append the content to the answer.

        Answer = Answer.replace("</s>", "")  # Remove unwanted tokens from the response.
        messages.append({"role": "assistant", "content": Answer})  # Add the AI's response to messages.
        return Answer

    Topic: str = Topic.removeprefix("Content ").strip()
    ContentByAI = ContentWriterAI(Topic)  # Generate content using AI.

    # Save generated content under a safely named path inside the project.
    safe_name = re.sub(r"[^\w-]+", "_", Topic.lower(), flags=re.UNICODE).strip("_-") or "content"
    content_path = ROOT / "Data" / f"{safe_name[:100]}.txt"
    content_path.parent.mkdir(parents=True, exist_ok=True)
    content_path.write_text(ContentByAI, encoding="utf-8")
    OpenNotepad(str(content_path))
    return True  # Indicate success.

# Function to search for a topic on YouTube.
def YouTubeSearch(Topic):
    UrlSearch = f"https://www.youtube.com/results?search_query={quote_plus(Topic)}"  # Construct the YouTube search URL.
    webbrowser.open(UrlSearch)  # Open the search in a web browser.
    return True  # Indicate success.


# Function to play a video on YouTube.
def PlayOnYouTube(query):
    playonyt(query)  # Use pywhatkit's playonyt function to play the video.
    return True  # Indicate success.

# Function to open an application or a relevant website.
def OpenApp(app, sess=requests.session()):
    try:
        appopen(app, match_closest=True, output=True, throw_error=True)  # Attempt to open the app.
        return True  # Indicate success.

    except:
        # Nested function to extract links from HTML content.
        def extract_links(html):
            if html is None:
                return []
            soup = BeautifulSoup(html, 'html.parser')  # Parse the HTML content.
            links = soup.find_all('a', {'jsname': 'UWckNb'})  # Find relevant links.
            return [link.get('href') for link in links]  # Return the links.

        # Nested function to perform a google search and retrieve HTML.
        def search_google(query):
            url = f"https://www.google.com/search?q={query}"  # Construct the Google search URL.
            headers = {'User-Agent': useragent}  # Use predefined user-agent.
            response = sess.get(url, headers=headers, timeout=10)  # Perform the GET request.

            if response.status_code == 200:
                return response.text  # Return HTML content.
            else:
                print("Failed to retrieve search results.")  # Print an error message.
                return None

        html = search_google(app)  # Retrieve search result HTML.

        links = extract_links(html)
        if links:
            webopen(links[0])  # Open the first matching result.
            return True
        return False

# Function to close an application.
def CloseApp(app):
    if "chrome" in app:
        pass  # Skip if the app is Chrome.
    else:
        try:
            close(app, match_closest=True, output=True, throw_error=True)  # Attempt to close the app.
            return True  # Indicate success.
        except:
            return False  # Indicate failure.

# Function to execute system-level commands.
def System(command):
    # Nested function to mute the system volume.
    def mute():
        keyboard.press_and_release("volume mute")  # Simulate the mute key press.

    # Nested function to unmute the system volume.
    def unmute():
        keyboard.press_and_release("volume mute")  # Simulate the unmute key press.

    # Nested function to increase the system volume.
    def volume_up():
        keyboard.press_and_release("volume up")  # Simulate the volume up key press.

    # Nested function to decrease the system volume.
    def volume_down():
        keyboard.press_and_release("volume down")  # Simulate the volume down key press.

    # Execute the appropriate command.
    if command == "mute":
        mute()
    elif command == "unmute":
        unmute()
    elif command == "volume up":
        volume_up()
    elif command == "volume down":
        volume_down()

    return True  # Indicate success.


    print(f"Executing system command: {command}")

# Asynchronous function to translate and execute commands.
async def TranslateAndExecute(commands: list[str]):
    funcs = []  # List to store asynchronous tasks.

    for command in commands:

        if command.startswith("open "):  # Handle "open" commands.
            if "open it" in command:  # Ignore "open it" commands.
                pass
            if "open file" == command:  # Ignore "open file" commands.
                pass
            else:
                fun = asyncio.to_thread(OpenApp, command.removeprefix("open "))  # Schedule app opening
                funcs.append(fun)

        elif command.startswith("general "):  # Placeholder for general commands.
            pass

        elif command.startswith("realtime "):  # Placeholder for real-time commands.
            pass

        elif command.startswith("close "):  # Handle "close" commands.
            fun = asyncio.to_thread(CloseApp, command.removeprefix("close "))  # Schedule app closing.
            funcs.append(fun)

        elif command.startswith("play "):  # Handle "play" commands.
            fun = asyncio.to_thread(PlayOnYouTube, command.removeprefix("play "))  # Schedule YouTube playback.
            funcs.append(fun)

        elif command.startswith("content "):  # Handle "content" commands.
            fun = asyncio.to_thread(Content, command.removeprefix("content "))  # Schedule content creation.
            funcs.append(fun)

        elif command.startswith("google search "):  # Handle Google search commands.
            fun = asyncio.to_thread(GoogleSearch, command.removeprefix("google search "))  # Schedule Google search.
            funcs.append(fun)

        elif command.startswith("youtube search "):  # Handle YouTube search commands.
            fun = asyncio.to_thread(YouTubeSearch, command.removeprefix("youtube search "))  # Schedule YouTube search.
            funcs.append(fun)

        elif command.startswith("system "):  # Handle system commands.
            fun = asyncio.to_thread(System, command.removeprefix("system "))  # Schedule system command.
            funcs.append(fun)

        else:
            print(f"No Function Found. For [command]")  # Print an error for unrecognized commands.

    results = await asyncio.gather(*funcs)  # Execute all tasks concurrently.

    for result in results:
        if isinstance(result, str):
            yield result
        else:
            yield result


async def Automation(commands: list[str]):
    results = []
    async for result in TranslateAndExecute(commands):
        results.append(result)
    return results
