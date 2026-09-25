# Luna V15 — voice and conversation

Run `app_v15.py` from this folder in the same Python environment used for V14.
The required files are `app_v15.py`, `voice_v15.py`, `actions_v15.py`,
`personality_v15.py`, and `memory.py`. Luna still needs your installed
Python packages, local Ollama server and `llama3` model, microphone, speakers,
and internet for Edge TTS.

In VS Code: open the extracted folder, open Terminal, run `python app_v15.py`.
Keep a backup of `luna_memory.db` and `luna_reminders.json` when changing folders
if you want to keep chat history and reminders. Do not delete the V14 files.

## Voice controls

- **Voice profile:** Hindi, English or Bengali voice; male/female choices.
- **Speech speed:** Gentle (default), Normal, Fast, Very fast.
- **Voice style:** Sweet (default), Playful, Calm, Focused.
- **Style strength:** Low, Medium, High.
- **STOP SPEAKING:** interrupts the current audio. **STOP VOICE** exits hands-free listening.

Luna keeps short answers as a single speech request and uses at most three
speech pieces for longer answers. It pauses briefly between pieces, speaks
serious replies more softly, and uses a slight brighter tone for playful replies
when the actual answer is playful. The reply text stays visible in the chat.
Luna does not add a laugh sound to every answer.

## Practical test

1. Try a casual question in Hindi/Hinglish, then select Calm and repeat.
2. Select Playful and ask a light, funny question.
3. Ask for a longer explanation and listen for small pauses.
4. Press STOP SPEAKING while Luna is talking.

This version uses Edge TTS rate, pitch and volume. It cannot promise an
indistinguishable human voice, true whispering, genuine laughter, or full
emotion acting. Generating speech can require internet and take time.
