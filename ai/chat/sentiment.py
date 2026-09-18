"""sentiment.py — Fast, deterministic sentiment and emotional cue detector for LawAid Legal Chat.

Located at: ai/chat/sentiment.py
"""

from typing import Dict, Any

DISTRESSED_KEYWORDS = [
    "punched", "bleeding", "scared", "terrified", "hurt", "crying", "attacked",
    "beaten", "frightening", "emergency", "desperate", "blood", "pain", "hospital",
    "violence", "assaulted", "injured", "fear", "fearful", "help me", "traumatized"
]

ANGRY_KEYWORDS = [
    "furious", "outraged", "cheated", "corrupt", "demand justice",
    "fraud", "scammed", "looted", "angry", "infuriating", "disgusted", "unfair"
]

CONFUSED_KEYWORDS = [
    "don't know", "what should i do", "confused", "understand", "not sure",
    "where to go", "how do i", "can i file", "rights", "procedure"
]


def detect_sentiment(text: str) -> Dict[str, Any]:
    """
    Detects basic emotional communication tone to adapt conversational empathy in legal chat.
    
    Returns:
        dict: {"tone": str, "empathy_guide": str}
    """
    if not text:
        return {"tone": "neutral", "empathy_guide": "Professional, informative, and clear."}

    t_lower = text.lower()

    for kw in DISTRESSED_KEYWORDS:
        if kw in t_lower:
            return {
                "tone": "distressed",
                "empathy_guide": "Empathic, supportive, and reassuring. Acknowledge the distressing or scary situation gently before explaining legal options."
            }

    for kw in ANGRY_KEYWORDS:
        if kw in t_lower:
            return {
                "tone": "angry",
                "empathy_guide": "Calm, objective, and validating. Acknowledge their concern clearly while maintaining professional legal clarity."
            }

    for kw in CONFUSED_KEYWORDS:
        if kw in t_lower:
            return {
                "tone": "confused",
                "empathy_guide": "Clear, structured, and guiding. Break down procedural steps simply to avoid overwhelming the citizen."
            }

    return {
        "tone": "neutral",
        "empathy_guide": "Professional, polite, clear, and informative."
    }
