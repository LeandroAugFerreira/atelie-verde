"""Private Rafinha conversations with atomic reservations and explicit cancellation."""

import time
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from . import assistant_provider as provider
from . import assistant_runtime, assistant_stream
from .assistant_engine import respond
from .assistant_installation import settings as research_settings
from .assistant_knowledge import retrieve
from .assistant_media import model_images
from .assistant_request import cloud_permitted, local_access
from .assistant_sensitive import contains_secret
from .database import get_db
from .models import (
    AssistantAttachment,
    AssistantConfiguration,
    AssistantConversation,
    AssistantMessage,
    AssistantPreference,
    now,
)
from .security import admin, current_user

router = APIRouter(prefix="/assistant")
GREETING = "Oi! Eu sou o Rafinha, o assistente virtual do Ateliê Verde 🌿 Posso ajudar com cuidados das plantas, ideias para seu jardim e nossos serviços. O que vamos cuidar hoje?"
SUGGESTIONS = [
    "Como cuidar da minha planta?",
    "Quais plantas combinam com meu espaço?",
    "Quero planejar meu jardim",
    "Conhecer os serviços",
]


class Context(BaseModel):
    model_config = {"extra": "forbid"}
    kind: Literal["species", "product", "article", "project", "quote"]
    id: int = Field(gt=0)


class MessageInput(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}
    text: str = Field(min_length=1, max_length=2000)
    request_id: UUID
    context: Context | None = None


class Preferences(BaseModel):
    model_config = {"extra": "forbid"}
    enabled: bool = True
    motion: bool = True
    typewriter: bool = True
    voice: bool = False


class Configuration(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}
    enabled: bool = True
    greeting: str = Field(default=GREETING, min_length=10, max_length=500)
    suggestions: list[str] = Field(default=SUGGESTIONS, min_length=1, max_length=6)

    def cleaned(self):
        if any(not s.strip() or len(s) > 100 for s in self.suggestions):
            raise HTTPException(422, "As sugestões precisam ter entre 1 e 100 caracteres.")
        return {**self.model_dump(), "suggestions": [s.strip() for s in self.suggestions]}


def data(row):
    result = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    if isinstance(row, AssistantMessage):
        result["expression"] = (row.context or {}).get("_expression", "explaining")
        result["meta"] = (row.context or {}).get("_meta", {})
        result["images"] = result["meta"].get("images", [])
        result["context"] = {k: v for k, v in (row.context or {}).items() if not k.startswith("_")}
    return result


def config(db):
    row = db.get(AssistantConfiguration, 1)
    return (
        {k: getattr(row, k) for k in ["enabled", "greeting", "suggestions"]}
        if row
        else Configuration().model_dump()
    )


def own(db, id, user):
    row = db.scalar(
        select(AssistantConversation).where(
            AssistantConversation.id == id, AssistantConversation.user_id == user.id
        )
    )
    if not row:
        raise HTTPException(404, "Conversa não encontrada.")
    return row


def messages(db, id):
    return list(
        db.scalars(
            select(AssistantMessage)
            .where(AssistantMessage.conversation_id == id)
            .order_by(AssistantMessage.id)
        )
    )


@router.get("/status")
def status(request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
    cfg = config(db)
    if assistant_runtime.chatgpt_mode():
        connected = bool(
            cfg["enabled"] and local_access(request) and assistant_runtime.connection()
        )
        return {
            **cfg,
            "mode": "chatgpt" if connected else "catalog",
            "label": "ChatGPT" if connected else "Orientações do catálogo",
            "local_available": False,
            "research_enabled": connected,
        }
    local = cfg["enabled"] and provider.available()
    return {
        **cfg,
        "mode": "local" if local else "catalog",
        "label": "IA local" if local else "Orientações do catálogo",
        "local_available": bool(local),
        "research_enabled": research_settings()["search_enabled"],
    }


@router.get("/local/health")
def local_health(user=Depends(current_user)):
    return provider.health_check()


@router.get("/configuration")
def configuration(db: Session = Depends(get_db), user=Depends(admin)):
    return config(db)


@router.put("/configuration")
def save_configuration(body: Configuration, db: Session = Depends(get_db), user=Depends(admin)):
    values = body.cleaned()
    row = db.get(AssistantConfiguration, 1)
    if row:
        for key, value in values.items():
            setattr(row, key, value)
    else:
        db.add(AssistantConfiguration(id=1, **values))
    db.commit()
    return values


@router.post("/test")
def test_assistant(
    body: MessageInput, request: Request, db: Session = Depends(get_db), user=Depends(admin)
):
    gate = cloud_permitted.set(local_access(request))
    try:
        result = respond(db, user, body.text, None, [], {})
    finally:
        cloud_permitted.reset(gate)
    return {
        "text": result["text"],
        "mode": result["mode"],
    }


@router.get("/preferences")
def preferences(db: Session = Depends(get_db), user=Depends(current_user)):
    row = db.get(AssistantPreference, user.id)
    return (
        {key: getattr(row, key) for key in Preferences.model_fields}
        if row
        else Preferences().model_dump()
    )


@router.put("/preferences")
def save_preferences(body: Preferences, db: Session = Depends(get_db), user=Depends(current_user)):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    values = body.model_dump()
    insert = sqlite_insert if db.bind.dialect.name == "sqlite" else pg_insert
    db.execute(
        insert(AssistantPreference)
        .values(user_id=user.id, **values)
        .on_conflict_do_update(index_elements=["user_id"], set_=values)
    )
    db.commit()
    return values


@router.post("/conversations", status_code=201)
def create_conversation(db: Session = Depends(get_db), user=Depends(current_user)):
    if not config(db)["enabled"]:
        raise HTTPException(409, "O assistente foi desativado pela administração.")
    count = db.scalar(
        select(func.count())
        .select_from(AssistantConversation)
        .where(AssistantConversation.user_id == user.id)
    )
    if count >= 100:
        raise HTTPException(409, "Exclua uma conversa antiga para iniciar outra.")
    row = AssistantConversation(user_id=user.id)
    db.add(row)
    db.commit()
    return data(row)


@router.get("/conversations")
def conversations(db: Session = Depends(get_db), user=Depends(current_user)):
    return [
        data(row)
        for row in db.scalars(
            select(AssistantConversation)
            .where(AssistantConversation.user_id == user.id)
            .order_by(AssistantConversation.updated_at.desc(), AssistantConversation.id.desc())
            .limit(100)
        )
    ]


@router.get("/conversations/{id}")
def conversation(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    row = own(db, id, user)
    attachments = list(
        db.scalars(select(AssistantAttachment).where(AssistantAttachment.conversation_id == id))
    )
    return {
        **data(row),
        "messages": [data(m) for m in messages(db, id)],
        "attachments": [
            {"id": a.id, "url": f"/api/assistant/attachments/{a.id}/content"} for a in attachments
        ],
    }


@router.get("/conversations/{id}/progress")
def progress(id: int, request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
    row = own(db, id, user)
    preview = (
        assistant_stream.snapshot(user.id, id, row.pending_request)
        if row.pending_request and local_access(request)
        else {}
    )
    from fastapi.responses import JSONResponse

    return JSONResponse(
        {
            "request_id": row.pending_request,
            "phase": "writing"
            if preview.get("text")
            else (
                (row.memory or {}).get("_progress", "context") if row.pending_request else "idle"
            ),
            **preview,
        },
        headers={"Cache-Control": "no-store"},
    )


@router.delete("/conversations/{id}", status_code=204)
def remove_conversation(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    own(db, id, user)
    assistant_stream.discard(user.id, id)
    from .assistant_uploads import delete_files

    files = list(
        db.scalars(select(AssistantAttachment).where(AssistantAttachment.conversation_id == id))
    )
    db.execute(delete(AssistantAttachment).where(AssistantAttachment.conversation_id == id))
    db.execute(delete(AssistantMessage).where(AssistantMessage.conversation_id == id))
    db.execute(
        delete(AssistantConversation).where(
            AssistantConversation.id == id, AssistantConversation.user_id == user.id
        )
    )
    db.commit()
    delete_files(files)
    return Response(status_code=204)


@router.post("/conversations/{id}/messages/{request_id}/cancel")
def cancel(id: int, request_id: UUID, db: Session = Depends(get_db), user=Depends(current_user)):
    own(db, id, user)
    req = str(request_id)
    changed = db.execute(
        update(AssistantConversation)
        .where(AssistantConversation.id == id, AssistantConversation.pending_request == req)
        .values(pending_request="", updated_at=now())
    ).rowcount
    if changed:
        assistant_stream.discard(user.id, id, req)
        db.execute(
            update(AssistantMessage)
            .where(
                AssistantMessage.conversation_id == id,
                AssistantMessage.request_id == req,
                AssistantMessage.role == "assistant",
                AssistantMessage.status == "pending",
            )
            .values(status="interrupted", text="Resposta interrompida.")
        )
    db.commit()
    return {"cancelled": bool(changed)}


@router.post("/conversations/{id}/messages")
def send(
    id: int,
    body: MessageInput,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    started_at = time.monotonic()
    row = own(db, id, user)
    if not config(db)["enabled"]:
        raise HTTPException(409, "O assistente foi desativado pela administração.")
    if contains_secret(body.text):
        raise HTTPException(
            422,
            "Não envie chaves ou tokens no chat. As credenciais devem ser configuradas pelo administrador no campo protegido.",
        )
    req = str(body.request_id)
    existing = db.scalar(
        select(AssistantMessage).where(
            AssistantMessage.conversation_id == id,
            AssistantMessage.request_id == req,
            AssistantMessage.role == "assistant",
        )
    )
    if existing:
        if existing.status == "pending":
            raise HTTPException(409, "Esta resposta ainda está sendo preparada.")
        return data(existing)
    history = messages(db, id)
    if len(history) >= 200:
        raise HTTPException(409, "Esta conversa está completa. Inicie uma nova conversa.")
    facts = retrieve(
        db, user, body.text, body.context.model_dump() if body.context else None, history
    )
    stale = (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat()
    changed = db.execute(
        update(AssistantConversation)
        .where(
            AssistantConversation.id == id,
            or_(
                AssistantConversation.pending_request == "",
                AssistantConversation.updated_at < stale,
            ),
        )
        .values(
            pending_request=req,
            title=body.text[:80] if not history else row.title,
            updated_at=now(),
        )
    ).rowcount
    if not changed:
        db.rollback()
        raise HTTPException(409, "Aguarde ou interrompa a resposta atual.")
    # A server restart or expired reservation must not leave an orphaned pending bubble.
    db.execute(
        update(AssistantMessage)
        .where(AssistantMessage.conversation_id == id, AssistantMessage.status == "pending")
        .values(status="interrupted", text="Resposta interrompida.")
    )
    db.add(
        AssistantMessage(
            conversation_id=id,
            request_id=req,
            role="user",
            text=body.text,
            context=facts["context"],
        )
    )
    reply = AssistantMessage(
        conversation_id=id,
        request_id=req,
        role="assistant",
        text="",
        status="pending",
        context=facts["context"],
    )
    db.add(reply)
    db.commit()
    reply_id = reply.id

    # No write transaction is held while a local model is running.
    def cancelled():
        return (
            db.scalar(
                select(AssistantConversation.pending_request).where(AssistantConversation.id == id)
            )
            != req
        )

    def update_progress(phase):
        db.execute(
            update(AssistantConversation)
            .where(AssistantConversation.id == id, AssistantConversation.pending_request == req)
            .values(memory={**(row.memory or {}), "_progress": phase})
        )
        db.commit()

    gate = cloud_permitted.set(local_access(request))
    publish = assistant_stream.begin(user.id, id, req)
    try:
        owned_photos = list(
            db.scalars(
                select(AssistantAttachment)
                .where(AssistantAttachment.conversation_id == id)
                .order_by(AssistantAttachment.id)
            )
        )
        result = respond(
            db,
            user,
            body.text,
            body.context.model_dump() if body.context else None,
            history,
            row.memory,
            cancelled,
            update_progress,
            started_at,
            input_images=model_images(owned_photos),
            stream_reply=publish,
        )
    finally:
        assistant_stream.discard(user.id, id, req)
        cloud_permitted.reset(gate)
    text = result["text"]
    changed = db.execute(
        update(AssistantConversation)
        .where(
            AssistantConversation.id == id,
            AssistantConversation.user_id == user.id,
            AssistantConversation.pending_request == req,
        )
        .values(pending_request="", updated_at=now(), memory=result["memory"])
    ).rowcount
    if not changed:
        db.rollback()
        raise HTTPException(409, "A resposta foi interrompida ou a conversa foi excluída.")
    db.execute(
        update(AssistantMessage)
        .where(AssistantMessage.id == reply_id, AssistantMessage.status == "pending")
        .values(
            text=text[:4000],
            mode=result["mode"],
            status="completed",
            sources=result["sources"],
            actions=result["actions"],
            context={
                **result["context"],
                "_expression": result["meta"]["expressions"]["final"],
                "_meta": result["meta"],
            },
        )
    )
    db.commit()
    db.expire_all()
    return data(db.get(AssistantMessage, reply_id))
