# tones.py

TONE_TEMPLATES = {
    "formal": "{sentence}.",
    "cheerful": "{sentence}",
    "sad": "{sentence}...",
    "neutral": "{sentence}."
}

def apply_tone(text, tone):
    template = TONE_TEMPLATES.get(tone, TONE_TEMPLATES["neutral"])
    return template.format(sentence=text)
