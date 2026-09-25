# Luna V16 — sci-fi interface and voice controls

Open this extracted folder in VS Code and run `python app_v16.py` using the
same Python environment that ran Luna V15. Required files in this folder:
`app_v16.py`, `voice_v16.py`, `actions_v16.py`, `personality_v16.py`, and
`memory.py`. Keep V15 as a backup. To keep chat history and reminders across
folders, copy your own `luna_memory.db` and `luna_reminders.json` separately.

**Voice button:** `START VOICE` begins hands-free listening. The same button
becomes `STOP VOICE`. While Luna is speaking, that button can stop audio too.

The default voice is Normal speed with the Confident style. The header and
animated core use a custom L crest. The microphone now adapts its detection
level to ambient noise and displays a hint if no voice or no words are found.

For a microphone-only test, run `python mic_check_v16.py` in the terminal,
wait half a second, speak for two seconds, and share the printed levels if
recognition still fails. This tool does not save the recording.

Try these checks in order: say "hello", say "notepad open", and press the
same voice button while Luna is speaking. The Edge TTS engine can vary speed,
pitch and volume but cannot promise a human-identical voice or real emotion.
