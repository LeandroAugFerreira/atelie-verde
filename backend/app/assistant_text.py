"""Correct obvious typing errors in generic terms, never botanical identities."""

import re
from difflib import SequenceMatcher

from .business import normalized

GROUP_WORDS = ("suculenta", "suculentas", "cacto", "cactos")


def understood_text(text):
    def correct(match):
        word = normalized(match.group())
        # An accidental number inserted in a word is common on phone keyboards.
        letters = re.sub(r"\d", "", word)
        if letters in GROUP_WORDS:
            return letters
        # Long generic words tolerate one typo; short names stay untouched.
        candidates = [
            target
            for target in GROUP_WORDS
            if len(target) >= 8
            and word[:3] == target[:3]
            and abs(len(word) - len(target)) <= 1
            and SequenceMatcher(None, word, target).ratio() >= 0.88
        ]
        return (
            max(candidates, key=lambda t: SequenceMatcher(None, word, t).ratio())
            if candidates
            else match.group()
        )

    return re.sub(r"(?<![\w-])[\w]+(?![\w-])", correct, text)
