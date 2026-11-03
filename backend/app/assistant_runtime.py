"""Select only a locally authorized ChatGPT profile; never import developer secrets."""

import os

from . import assistant_credentials as vault


def chatgpt_mode():
    return os.getenv("RAFINHA_MODE", "chatgpt") == "chatgpt"


def select_profile(user_id):
    with vault.installation_lock():
        return _select_profile(user_id)


def _select_profile(user_id):
    value = vault.load(user_id)
    if (
        not value
        or value.get("kind") != "chatgpt"
        or "chatgpt.tokens.use.direct" not in value.get("scopes", [])
    ):
        raise ValueError("A conta não autorizou o plano ChatGPT.")
    vault.protected_save(
        "chatgpt-selection", {"user_id": user_id, "generation": value["generation"]}
    )


def selected_profile():
    with vault.installation_lock():
        return _selected_profile()


def _selected_profile():
    selected = vault.protected_read("chatgpt-selection")
    uid = selected.get("user_id")
    if not isinstance(uid, int) or uid <= 0:
        return None
    value = vault.load(uid)
    if (
        not value
        or value.get("kind") != "chatgpt"
        or value.get("generation") != selected.get("generation")
    ):
        return None
    if "chatgpt.tokens.use.direct" not in value.get("scopes", []):
        return None
    return uid, value


def management_profile(user_id):
    selected = selected_profile() if chatgpt_mode() else None
    return selected[0] if selected else user_id


def connection():
    from .assistant_connections import ready

    selected = selected_profile()
    if not selected:
        return None
    value = ready(selected[0])
    return (selected[0], value) if value else None


def unselect(user_id):
    selected = vault.protected_read("chatgpt-selection")
    if selected.get("user_id") == user_id:
        vault.protected_remove("chatgpt-selection")
