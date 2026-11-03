"""MANAGE_AI_SETTINGS: installation configuration is exclusive to local administrators."""

import re
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from . import assistant_installation as installation
from .assistant_provider import health_check as local_health
from .assistant_request import local_access
from .assistant_search_providers import ProviderError, openai_models, tavily_usage
from .security import admin

router = APIRouter(prefix="/assistant/admin-ai", tags=["Administrator AI"])


def manage(request: Request, user=Depends(admin)):
    if not local_access(request):
        raise HTTPException(
            403, "Configure os provedores na instalação local, usando o portal administrativo."
        )
    return user


async def incoming_key(request: Request):
    try:
        body = await request.json()
    except (ValueError, TypeError):
        raise HTTPException(422, "Informe uma chave válida no campo protegido.")
    key = body.get("key") if isinstance(body, dict) else None
    if not isinstance(key, str) or not 20 <= len(key) <= 300:
        raise HTTPException(422, "Informe uma chave válida no campo protegido.")
    return key


def validate(provider, key):
    if not re.fullmatch(
        r"tvly-[A-Za-z0-9_-]{15,295}" if provider == "tavily" else r"sk-[A-Za-z0-9_-]{17,297}", key
    ):
        raise HTTPException(422, "Confira o formato da sua chave pessoal.")
    try:
        return (
            {"usage": tavily_usage(key)} if provider == "tavily" else {"models": openai_models(key)}
        )
    except (ProviderError, httpx.HTTPError, TimeoutError, ValueError, TypeError, KeyError):
        raise HTTPException(
            400,
            "Não foi possível validar a chave. Confira a conta, a cota e a conexão; nenhuma pesquisa paga foi ativada.",
        )


@router.get("")
def status(user=Depends(manage)):
    return installation.public_status()


@router.put("/settings")
def configure(body: installation.SettingsPatch, user=Depends(manage)):
    with installation.vault.installation_lock():
        current = installation.settings()
        current.update(body.model_dump(exclude_none=True, exclude_unset=True))
        if current["mode"] == "free_only":
            current["paid_search_enabled"] = False
        if current["paid_search_enabled"]:
            key = installation.credential("openai")
            if not key or not key.get("verified"):
                raise HTTPException(
                    409, "Configure e valide sua chave OpenAI antes de autorizar pesquisa paga."
                )
            if current["openai_model"] not in {m["id"] for m in key.get("models", [])}:
                raise HTTPException(422, "Selecione um modelo liberado para esta chave.")
        installation.vault.protected_save(
            "installation-ai-settings",
            installation.ResearchSettings.model_validate(current).model_dump(),
        )
    return installation.public_status()


@router.post("/providers/{provider}/key")
def save(provider: Literal["tavily", "openai"], user=Depends(manage), key=Depends(incoming_key)):
    details = validate(provider, key)
    installation.save_credential(provider, key, details)
    return installation.public_status()


@router.post("/providers/{provider}/test")
def test(provider: Literal["tavily", "openai"], user=Depends(manage)):
    value = installation.credential(provider)
    if not value:
        raise HTTPException(409, "Configure sua própria chave primeiro.")
    details = validate(provider, value["key"])
    with installation.vault.installation_lock():
        active = installation.credential(provider)
        if (
            not active
            or active.get("generation") != value.get("generation")
            or active.get("key") != value.get("key")
        ):
            raise HTTPException(
                409,
                "A credencial mudou durante a verificação. Atualize o painel e teste novamente.",
            )
        # Environment credentials become protected records only after admin validation.
        if not active.get("verified"):
            installation.save_credential(provider, active["key"], details)
        else:
            installation.vault.protected_save("installation-" + provider, {**active, **details})
    return installation.public_status()


@router.delete("/providers/{provider}", status_code=204)
def remove(provider: Literal["tavily", "openai"], user=Depends(manage)):
    installation.remove_credential(provider)


@router.get("/local/health")
def ollama(user=Depends(manage)):
    return local_health()
