"""Bounded, ephemeral answer previews; never credentials, reasoning or stored history."""

import threading
import time

from .assistant_emotions import EXPRESSIONS
from .assistant_sensitive import contains_secret

_lock = threading.RLock()
_active = {}


def _prune():
    current = time.monotonic()
    for key, value in list(_active.items()):
        if current - value["started"] > 90:
            _active.pop(key, None)


def begin(user_id, conversation_id, request_id):
    key = (user_id, conversation_id, request_id)
    value = {"started": time.monotonic(), "text": "", "expression": "explaining"}
    with _lock:
        _prune()
        if len(_active) >= 128:
            return lambda *args: None
        _active[key] = value

    def publish(text, expression):
        if not isinstance(text, str) or len(text) > 4000 or contains_secret(text) or "<" in text:
            return
        with _lock:
            # Cancellation/deletion removes this exact reservation permanently.
            if _active.get(key) is value:
                value.update(
                    text=text,
                    expression=expression if expression in EXPRESSIONS else "explaining",
                )

    return publish


def snapshot(user_id, conversation_id, request_id):
    with _lock:
        _prune()
        value = _active.get((user_id, conversation_id, request_id))
        return {k: value[k] for k in ("text", "expression")} if value else {}


def discard(user_id, conversation_id, request_id=None):
    with _lock:
        for key in list(_active):
            if key[:2] == (user_id, conversation_id) and (
                request_id is None or key[2] == request_id
            ):
                _active.pop(key, None)
