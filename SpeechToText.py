"""Microphone input for Jarvis: records from the microphone and transcribes with Groq Whisper.

No browser is needed. Speech is recorded locally, cut at the first pause, and sent to Groq.
InputLanguage in .env decides the mode:
  * English ("en", "en-IN", "en-US"...)  -> transcription in English.
  * Anything else (for example "hi")      -> speech is translated to English text, so Hindi,
                                             Hinglish and English all work.
"""

from collections import deque
from pathlib import Path
from time import sleep
import io
import sys
import wave

import numpy as np
from dotenv import dotenv_values
from groq import Groq

try:  # Needs PortAudio; the pip wheel for Windows includes it.
    import sounddevice as sd
except (ImportError, OSError):
    sd = None


ROOT = Path(__file__).resolve().parent.parent
FILES = ROOT / "Frontend" / "Files"
MIC_FILE = FILES / "Mic.data"
STATUS_FILE = FILES / "status.data"
ENV = dotenv_values(ROOT / ".env")

SAMPLE_RATE = 16000          # Whisper works on 16 kHz mono audio.
BLOCK = 480                  # 30 ms per read.
END_SILENCE = 0.9            # Seconds of quiet that end a sentence.
MIN_SPEECH = 0.25            # Ignore clicks and bumps shorter than this.
MAX_SECONDS = 20.0           # Hard limit for one spoken request.
CALIBRATION_SECONDS = 0.5    # Room-noise measurement at the start of each listen.
# Whisper sometimes "hears" these in near-silence, so they are ignored.
PHANTOM_PHRASES = {"you", "thank you", "thank you.", "thanks for watching!", "thanks for watching.", "bye.", "."}

TRANSCRIBE_MODEL = ENV.get("GroqSpeechModel") or "whisper-large-v3-turbo"
TRANSLATE_MODEL = "whisper-large-v3"  # The translations endpoint is only available on this model.

_debug = False
_client = None
_last_error = ""


def _write_status(path, value):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(value), encoding="utf-8")
    except OSError:
        pass


def SetAssistantStatus(status):
    _write_status(STATUS_FILE, status)


def SetMicrophoneStatus(status):
    _write_status(MIC_FILE, status)


def GetMicrophoneStatus():
    try:
        return MIC_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "False"


def QueryModifier(query):
    query = (query or "").strip()
    if not query:
        return ""
    if query[-1] not in ".?!":
        query += "."
    return query[0].upper() + query[1:]


def _report(message):
    """Print an error once instead of repeating it every cycle."""
    global _last_error
    if message != _last_error:
        _last_error = message
        print(message)


def _clear_report():
    global _last_error
    _last_error = ""


def _is_english():
    return (ENV.get("InputLanguage") or "en").strip().lower().startswith("en")


def _mic_device():
    """Optional MicDevice in .env: a device number or part of its name. Empty means the Windows default."""
    value = (ENV.get("MicDevice") or "").strip()
    if not value:
        return None
    return int(value) if value.isdigit() else value


def _get_client():
    global _client
    if _client is None:
        key = ENV.get("GroqAPIKey")
        if not key:
            _report("Speech input needs GroqAPIKey in the .env file.")
            return None
        _client = Groq(api_key=key)
    return _client


def _capture_utterance(read_block, keep_listening, threshold=None):
    """Wait for speech, then record until a pause.

    Returns the samples as a float32 array, or None if listening was switched off first.
    """
    block_seconds = BLOCK / SAMPLE_RATE
    calibration_blocks = int(CALIBRATION_SECONDS / block_seconds)
    pre_roll = deque(maxlen=int(0.3 / block_seconds))  # keeps the first syllable
    calibration = []
    recorded = []
    speaking = False
    quiet = speech = total = 0.0

    while keep_listening():
        block = read_block()
        if block is None:
            continue
        level = float(np.sqrt(np.mean(np.square(block))))

        if threshold is None:
            calibration.append(level)
            if len(calibration) >= calibration_blocks:
                ambient = float(np.percentile(calibration, 25))
                threshold = min(0.05, max(0.012, ambient * 3.0))
                if _debug:
                    print(f"[mic] room noise {ambient:.4f}, speech threshold {threshold:.4f}")
            continue

        if not speaking:
            pre_roll.append(block)
            if level > threshold:
                speaking = True
                recorded = list(pre_roll)
                quiet, speech, total = 0.0, block_seconds, block_seconds
            continue

        recorded.append(block)
        total += block_seconds
        if level > threshold:
            speech += block_seconds
            quiet = 0.0
        else:
            quiet += block_seconds
        if quiet >= END_SILENCE or total >= MAX_SECONDS:
            if speech >= MIN_SPEECH:
                return np.concatenate(recorded)
            speaking = False
            recorded = []
            pre_roll.clear()
    return None


def _to_wav(samples):
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm.tobytes())
    return buffer.getvalue()


def _transcribe(client, samples):
    audio = ("speech.wav", _to_wav(samples))
    if _is_english():
        result = client.audio.transcriptions.create(file=audio, model=TRANSCRIBE_MODEL, language="en", temperature=0.0)
    else:
        result = client.audio.translations.create(file=audio, model=TRANSLATE_MODEL, temperature=0.0)
    text = result if isinstance(result, str) else getattr(result, "text", "")
    return (text or "").strip()


def SpeechRecognition(force_listen=False):
    """Listen for one spoken request and return it as English text.

    The Mic.data switch (set by the mic button in the GUI) decides whether Jarvis listens.
    ``force_listen`` is used by the standalone test at the bottom of this file.
    """
    def keep_listening():
        return force_listen or GetMicrophoneStatus().lower() == "true"

    def give_up(message):
        _report(message)
        if not force_listen:
            SetMicrophoneStatus("False")
        SetAssistantStatus("Ready")
        return ""

    if not keep_listening():
        SetAssistantStatus("Ready")
        return ""
    if sd is None:
        return give_up("Speech input needs the sounddevice package. Run: pip install sounddevice numpy")
    client = _get_client()
    if client is None:
        return give_up("Speech input needs GroqAPIKey in the .env file.")

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=BLOCK, device=_mic_device()) as stream:
            def read_block():
                data, _ = stream.read(BLOCK)
                return data[:, 0]
            samples = _capture_utterance(read_block, keep_listening, threshold=_threshold_override())
    except Exception as exc:
        return give_up(f"Speech input could not use the microphone: {exc}")

    if samples is None:
        SetAssistantStatus("Ready")
        return ""

    SetAssistantStatus("Transcribing...")
    try:
        text = _transcribe(client, samples)
    except Exception as exc:
        return give_up(f"Speech recognition failed: {str(exc).splitlines()[0] if str(exc) else type(exc).__name__}")

    if not text or text.lower() in PHANTOM_PHRASES:
        SetAssistantStatus("Listening...")
        return ""
    _clear_report()
    return QueryModifier(text)


def _threshold_override():
    """Optional MicThreshold in .env (for example 0.02) if automatic detection is too strict or too loose."""
    try:
        return float(ENV.get("MicThreshold")) if ENV.get("MicThreshold") else None
    except ValueError:
        return None


if __name__ == "__main__":
    if sd is None:
        sys.exit("The sounddevice package is missing. Run: pip install sounddevice numpy")
    if "--devices" in sys.argv:
        print(sd.query_devices())
        sys.exit(0)
    _debug = True
    SetMicrophoneStatus("True")
    print("Listening... speak, then pause. Press Ctrl+C to stop.")
    try:
        while True:
            recognized = SpeechRecognition(force_listen=True)
            if recognized:
                print(f"Heard: {recognized}")
    except KeyboardInterrupt:
        pass
    finally:
        SetMicrophoneStatus("False")
