"""Luna's response policy and conservative speech delivery hints."""

import re


PERSONALITY = """You are Luna, a friendly, smart Windows assistant with a little wit.
Match the user's language and register, including Roman Hindi/Hinglish and Roman Bengali/Banglish.
If they use Roman script, prefer Roman script. Do not switch scripts unless asked.
For a simple question, answer in one or two short sentences. Explain in detail when asked.
Use light humor only when it fits; never joke about distress, health, money, or errors.
Vary ordinary greetings naturally, but never vary facts or action outcomes for entertainment.
For commands, report the actual outcome briefly. Never claim a task succeeded without evidence.
When recalling a recent action, distinguish what Luna did from what the user did.
Use the actual action replies in conversation history as evidence. Say when you do not know.
Never guess the current time or date; only report a clock result from the action system.
Do not claim to feel emotions. Do not add emojis to every reply.
Use short, warm everyday wording. For playful conversation, a brief natural chuckle
in the actual reply is okay occasionally; do not insert laughter in serious or action replies.
"""


def delivery_hint(text):
    """Return a modest rate/pitch adjustment; Edge TTS has no true emotion control."""
    if re.search(r"\b(error|failed|sorry|problem|warning|urgent)\b", text, re.I):
        return "-10%", "-2Hz"
    if re.search(r"[!?]", text) and len(text) < 100:
        return "+0%", "+1Hz"
    return "+0%", "+0Hz"


def speech_plan(text):
    """Small speech chunks with pauses; keep displayed text unchanged."""
    spoken = re.sub(r"[\U0001F300-\U0001FAFF]", "", (text or "")).strip()
    if not spoken:
        return []

    # Short answers stay in one TTS request to avoid extra network delay.
    if len(spoken) <= 100 and "..." not in spoken and "…" not in spoken:
        parts = [spoken]
    else:
        pieces = [p.strip() for p in re.split(r"(?<=[.!?।])\s+|(?<=…)\s*|(?<=\.\.\.)\s*|\n+", spoken) if p.strip()]
        parts = []
        for piece in pieces:
            if parts and (len(parts) >= 3 or (len(parts[-1]) < 28 and not parts[-1].endswith(("...", "…")))):
                parts[-1] += " " + piece
            else:
                parts.append(piece)
        if not parts:
            parts = [spoken]

    plan = []
    for index, part in enumerate(parts):
        rate, pitch = delivery_hint(part)
        volume = "+0%"
        if re.search(r"\b(sorry|afsoos|maaf|dukhi|sad|serious)\b|माफ़|दुख|দুঃখ", part, re.I):
            rate, pitch, volume = "-12%", "-2Hz", "-6%"
        elif re.search(r"\b(haha|hehe|funny|mazak)\b|हाहा|হাহা|😄|😂", part, re.I):
            rate, pitch = "+3%", "+3Hz"
        pause = 0.0
        if index < len(parts) - 1:
            pause = 0.34 if part.endswith(("...", "…")) else 0.18
        plan.append((part, rate, pitch, volume, pause))
    return plan


def recent_user_recall(question, history):
    """Answer only direct 'what did I just tell you' queries from saved user turns."""
    normalized = re.sub(r"\s+", " ", question.lower()).strip()
    recall = (
        re.search(r"\b(tumko|tumhe|tujhe|aapko)\b.*\b(kya|kiya)\b.*\b(bataya|bola|kaha)\b", normalized)
        or re.search(r"\b(what did i|what have i)\b.*\b(tell|say|ask)\b", normalized)
    )
    if not recall or not re.search(r"\b(abhi|just|last|recently|pichle)\b", normalized):
        return None
    for item in reversed(history):
        if item.get("role") == "user" and item.get("content", "").strip() != question.strip():
            return "Abhi tumne mujhe '" + item["content"].strip() + "' bola tha."
    return "Is chat mein tumhari pichhli baat mujhe nahi mili."
