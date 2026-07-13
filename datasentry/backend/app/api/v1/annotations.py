from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import _http, get_current_user
from app.core.rbac import membership_for
from app.db.models import Annotation, Dataset, User
from app.db.session import get_db
from app.schemas.v34 import AnnotationCreate, AnnotationOut

router = APIRouter(prefix="/datasets", tags=["annotations"])


def _access(db: Session, user: User, ds: Dataset) -> bool:
    if ds.owner_id == user.id:
        return True
    if ds.team_id and membership_for(db, user, ds.team_id):
        return True
    if ds.owner_id is None and ds.team_id is None:
        return True  # legacy global dataset
    return False


def _out(a: Annotation) -> AnnotationOut:
    return AnnotationOut(
        id=str(a.id),
        dataset_id=str(a.dataset_id),
        author_id=str(a.author_id),
        column_name=a.column_name,
        body=a.body,
        created_at=a.created_at.isoformat() if a.created_at else None,
    )


@router.post("/{dataset_id}/annotations", response_model=AnnotationOut, status_code=201)
def create_annotation(dataset_id: str, body: AnnotationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        ds = db.get(Dataset, uuid.UUID(dataset_id))
    except ValueError:
        raise _http(404, "NOT_FOUND", "Dataset not found.")
    if not ds:
        raise _http(404, "NOT_FOUND", "Dataset not found.")
    if not _access(db, user, ds):
        raise _http(403, "FORBIDDEN", "Not allowed to annotate this dataset.")
    ann = Annotation(dataset_id=ds.id, author_id=user.id, column_name=body.column_name, body=body.body)
    db.add(ann)
    db.commit()
    return _out(ann)


@router.get("/{dataset_id}/annotations", response_model=list[AnnotationOut])
def list_annotations(dataset_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        ds = db.get(Dataset, uuid.UUID(dataset_id))
    except ValueError:
        raise _http(404, "NOT_FOUND", "Dataset not found.")
    if not ds:
        raise _http(404, "NOT_FOUND", "Dataset not found.")
    if not _access(db, user, ds):
        raise _http(403, "FORBIDDEN", "Not allowed to view this dataset.")
    rows = db.query(Annotation).filter(Annotation.dataset_id == ds.id).order_by(Annotation.created_at.desc()).all()
    return [_out(a) for a in rows]
