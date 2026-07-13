from __future__ import annotations

import io
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import storage
from app.db.models import (
    AiInsight,
    AlertRule,
    CleanedDataset,
    CleaningRecommendation,
    Connector,
    Dataset,
    DriftSnapshot,
    MonitorRun,
    MonitorSchedule,
    ProfilingResult,
    Report,
    TrainingJob,
)
from app.db.session import SessionLocal
from app.services import (
    ai_analyst,
    ai_cleaner,
    alerts as alerts_svc,
    chart_aggregator,
    cleaning_engine,
    connectors,
    drift as drift_svc,
    profiler,
    training as training_svc,
)
from app.services.report_builder import generate_report_pdf
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_db() -> Session:
    return SessionLocal()


def _set_status(db: Session, dataset_id: str, status: str, error: str | None = None) -> None:
    ds = db.get(Dataset, _uuid(dataset_id))
    if ds:
        ds.status = status
        if error is not None:
            ds.error_message = error
        db.commit()


def _uuid(dataset_id: str):
    return uuid.UUID(dataset_id)


@celery_app.task(name="profile_dataset")
def profile_dataset(dataset_id: str) -> None:
    db = _get_db()
    try:
        ds = db.get(Dataset, _uuid(dataset_id))
        if not ds:
            return
        ds.status = "PROFILING"
        db.commit()
        df = profiler.read_csv(storage.raw_path(dataset_id))
        byte_size = storage.raw_path(dataset_id).stat().st_size
        profile = profiler.profile_dataframe(df, byte_size)
        ds.row_count = profile["row_count"]
        ds.column_count = profile["column_count"]
        ds.byte_size = profile["byte_size"]
        db.add(ProfilingResult(dataset_id=ds.id, column_profiles=profile["columns"], duplicate_row_count=profile["duplicate_row_count"]))
        db.commit()
        ds.status = "READY"
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("profiling failed")
        _set_status(db, dataset_id, "FAILED", str(exc))
    finally:
        db.close()


@celery_app.task(name="generate_ai_insights")
def generate_ai_insights(dataset_id: str) -> None:
    db = _get_db()
    try:
        ds = db.get(Dataset, _uuid(dataset_id))
        prof = db.query(ProfilingResult).filter_by(dataset_id=ds.id).first()
        if not prof:
            return
        profile = {
            "row_count": ds.row_count,
            "column_count": ds.column_count,
            "duplicate_row_count": prof.duplicate_row_count,
            "columns": prof.column_profiles,
        }
        df = profiler.read_csv(storage.raw_path(dataset_id))
        sample = df.head(50).where(df.notna(), None).to_dict(orient="records")
        insights = ai_analyst.build_insights(profile, sample)
        db.add(AiInsight(
            dataset_id=ds.id,
            column_explanations=insights["column_explanations"],
            candidate_targets=insights.get("candidate_targets", []),
            possible_tasks=insights.get("possible_tasks", []),
            risks_and_assumptions=insights.get("risks_and_assumptions", []),
        ))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai insights generation failed: %s", exc)
    finally:
        db.close()


@celery_app.task(name="generate_cleaning_recommendations")
def generate_cleaning_recommendations(dataset_id: str) -> None:
    db = _get_db()
    try:
        ds = db.get(Dataset, _uuid(dataset_id))
        prof = db.query(ProfilingResult).filter_by(dataset_id=ds.id).first()
        if not prof:
            return
        profile = {
            "row_count": ds.row_count,
            "column_count": ds.column_count,
            "duplicate_row_count": prof.duplicate_row_count,
            "columns": prof.column_profiles,
        }
        recs = ai_cleaner.build_recommendations(profile)
        # Validate (SRS-4.2): discard any rec whose rationale lacks its stat_reference.
        for r in recs:
            if r["stat_reference"] not in r.get("rationale", ""):
                logger.warning("discarding recommendation without traceable stat: %s", r)
                continue
            db.add(CleaningRecommendation(
                dataset_id=ds.id,
                column_name=r.get("column_name"),
                issue_type=r["issue_type"],
                stat_reference=r["stat_reference"],
                recommendation=r["recommendation"],
                rationale=r["rationale"],
            ))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("cleaning recommendations failed: %s", exc)
    finally:
        db.close()


@celery_app.task(name="apply_cleaning")
def apply_cleaning(dataset_id: str, accepted_ids: list[str]) -> None:
    db = _get_db()
    try:
        ds = db.get(Dataset, _uuid(dataset_id))
        if not ds:
            return
        accepted_uuids = [_uuid(i) for i in accepted_ids]
        recs = db.query(CleaningRecommendation).filter(
            CleaningRecommendation.dataset_id == ds.id,
            CleaningRecommendation.id.in_(accepted_uuids),
        ).all()
        accepted = [{"column_name": r.column_name, "issue_type": r.issue_type, "recommendation": r.recommendation} for r in recs]
        df = profiler.read_csv(storage.raw_path(dataset_id))
        df_clean, diff = cleaning_engine.apply_transforms(df, accepted)
        path = storage.write_cleaned(dataset_id, df_clean)
        db.add(CleanedDataset(
            dataset_id=ds.id,
            file_path=str(path),
            applied_recommendation_ids=[str(r.id) for r in recs],
            row_count_before=diff["row_count_before"],
            row_count_after=diff["row_count_after"],
            diff_summary=diff,
        ))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("apply cleaning failed")
        _set_status(db, dataset_id, "FAILED", str(exc))
    finally:
        db.close()


@celery_app.task(name="generate_report")
def generate_report(dataset_id: str) -> None:
    db = _get_db()
    try:
        ds = db.get(Dataset, _uuid(dataset_id))
        if not ds:
            return
        rep = db.query(Report).filter_by(dataset_id=ds.id).first()
        if not rep:
            rep = Report(dataset_id=ds.id, status="GENERATING")
            db.add(rep)
        else:
            rep.status = "GENERATING"
        db.commit()

        prof = db.query(ProfilingResult).filter_by(dataset_id=ds.id).first()
        insights_row = db.query(AiInsight).filter_by(dataset_id=ds.id).first()
        cleaned = db.query(CleanedDataset).filter_by(dataset_id=ds.id).first()

        profile = {
            "row_count": ds.row_count,
            "column_count": ds.column_count,
            "byte_size": ds.byte_size or 0,
            "duplicate_row_count": prof.duplicate_row_count if prof else 0,
            "columns": prof.column_profiles if prof else [],
        }
        insights = None
        if insights_row:
            insights = {
                "column_explanations": insights_row.column_explanations,
                "candidate_targets": insights_row.candidate_targets,
                "possible_tasks": insights_row.possible_tasks,
                "risks_and_assumptions": insights_row.risks_and_assumptions,
            }
        df = profiler.read_csv(storage.raw_path(dataset_id)) if storage.raw_path(dataset_id).exists() else None
        pdf = generate_report_pdf(
            ds.original_filename,
            profile,
            insights,
            cleaned.diff_summary if cleaned else None,
            df=df,
        )
        storage.write_report(dataset_id, pdf)
        rep.status = "READY"
        rep.file_path = str(storage.report_path(dataset_id))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("report generation failed")
        if rep:
            rep.status = "FAILED"
            rep.error_message = str(exc)
            db.commit()
    finally:
        db.close()


@celery_app.task(name="ingest_connector")
def ingest_connector(connector_id: str, dataset_id: str) -> str | None:
    """Pull data from a registered connector and run the standard v1 pipeline."""
    db = _get_db()
    try:
        conn = db.get(Connector, _uuid(connector_id))
        if not conn:
            return None
        connector = connectors.build_connector(conn.type, connectors.parse_config(conn.config))
        data, fname = connector.pull()
        storage.save_raw(dataset_id, data)
        ds = db.get(Dataset, _uuid(dataset_id))
        if ds:
            ds.original_filename = fname
            ds.status = "QUEUED"
            ds.file_path = str(storage.raw_path(dataset_id))
            ds.owner_id = conn.owner_id
            db.commit()
        profile_dataset.delay(dataset_id)
        generate_ai_insights.delay(dataset_id)
        generate_cleaning_recommendations.delay(dataset_id)
        return dataset_id
    except Exception as exc:  # noqa: BLE001
        logger.exception("connector ingest failed")
        ds = db.get(Dataset, _uuid(dataset_id))
        if ds:
            ds.status = "FAILED"
            ds.error_message = str(exc)
            db.commit()
        conn = db.get(Connector, _uuid(connector_id))
        if conn:
            conn.last_error = str(exc)
            db.commit()
        return None
    finally:
        db.close()


@celery_app.task(name="train_model")
def train_model(job_id: str, source_type: str, source_id: str, target: str, task: str) -> None:
    """Train a baseline model on a dataset or connector source."""
    db = _get_db()
    try:
        job = db.get(TrainingJob, _uuid(job_id))
        if not job:
            return
        job.status = "RUNNING"
        db.commit()

        df = _load_source_df(db, source_type, source_id)

        result = training_svc.train(df, target, task)
        training_svc.save_model(job_id, result["model_bytes"])
        job.status = "READY"
        job.metrics_json = json.dumps(result["metrics"])
        job.feature_importances_json = json.dumps(result["feature_importances"])
        job.model_path = str(storage.model_path(job_id))
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("training failed")
        job = db.get(TrainingJob, _uuid(job_id))
        if job:
            job.status = "FAILED"
            job.error_message = str(exc)
            db.commit()
    finally:
        db.close()


def _load_source_df(db: Session, source_type: str, source_id: str):
    source_id = str(source_id)
    if source_type == "dataset":
        ds = db.get(Dataset, _uuid(source_id))
        if not ds or not storage.raw_path(source_id).exists():
            raise ValueError("Dataset data unavailable.")
        return profiler.read_csv(storage.raw_path(source_id))
    if source_type == "connector":
        conn = db.get(Connector, _uuid(source_id))
        if not conn:
            raise ValueError("Connector not found.")
        svc = connectors.build_connector(conn.type, connectors.parse_config(conn.config))
        data, _ = svc.pull()
        return profiler.read_csv(io.BytesIO(data))
    raise ValueError("Unknown source_type.")


@celery_app.task(name="run_monitor")
def run_monitor(schedule_id: str) -> None:
    """Pull the latest data for a schedule, snapshot it, and drift-check vs baseline."""
    db = _get_db()
    now = datetime.now(timezone.utc)
    try:
        sched = db.get(MonitorSchedule, _uuid(schedule_id))
        if not sched:
            return
        run = MonitorRun(schedule_id=sched.id, owner_id=sched.owner_id, status="RUNNING")
        db.add(run)
        db.commit()
        run_id = str(run.id)

        df = _load_source_df(db, sched.source_type, sched.source_id)
        sample = df.head(5000)
        snap_id = str(uuid.uuid4())
        storage.save_snapshot(snap_id, sample)
        byte_size = 0
        if sched.source_type == "dataset":
            try:
                byte_size = storage.raw_path(str(sched.source_id)).stat().st_size
            except Exception:
                byte_size = 0
        profile = drift_svc.build_profile_json(df, byte_size)
        ds_ref = _uuid(str(sched.source_id))
        snap = DriftSnapshot(
            id=_uuid(snap_id),
            owner_id=sched.owner_id,
            dataset_id=ds_ref,
            label=f"monitor {sched.name}",
            profile_json=json.dumps(profile),
            sample_path=str(storage.snapshot_path(snap_id)),
            row_count=str(df.shape[0]),
        )
        db.add(snap)
        db.commit()

        summary: dict = {"rows_processed": int(df.shape[0]), "max_drift": 0.0, "status": "STABLE"}
        drift_status = "STABLE"
        if sched.baseline_snapshot_id and snap.sample_path:
            base = db.get(DriftSnapshot, _uuid(sched.baseline_snapshot_id))
            if base and base.sample_path:
                b_df = profiler.read_csv(base.sample_path)
                results = drift_svc.compare_dataframes(b_df, sample, float(sched.drift_threshold))
                summary = {**summary, **results}
                drift_status = results["status"]
                alerts_svc.process_scope(
                    db,
                    "monitor",
                    schedule_id,
                    {"drift_psi": results["max_drift"], "drift_status": drift_status},
                )

        run = db.get(MonitorRun, _uuid(run_id))
        run.status = "READY"
        run.finished_at = now
        run.rows_processed = str(df.shape[0])
        run.drift_status = drift_status
        run.drift_summary_json = json.dumps(summary)
        run.snapshot_id = _uuid(snap_id)
        sched.last_run_at = now
        try:
            from app.services import webhooks as webhook_svc

            webhook_svc.fire_event(
                db,
                "monitor.run",
                {"schedule_id": str(sched.id), "drift_status": drift_status, "summary": summary},
                owner_id=sched.owner_id,
                team_id=sched.team_id,
            )
        except Exception:
            pass
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.exception("monitor run failed")
        run = (
            db.query(MonitorRun)
            .filter(MonitorRun.schedule_id == _uuid(schedule_id))
            .order_by(MonitorRun.started_at.desc())
            .first()
        )
        if run:
            run.status = "FAILED"
            db.commit()
    finally:
        db.close()


@celery_app.task(name="run_due_monitors")
def run_due_monitors() -> None:
    """Entry point for a Celery beat schedule: runs all schedules past their cadence."""
    db = SessionLocal()
    try:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        schedules = db.query(MonitorSchedule).filter(MonitorSchedule.enabled == "true").all()
        for s in schedules:
            cadence = float(s.cadence_minutes or 1440) * 60
            last = s.last_run_at
            if last is None:
                run_monitor.delay(str(s.id))
                continue
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if (now - last).total_seconds() >= cadence:
                run_monitor.delay(str(s.id))
    finally:
        db.close()
