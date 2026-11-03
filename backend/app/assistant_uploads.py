"""Owned photos for visual analysis through the authorized ChatGPT connection."""

import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .assistant import own
from .assistant_media import FOLDER
from .assistant_state import Memory
from .database import get_db
from .models import AssistantAttachment, AssistantConversation
from .security import current_user
from .transactions import locked

router = APIRouter(prefix="/assistant")


def delete_files(rows):
    for row in rows:
        (FOLDER / row.filename).unlink(missing_ok=True)


@router.post("/conversations/{id}/attachments", status_code=201)
async def upload(
    id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(current_user)
):
    row = own(db, id, user)
    row = locked(db, AssistantConversation, row.id)
    if row.pending_request:
        raise HTTPException(409, "Aguarde a resposta antes de anexar a foto.")
    if (
        db.scalar(
            select(func.count())
            .select_from(AssistantAttachment)
            .where(AssistantAttachment.conversation_id == id)
        )
        >= 3
    ):
        raise HTTPException(422, "Use até três fotos por conversa.")
    raw = await file.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(422, "A foto deve ter até 5 MB.")
    try:
        image = Image.open(io.BytesIO(raw))
        extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}.get(image.format)
        if (
            not extension
            or image.width * image.height > 16000000
            or getattr(image, "is_animated", False)
        ):
            raise ValueError()
        image.verify()
    except (ValueError, UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError):
        raise HTTPException(422, "Envie uma imagem JPEG, PNG, WebP ou GIF estático válida.")
    filename = f"{uuid.uuid4().hex}.{extension}"
    FOLDER.mkdir(parents=True, exist_ok=True)
    path = FOLDER / filename
    path.write_bytes(raw)
    record = AssistantAttachment(conversation_id=id, filename=filename)
    db.add(record)
    memory = Memory.model_validate(row.memory or {})
    memory.slots["photo"] = "foto fornecida na conversa"
    memory.known_unknowns = [f for f in memory.known_unknowns if f != "photo"]
    if memory.pending_field == "photo":
        memory.pending_field = None
    row.memory = memory.model_dump()
    try:
        db.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {
        "id": record.id,
        "url": f"/api/assistant/attachments/{record.id}/content",
        "message": "Foto recebida. Ela será analisada quando a conexão ChatGPT estiver disponível.",
    }


@router.get("/attachments/{id}/content")
def content(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    record = db.get(AssistantAttachment, id)
    if not record:
        raise HTTPException(404, "Foto não encontrada.")
    own(db, record.conversation_id, user)
    path = FOLDER / record.filename
    if not path.is_file():
        raise HTTPException(404, "Foto não encontrada.")
    return FileResponse(
        path,
        media_type={
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(path.suffix, "image/jpeg"),
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
