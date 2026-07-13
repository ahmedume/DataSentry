from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import _http, get_current_user, require_dataset_access
from app.core.storage import storage
from app.db.models import Dataset, Report, User
from app.db.session import get_db
from app.schemas.reports import ReportStatusOut
from app.workers.tasks import generate_report

router = APIRouter(prefix="/datasets", tags=["reports"])


@router.post("/{dataset_id}/report", response_model=ReportStatusOut)
def request_report(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = require_dataset_access(dataset_id, user, db)
    generate_report.delay(dataset_id)
    return ReportStatusOut(dataset_id=dataset_id, status="QUEUED", download_ready=False)


@router.get("/{dataset_id}/report/status", response_model=ReportStatusOut)
def report_status(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = require_dataset_access(dataset_id, user, db)
    rep = db.query(Report).filter_by(dataset_id=ds.id).first()
    if not rep:
        return ReportStatusOut(dataset_id=dataset_id, status="QUEUED", download_ready=False)
    return ReportStatusOut(
        dataset_id=dataset_id,
        status=rep.status,
        error_message=rep.error_message,
        download_ready=(rep.status == "READY" and storage.report_exists(dataset_id)),
    )


@router.get("/{dataset_id}/report/download")
def report_download(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = require_dataset_access(dataset_id, user, db)
    if not storage.report_exists(dataset_id):
        raise _http(409, "NOT_READY", "Report is not ready for download.")
    path = storage.report_path(dataset_id)

    def iterfile():
        with open(path, "rb") as f:
            yield from f

    return StreamingResponse(iterfile(), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{ds.original_filename}_report.pdf"'})


@router.get("/{dataset_id}/download/cleaned")
def download_cleaned(dataset_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ds = require_dataset_access(dataset_id, user, db)
    if not storage.cleaned_exists(dataset_id):
        raise _http(409, "NO_CLEANED", "No cleaned dataset available. Apply cleaning first.")
    path = storage.cleaned_path(dataset_id)

    def iterfile():
        with open(path, "rb") as f:
            yield from f

    return StreamingResponse(iterfile(), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{ds.original_filename}_cleaned.csv"'})
