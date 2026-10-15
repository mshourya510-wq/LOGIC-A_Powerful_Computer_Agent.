"""Text-to-speech playback with bounded failures, an offline fallback and safe concurrent calls."""
from dotenv import dotenv_values
from pathlib import Path
from threading import Lock
from time import monotonic
import asyncio
import re
import subprocess

import edge_tts
import pygame

ROOT = Path(__file__).resolve().parent.parent
env_vars = dotenv_values(ROOT / ".env")
AssistantVoice = (env_vars.get("AssistantVoice") or "en-CA-LiamNeural").strip()
AUDIO_PATH = ROOT / "Data" / "speech.mp3"
ONLINE_RETRY_SECONDS = 120  # After the online voice fails, use the Windows voice for this long.
_playback_lock = Lock()
_online_retry_at = 0.0


async def TextToAudioFile(text) -> None:
    AUDIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(str(text), AssistantVoice, pitch="+5Hz", rate="+13%")
    await communicate.save(str(AUDIO_PATH))


def _short(exc):
    """Error text without the long service URL (it contains a key and a connection id)."""
    return str(exc).split(", url=")[0]


def _play_audio_file(func):
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.music.load(str(AUDIO_PATH))
    pygame.mixer.music.play()
    clock = pygame.time.Clock()
    while pygame.mixer.music.get_busy():
        if func() is False:
            pygame.mixer.music.stop()
            break
        clock.tick(30)
    return True


def _speak_offline(text):
    """Speak with the voice built into Windows (no internet, no extra install)."""
    script = (
        "[Console]::InputEncoding=[Text.Encoding]::UTF8;"
        "Add-Type -AssemblyName System.Speech;"
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
        "$s.Speak([Console]::In.ReadToEnd())"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            input=text, text=True, encoding="utf-8", timeout=180, check=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True
    except Exception as exc:
        print(f"Offline voice failed: {_short(exc)}")
        return False


def TTS(text, func=lambda r=None: True):
    """Synthesize and play one utterance. Return False instead of retrying forever."""
    global _online_retry_at
    text = str(text).strip()
    if not text:
        return True
    with _playback_lock:
        try:
            if monotonic() >= _online_retry_at:
                try:
                    asyncio.run(TextToAudioFile(text))
                except Exception as exc:
                    _online_retry_at = monotonic() + ONLINE_RETRY_SECONDS
                    print(f"Online voice unavailable ({_short(exc)}). Using the Windows voice for a while.")
                else:
                    return _play_audio_file(func)
            return _speak_offline(text)
        except Exception as exc:
            print(f"Text-to-speech failed: {_short(exc)}")
            return False
        finally:
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    pygame.mixer.quit()
            except pygame.error:
                pass
            try:
                func(False)
            except Exception:
                pass


def TextToSpeech(text, func=lambda r=None: True):
    """Speak a concise preview for long replies; the full answer remains in chat."""
    text = re.sub(r"\s+", " ", str(text)).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(text) > 250 or len(sentences) > 4:
        preview = " ".join(sentences[:2]).strip()
        if len(preview) > 320:
            preview = preview[:317].rsplit(" ", 1)[0] + "…"
        spoken = f"{preview} The complete answer is in the chat window."
    else:
        spoken = text
    return TTS(spoken, func)


if __name__ == "__main__":
    while True:
        TextToSpeech(input("Enter the text: "))
