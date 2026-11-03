"""Administrator-owned BYOK, explicit paid authorization and atomic usage limits."""

import os
import re
import sys
import time
import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from . import assistant_credentials as vault


class ResearchSettings(BaseModel):
    model_config = {"extra": "forbid"}
    mode: Literal["tavily_first", "free_only", "on_request", "important_double"] = "tavily_first"
    paid_search_enabled: bool = False
    search_enabled: bool = True
    images: bool = True
    response_timeout: Literal[10, 30] = 30
    tavily_daily_limit: int = Field(default=50, ge=0, le=1000)
    tavily_monthly_limit: int = Field(default=1000, ge=0, le=10000)
    paid_daily_limit: int = Field(default=10, ge=0, le=1000)
    paid_monthly_limit: int = Field(default=100, ge=0, le=10000)
    openai_model: str = Field(default="", max_length=100)


class SettingsPatch(BaseModel):
    model_config = {"extra": "forbid"}
    mode: Literal["tavily_first", "free_only", "on_request", "important_double"] | None = None
    paid_search_enabled: bool | None = None
    search_enabled: bool | None = None
    images: bool | None = None
    response_timeout: Literal[10, 30] | None = None
    tavily_daily_limit: int | None = Field(default=None, ge=0, le=1000)
    tavily_monthly_limit: int | None = Field(default=None, ge=0, le=10000)
    paid_daily_limit: int | None = Field(default=None, ge=0, le=1000)
    paid_monthly_limit: int | None = Field(default=None, ge=0, le=10000)
    openai_model: str | None = Field(default=None, max_length=100)


def settings():
    return ResearchSettings.model_validate(
        vault.protected_read("installation-ai-settings")
    ).model_dump()


def credential(provider):
    if provider not in {"tavily", "openai"}:
        raise ValueError("Unknown provider")
    stored = vault.protected_read("installation-" + provider)
    if stored.get("key") and stored.get("verified"):
        return stored
    if vault.protected_read("installation-credential-blocks").get(provider):
        return None
    # Development fallback is opt-in and is never active in an executable.
    if (
        not getattr(sys, "frozen", False)
        and os.getenv("APP_ENV", "development") == "development"
        and os.getenv("RAFINHA_ALLOW_DEV_API_KEYS", "false").lower() == "true"
    ):
        key = os.getenv(provider.upper() + "_API_KEY", "").strip()
        if key:
            return {
                "key": key,
                "verified": False,
                "source": "development_environment",
                "generation": "env",
            }
    return None


def save_credential(provider, key, details):
    with vault.installation_lock():
        blocks = vault.protected_read("installation-credential-blocks")
        blocks[provider] = False
        vault.protected_save("installation-credential-blocks", blocks)
        vault.protected_save(
            "installation-" + provider,
            {
                **details,
                "key": key,
                "verified": True,
                "generation": str(uuid.uuid4()),
                "source": "os_vault",
                "verified_at": time.time(),
            },
        )
        if provider == "openai":
            current = settings()
            current["paid_search_enabled"] = False
            choices = details.get("models", [])
            current["openai_model"] = next(
                (m["id"] for m in choices if m["id"].endswith("-sol")),
                choices[0]["id"] if choices else "",
            )
            vault.protected_save("installation-ai-settings", current)


def remove_credential(provider):
    with vault.installation_lock():
        vault.protected_remove("installation-" + provider)
        blocks = vault.protected_read("installation-credential-blocks")
        blocks[provider] = True
        vault.protected_save("installation-credential-blocks", blocks)
        if provider == "openai":
            current = settings()
            current.update(paid_search_enabled=False, openai_model="")
            vault.protected_save("installation-ai-settings", current)


def key_hint(value):
    key = (value or {}).get("key", "")
    return "••••••••••••" + key[-3:] if key else ""


def clock_keys():
    day = datetime.now(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    return day, day[:7]


def usage():
    day, month = clock_keys()
    stored = vault.protected_read("installation-ai-usage")
    return {
        "day": day,
        "month": month,
        "daily": stored.get("daily", {}) if stored.get("day") == day else {},
        "monthly": stored.get("monthly", {}) if stored.get("month") == month else {},
        "events": stored.get("events", [])[-80:],
    }


def available(provider):
    value = credential(provider)
    return bool(value and value.get("verified"))


def reserve(provider, reason):
    with vault.installation_lock():
        config = settings()
        value = credential(provider)
        if not config["search_enabled"] or not value or not value.get("verified"):
            return None, "not_configured"
        if provider == "openai" and (
            not config["paid_search_enabled"] or config["mode"] == "free_only"
        ):
            return None, "paid_not_authorized"
        counters = usage()
        prefix = "paid" if provider == "openai" else "tavily"
        daily = counters["daily"].get(provider, 0)
        monthly = counters["monthly"].get(provider, 0)
        if daily >= config[prefix + "_daily_limit"] or monthly >= config[prefix + "_monthly_limit"]:
            return None, "local_limit"
        counters["daily"][provider] = daily + 1
        counters["monthly"][provider] = monthly + 1
        vault.protected_save("installation-ai-usage", counters)
        return value, "allowed"


def record(provider, status, elapsed, reason, results=0, confidence="low", credits=None):
    with vault.installation_lock():
        counters = usage()
        event = {
            "at": datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds"),
            "provider": provider,
            "result": status,
            "seconds": round(elapsed, 2),
            "reason": re.sub(r"[^a-z0-9_]", "", reason)[:80],
            "results": results,
            "confidence": confidence,
        }
        if isinstance(credits, (int, float)) and 0 <= credits < 1000:
            event["credits"] = credits
        counters["events"] = [*counters["events"], event][-80:]
        vault.protected_save("installation-ai-usage", counters)


def public_status():
    providers = {}
    for provider in ["tavily", "openai"]:
        value = credential(provider) or {}
        providers[provider] = {
            "configured": bool(value.get("verified")),
            "has_key": bool(value.get("key")),
            "key_hint": key_hint(value),
            "models": value.get("models", []),
            "usage": value.get("usage", {}),
            "source": value.get("source", "none"),
            "message": value.get("message", ""),
        }
    return {
        "permission": "MANAGE_AI_SETTINGS",
        "settings": settings(),
        "providers": providers,
        "usage": usage(),
        "storage": "Windows DPAPI" if os.name == "nt" else "Cofre criptografado local",
    }
