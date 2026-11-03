"""Prevent accidental credentials in chat, evidence caches and rendered sources."""

import re

SECRET = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{17,}|tvly-[A-Za-z0-9_-]{15,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,})"
)


def contains_secret(value):
    return bool(SECRET.search(value)) if isinstance(value, str) else False


def redact(value):
    return SECRET.sub("[credencial removida]", str(value or ""))
