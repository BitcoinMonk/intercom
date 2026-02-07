# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Intercom is a voice-activated Claude assistant. It uses RealtimeSTT (Whisper) for speech-to-text with optional wake word detection (OpenWakeWord), then pipes transcribed speech to `claude -p` and prints the response.

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
```

## Dependencies

System: `portaudio` (for PyAudio microphone access)

Python (in venv): `RealtimeSTT`, `pyaudio`, `requests`

## Architecture

Single-file app (`intercom.py`). The loop is:

1. **Wake word** (optional) via OpenWakeWord backend → triggers listening
2. **Speech-to-text** via `AudioToTextRecorder` (RealtimeSTT/Whisper)
3. **Claude CLI** via `subprocess.run(["claude", "-p", text])` → prints response
4. Return to step 1

No TTS yet — responses are text-only in the terminal.
