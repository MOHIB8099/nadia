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
"""


def delivery_hint(text):
    """Return a modest rate/pitch adjustment; Edge TTS has no true emotion control."""
    if re.search(r"\b(error|failed|sorry|problem|warning|urgent)\b", text, re.I):
        return "-10%", "-2Hz"
    if re.search(r"[!?]", text) and len(text) < 100:
        return "+0%", "+1Hz"
    return "+0%", "+0Hz"


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
