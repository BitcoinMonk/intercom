#!/usr/bin/env python3
"""
Intercom - Voice-activated Claude assistant
Phase 2: Wake word + real-time voice to Claude CLI
"""

import subprocess
import sys
import argparse
import os

# Suppress ALSA/JACK warnings
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
stderr_backup = None

def suppress_alsa_errors():
    """Suppress ALSA error messages."""
    global stderr_backup
    import ctypes
    try:
        asound = ctypes.cdll.LoadLibrary('libasound.so.2')
        asound.snd_lib_error_set_handler(ctypes.c_void_p(None))
    except:
        pass

def send_to_claude(text: str) -> str:
    """Send text to claude CLI and return response."""
    result = subprocess.run(
        ["claude", "-p", text],
        capture_output=True,
        text=True
    )
    return result.stdout

def on_wakeword():
    """Called when wake word is detected."""
    print("\n✨ Wake word detected! Listening for command...")

def main():
    parser = argparse.ArgumentParser(description="Intercom - Voice-activated Claude")
    parser.add_argument("--no-wake", action="store_true",
                       help="Disable wake word (always listening)")
    parser.add_argument("--wake-word", type=str, default="hey jarvis",
                       help="Wake word to use (default: 'hey jarvis'). Options: 'alexa', 'hey mycroft', 'hey jarvis'")
    parser.add_argument("--model", type=str, default="tiny.en",
                       help="Whisper model: tiny.en, base.en, small.en (default: tiny.en)")
    parser.add_argument("--sensitivity", type=float, default=0.3,
                       help="Wake word sensitivity 0.0-1.0 (default: 0.3)")
    args = parser.parse_args()

    suppress_alsa_errors()

    try:
        from RealtimeSTT import AudioToTextRecorder
    except ImportError:
        print("Missing dependencies. Run: pip install -r requirements.txt")
        sys.exit(1)

    print("=" * 50)
    print("INTERCOM - Voice-activated Claude")
    print("=" * 50)

    use_wakeword = not args.no_wake

    if use_wakeword:
        print(f"Wake word: \"{args.wake_word}\"")
        print(f"Say \"{args.wake_word}\" then speak your command.")
    else:
        print("Wake word: DISABLED (always listening)")
        print("Speak naturally, pause when done.")

    print(f"Model: {args.model}")
    print("Press Ctrl+C to exit.")
    print("=" * 50)
    print()

    # Configure recorder
    recorder_config = {
        "model": args.model,
        "language": "en",
        "silero_sensitivity": 0.4,
        "post_speech_silence_duration": 0.8,
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
        print(f"🔇 Waiting for \"{args.wake_word}\"...")
    else:
        print("🎤 Listening...")

    while True:
        try:
            text = recorder.text()

            if not text or not text.strip():
                if use_wakeword:
                    print(f"\n🔇 Waiting for \"{args.wake_word}\"...")
                continue

            print(f"\n📝 You said: {text}")
            print("\n🤖 Claude is thinking...")

            response = send_to_claude(text)

            print("\n" + "-" * 50)
            print(response)
            print("-" * 50)

            if use_wakeword:
                print(f"\n🔇 Waiting for \"{args.wake_word}\"...")
            else:
                print("\n🎤 Listening...")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break

if __name__ == "__main__":
    main()
