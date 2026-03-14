#!/usr/bin/env python3
"""
Intercom - Voice-activated Claude assistant
Direct API with streaming, conversation memory, and barge-in interrupt.
"""

import subprocess
import sys
import argparse
import os
import tempfile
import asyncio
import signal
import threading
import time

from dotenv import load_dotenv
load_dotenv()

# Suppress ALSA/JACK warnings
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

def suppress_alsa_errors():
    import ctypes
    try:
        asound = ctypes.cdll.LoadLibrary('libasound.so.2')
        asound.snd_lib_error_set_handler(ctypes.c_void_p(None))
    except:
        pass


# --- TTS with interruptible playback ---

_tts_process = None
_tts_lock = threading.Lock()

def stop_speaking():
    """Kill any in-progress TTS playback."""
    global _tts_process
    with _tts_lock:
        if _tts_process and _tts_process.poll() is None:
            _tts_process.kill()
            _tts_process.wait()
            _tts_process = None

def speak(text: str, voice: str):
    """Speak text using edge-tts. Can be interrupted by stop_speaking()."""
    global _tts_process
    import edge_tts

    async def _speak():
        global _tts_process
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(tmp_path)
            with _tts_lock:
                _tts_process = subprocess.Popen(
                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp_path],
                )
            _tts_process.wait()
        finally:
            with _tts_lock:
                _tts_process = None
            try:
                os.unlink(tmp_path)
            except:
                pass

    asyncio.run(_speak())


# --- Claude API ---

def create_client():
    from anthropic import Anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set. Add it to .env")
        sys.exit(1)
    return Anthropic(api_key=api_key)

def send_to_claude(client, messages: list, text: str, system_prompt: str) -> str:
    """Send text to Claude API with streaming. Returns full response."""
    messages.append({"role": "user", "content": text})

    full_response = ""
    with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=system_prompt,
        messages=messages,
    ) as stream:
        for chunk in stream.text_stream:
            print(chunk, end="", flush=True)
            full_response += chunk

    messages.append({"role": "assistant", "content": full_response})

    # Keep conversation history manageable (last 20 exchanges)
    if len(messages) > 40:
        messages[:] = messages[-40:]

    return full_response


# --- Wake word ---

_last_wakeword_time = 0

def on_wakeword():
    global _last_wakeword_time
    now = time.time()
    if now - _last_wakeword_time < 3:
        return
    _last_wakeword_time = now
    stop_speaking()  # Interrupt TTS if speaking
    print("\n✨ Wake word detected! Listening...")


# --- Main ---

SYSTEM_PROMPT = (
    "You are a voice assistant. Keep responses short and conversational — "
    "1-3 sentences unless asked for detail. Be direct and helpful. "
    "Don't use markdown, bullet points, or formatting — you're being read aloud."
)

def main():
    parser = argparse.ArgumentParser(description="Intercom - Voice-activated Claude")
    parser.add_argument("--no-wake", action="store_true",
                       help="Disable wake word (always listening)")
    parser.add_argument("--wake-word", type=str, default="hey jarvis",
                       help="Wake word (default: 'hey jarvis')")
    parser.add_argument("--model", type=str, default="tiny.en",
                       help="Whisper model: tiny.en, base.en, small.en")
    parser.add_argument("--sensitivity", type=float, default=0.2,
                       help="Wake word sensitivity 0.0-1.0")
    parser.add_argument("--pause", type=float, default=1.6,
                       help="Seconds of silence before finalizing speech")
    parser.add_argument("--no-tts", action="store_true",
                       help="Disable text-to-speech")
    parser.add_argument("--voice", type=str, default="en-US-GuyNeural",
                       help="Edge TTS voice")
    args = parser.parse_args()

    suppress_alsa_errors()

    try:
        from RealtimeSTT import AudioToTextRecorder
    except ImportError:
        print("Missing: pip install -r requirements.txt")
        sys.exit(1)

    tts_enabled = False
    if not args.no_tts:
        try:
            import edge_tts
            tts_enabled = True
        except ImportError:
            print("TTS: edge-tts not installed, text-only mode")

    # Init Claude API client
    client = create_client()
    messages = []

    print("=" * 50)
    print("INTERCOM - Voice-activated Claude")
    print("=" * 50)

    use_wakeword = not args.no_wake

    if use_wakeword:
        print(f'Wake word: "{args.wake_word}"')
    else:
        print("Wake word: DISABLED (always listening)")

    print(f"Model: {args.model} | Pause: {args.pause}s")
    print(f"TTS: {args.voice if tts_enabled else 'disabled'}")
    print(f"API: Direct (streaming) | Interrupt: speak to cut off")
    print("Ctrl+C to exit.")
    print("=" * 50)
    print()

    # Configure recorder
    recorder_config = {
        "model": args.model,
        "language": "en",
        "silero_sensitivity": 0.4,
        "post_speech_silence_duration": args.pause,
    }

    if use_wakeword:
        recorder_config.update({
            "wakeword_backend": "oww",
            "wake_words": args.wake_word,
            "wake_words_sensitivity": args.sensitivity,
            "on_wakeword_detected": on_wakeword,
        })

    recorder = AudioToTextRecorder(**recorder_config)

    if use_wakeword:
        print(f'🔇 Waiting for "{args.wake_word}"...')
    else:
        print("🎤 Listening...")

    while True:
        try:
            text = recorder.text()

            if not text or not text.strip():
                if use_wakeword:
                    print(f'\n🔇 Waiting for "{args.wake_word}"...')
                continue

            # Interrupt any current TTS
            stop_speaking()

            print(f"\n📝 You: {text}")
            print("🤖 ", end="", flush=True)

            response = send_to_claude(client, messages, text, SYSTEM_PROMPT)
            print()

            if tts_enabled and response.strip():
                speak(response.strip(), args.voice)

            if use_wakeword:
                print(f'\n🔇 Waiting for "{args.wake_word}"...')
            else:
                print("\n🎤 Listening...")

        except KeyboardInterrupt:
            stop_speaking()
            print("\n\nGoodbye!")
            break

if __name__ == "__main__":
    main()
