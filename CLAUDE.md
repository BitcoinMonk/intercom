# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Intercom is a voice-activated Claude assistant. It uses RealtimeSTT (Whisper) for speech-to-text with optional wake word detection (OpenWakeWord), pipes transcribed speech to `claude -p`, and speaks the response using edge-tts.

## Setup & Running

```bash
# Activate venv and run (preferred)
./run.sh

# Or manually
source venv/bin/activate
python intercom.py

# Flags
python intercom.py --no-wake          # Skip wake word, always listening
python intercom.py --wake-word "alexa"  # Change wake word (alexa, hey mycroft, hey jarvis)
python intercom.py --model base.en    # Whisper model (tiny.en, base.en, small.en)
python intercom.py --sensitivity 0.8  # Wake word sensitivity 0.0-1.0
python intercom.py --no-tts           # Disable TTS (text-only output)
python intercom.py --voice "en-US-AriaNeural"  # Change TTS voice
```

## Dependencies

System: `portaudio` (for PyAudio microphone access), `ffplay` (from ffmpeg, for audio playback)

Python (in venv): `RealtimeSTT`, `edge-tts`, `pyaudio`, `requests`

## Architecture

Single-file app (`intercom.py`). The loop is:

1. **Wake word** (optional) via OpenWakeWord backend → triggers listening
2. **Speech-to-text** via `AudioToTextRecorder` (RealtimeSTT/Whisper)
3. **Claude CLI** via `subprocess.run(["claude", "-p", text])` → gets response
4. **Text-to-speech** via `edge-tts` (Microsoft neural voices) → speaks response
5. Return to step 1
