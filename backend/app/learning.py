from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_db
from .models import Article, LearningProgress
from .security import current_user

router = APIRouter(prefix="/learning")


def serialize(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


@router.get("")
def articles(db: Session = Depends(get_db)):
    return [serialize(row) for row in db.scalars(select(Article).order_by(Article.id))]


@router.get("/progress")
def progress(db: Session = Depends(get_db), user=Depends(current_user)):
    return [
        serialize(row)
        for row in db.scalars(select(LearningProgress).where(LearningProgress.user_id == user.id))
    ]


@router.put("/{id}/complete")
def complete(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    if not db.get(Article, id):
        raise HTTPException(404, "Guia não encontrado.")
    existing = db.scalar(
        select(LearningProgress).where(
            LearningProgress.user_id == user.id, LearningProgress.article_id == id
        )
    )
    if existing:
        return serialize(existing)
    row = LearningProgress(user_id=user.id, article_id=id)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        row = db.scalar(
            select(LearningProgress).where(
                LearningProgress.user_id == user.id, LearningProgress.article_id == id
            )
        )
    return serialize(row)


@router.delete("/{id}/complete", status_code=204)
def incomplete(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    db.execute(
        delete(LearningProgress).where(
            LearningProgress.user_id == user.id, LearningProgress.article_id == id
        )
    )
    db.commit()
    return Response(status_code=204)
