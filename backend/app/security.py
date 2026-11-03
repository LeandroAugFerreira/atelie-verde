import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from .database import DATA_DIR, get_db
from .models import User


def load_secret():
    value = os.getenv("JWT_SECRET")
    if value:
        if len(value) < 32:
            raise RuntimeError("JWT_SECRET deve ter pelo menos 32 caracteres.")
        return value
    if os.getenv("APP_ENV") == "production":
        raise RuntimeError("Configure JWT_SECRET em produção.")
    path = DATA_DIR / ".jwt-secret"
    try:
        with path.open("x", encoding="utf-8") as file:
            file.write(secrets.token_urlsafe(48))
    except FileExistsError:
        pass
    return path.read_text(encoding="utf-8")


SECRET = load_secret()
passwords = PasswordHash.recommended()
bearer = HTTPBearer()


def token_for(user):
    return jwt.encode(
        {"sub": str(user.id), "exp": datetime.now(timezone.utc) + timedelta(hours=8)},
        SECRET,
        algorithm="HS256",
    )


def current_user(credentials=Depends(bearer), db: Session = Depends(get_db)):
    try:
        claims = jwt.decode(
            credentials.credentials,
            SECRET,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        user = db.get(User, int(claims["sub"]))
        if not user or not user.active or not user.portal_enabled:
            raise ValueError()
        return user
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(401, "Sessão inválida ou expirada.")


def admin(user: User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Acesso exclusivo do administrador.")
    return user
