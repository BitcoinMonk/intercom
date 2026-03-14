#!/usr/bin/env python3
"""
Voice Input - Speech-to-keyboard bridge.
Transcribes speech and types it into the focused window via wtype.
Use with Claude Code, terminal, or any app.
"""

import subprocess
import sys
import argparse
import os
import time

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

def suppress_alsa_errors():
    import ctypes
    try:
        asound = ctypes.cdll.LoadLibrary('libasound.so.2')
        asound.snd_lib_error_set_handler(ctypes.c_void_p(None))
    except:
        pass

VOICE_FIFO = "/tmp/voice-input-pipe"

def type_text(text, press_enter=True):
    """Write text to named pipe for Claude Code to read."""
    with open(VOICE_FIFO, "a") as f:
        f.write(text.strip() + "\n")

_last_wakeword_time = 0

def on_wakeword():
    global _last_wakeword_time
    now = time.time()
    if now - _last_wakeword_time < 3:
        return
    _last_wakeword_time = now
    print("\n✨ Wake word detected! Listening...")

def main():
    parser = argparse.ArgumentParser(description="Voice Input - STT to keyboard")
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
    parser.add_argument("--no-enter", action="store_true",
                       help="Don't press enter after typing")
    parser.add_argument("--delay", type=float, default=0.0,
                       help="Seconds to wait before typing (to switch windows)")
    args = parser.parse_args()

    suppress_alsa_errors()

    # Clear voice input file
    open(VOICE_FIFO, "w").close()

    try:
        from RealtimeSTT import AudioToTextRecorder
    except ImportError:
        print("Missing: pip install -r requirements.txt")
        sys.exit(1)

    print("=" * 50)
    print("VOICE INPUT - Speech to keyboard")
    print("=" * 50)

    use_wakeword = not args.no_wake

    if use_wakeword:
        print(f'Wake word: "{args.wake_word}"')
    else:
        print("Always listening")

    print(f"Model: {args.model} | Pause: {args.pause}s")
    print(f"Auto-enter: {'no' if args.no_enter else 'yes'}")
    print("Speak → text is typed into focused window")
    print("Ctrl+C to exit.")
    print("=" * 50)
    print()

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

            print(f"\n📝 Heard: {text}")

            if args.delay > 0:
                time.sleep(args.delay)

            type_text(text.strip(), press_enter=not args.no_enter)
            print("⌨️  Typed!")

            if use_wakeword:
                print(f'\n🔇 Waiting for "{args.wake_word}"...')
            else:
                print("\n🎤 Listening...")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break

if __name__ == "__main__":
    main()
