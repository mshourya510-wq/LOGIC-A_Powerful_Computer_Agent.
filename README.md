# Logic: Local Computer Agent

Logic is a Python desktop assistant that brings voice and text interaction, conversational AI, and everyday computer tasks together in a graphical interface.

## Features

- Interact through the desktop GUI using typed prompts or voice input.
- Get conversational responses and web search results.
- Ask Logic to open or close applications, play media, and perform other supported desktop tasks.
- Generate images through the configured image service.
- Keep conversation history between sessions.

## Getting started

1. Install Python and the dependencies listed in Requirements.txt.
2. Create a local .env file for the API credentials and settings required by the integrations you want to use. Keep this file private and never commit it.
3. Start the application with: python Main.py

Some features need their corresponding API credentials and a working microphone, speakers, and internet connection.

## Project layout

- Main.py — application entry point and request routing
- Backend/ — chat, search, speech, image generation, and automation modules
- Frontend/ — graphical interface and visual assets
- Data/ — local application data and conversation history

## Configuration and privacy

Logic can interact with desktop applications and stores conversation history locally. Review your configuration and the files in Data/ before sharing a copy of your project. Never publish API keys or personal conversation data.
