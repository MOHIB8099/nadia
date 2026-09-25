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
Use short, warm everyday wording. Occasionally use a brief 'haha' only when the
conversation is already playful; do not force laughter into ordinary answers.
Playful teasing is okay if the user initiated it; never insult or scold them.
Do not write stage directions such as *laughs* or *whispers* for speech output.
For casual chat, prefer one natural thought over a numbered list or canned greeting.
Match the user's energy without pretending to be a human being.
"""


VOICE_STYLES = ("Confident", "Sweet", "Playful", "Calm", "Focused")
INTENSITIES = ("Low", "Medium", "High")


def style_instruction(style, intensity):
    """Instructions for wording; speech delivery is handled independently."""
    if style not in VOICE_STYLES:
        style = "Confident"
    if intensity not in INTENSITIES:
        intensity = "Medium"
    instructions = {
        "Confident": "Sound composed, clear and assured; avoid timid filler words and exaggerated claims.",
        "Sweet": "Sound kind, easygoing and naturally conversational.",
        "Playful": "Use gentle wit when the user is playful; never force a joke.",
        "Calm": "Use reassuring, simple wording and give the user room to think.",
        "Focused": "Be concise and direct, especially for computer commands.",
    }
    return instructions[style] + " Style strength: " + intensity + "."


def delivery_hint(text):
    """Return a modest rate/pitch adjustment; Edge TTS has no true emotion control."""
    if re.search(r"\b(error|failed|sorry|problem|warning|urgent)\b", text, re.I):
        return "-10%", "-2Hz"
    if re.search(r"[!?]", text) and len(text) < 100:
        return "+0%", "+1Hz"
    return "+0%", "+0Hz"


def speech_plan(text, style="Confident", intensity="Medium"):
    """Small speech chunks with modest prosody changes; displayed text is untouched."""
    original = text or ""
    spoken = re.sub(r"[\U0001F300-\U0001FAFF]", "", original).strip()
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

    style = style if style in VOICE_STYLES else "Confident"
    intensity = intensity if intensity in INTENSITIES else "Medium"
    strength = {"Low": 0.55, "Medium": 1.0, "High": 1.4}[intensity]
    playful_text = bool(re.search(r"\b(haha|hehe|funny|mazak)\b|हाहा|হাহা|😄|😂", original, re.I))
    style_rate, style_pitch, style_volume = {
        "Confident": (4, 0, 1),
        "Sweet": (-2, 1, 0),
        "Playful": (2, 2, 0),
        "Calm": (-5, -1, -2),
        "Focused": (2, 0, 0),
    }[style]
    plan = []
    for index, part in enumerate(parts):
        rate, pitch = delivery_hint(part)
        serious = bool(re.search(r"\b(sorry|afsoos|maaf|dukhi|sad|serious|error|failed|urgent)\b|माफ़|दुख|দুঃখ", part, re.I))
        if serious:
            # Serious content always overrides the playful setting.
            rate_delta, pitch_delta, volume_delta = -10, -2, -6
        elif playful_text and style == "Playful":
            rate_delta, pitch_delta, volume_delta = 3, 3, 0
        else:
            rate_delta, pitch_delta, volume_delta = style_rate, style_pitch, style_volume
        rate_value = max(-20, min(12, int(rate.rstrip("%")) + round(rate_delta * strength)))
        pitch_value = max(-5, min(5, int(pitch.rstrip("Hz")) + round(pitch_delta * strength)))
        volume_value = max(-12, min(3, round(volume_delta * strength)))
        rate, pitch, volume = f"{rate_value:+d}%", f"{pitch_value:+d}Hz", f"{volume_value:+d}%"
        pause = 0.0
        if index < len(parts) - 1:
            pause = 0.34 if part.endswith(("...", "…")) else 0.18
            if style == "Calm":
                pause += 0.08
            if style == "Focused":
                pause = max(0.08, pause - 0.08)
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
