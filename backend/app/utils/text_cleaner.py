import re

HINGLISH_CORRECTIONS = {
    "ka ise": "kaise",
    "py thon": "python",
    "vid eo": "video",
    "kya h": "kya hai",
    "ki se": "kise",
    "samaj ah": "samajh a",
    "ho rha": "ho raha"
}

def clean_sentence(text: str) -> str:
    """
    Post-processes the transcribed text to fix broken Hinglish words, 
    merge split words, and improve sentence flow.
    """
    for wrong, right in HINGLISH_CORRECTIONS.items():
        pattern = re.compile(rf'\b{wrong}\b', re.IGNORECASE)
        text = pattern.sub(right, text)
    
    # Remove unnecessary double spaces and fix basic punctuation
    text = " ".join(text.split())
    
    return text

def remove_repetition(text: str) -> str:
    """
    Removes consecutive duplicate words or phrases in a single text string.
    Example: 'hello world hello world' -> 'hello world'
    """
    words = text.split()
    if not words:
        return text
    
    deduped = []
    for word in words:
        if not deduped or word.lower() != deduped[-1].lower():
            deduped.append(word)
            
    return " ".join(deduped)

def clean_hinglish_text(text: str) -> str:
    """
    Master wrapper to apply all text cleaning utilities to a single string.
    """
    text = clean_sentence(text)
    text = remove_repetition(text)
    return text
