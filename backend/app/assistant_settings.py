"""Load only assistant settings; never override database or authentication configuration."""

import os
import sys
from pathlib import Path

from dotenv import dotenv_values

KEYS = {
    "RAFINHA_MODE",
    "RAFINHA_PROVIDER",
    "RAFINHA_OLLAMA_URL",
    "RAFINHA_OLLAMA_MODEL",
    "WEB_SEARCH_PROVIDER",
    "WEB_SEARCH_URL",
    "RAFINHA_ALLOW_DEV_API_KEYS",
}


def load():
    if getattr(sys, "frozen", False):
        return
    path = Path(__file__).resolve().parents[2] / ".env"
    if path.is_file():
        for key, value in dotenv_values(path).items():
            if key in KEYS and value:
                os.environ.setdefault(key, value)
        if (
            os.getenv("APP_ENV", "development") == "development"
            and os.getenv("RAFINHA_ALLOW_DEV_API_KEYS", "false").lower() == "true"
        ):
            for key, value in dotenv_values(path).items():
                if key in {"TAVILY_API_KEY", "OPENAI_API_KEY"} and value:
                    os.environ.setdefault(key, value)
