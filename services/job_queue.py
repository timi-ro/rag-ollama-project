import asyncio
import json
import logging
import os
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Literal, Callable, Awaitable, Optional

logger = logging.getLogger(__name__)

JobStatus = Literal["queued", "processing", "done", "failed"]

JOB_TTL_SECONDS = 3600  # completed/failed jobs are cleaned up after 1 hour


@dataclass
class UploadJob:
    job_id: str
    site_id: int
    site_plan: str
    tmp_path: str
    ext: str
    filename: str
    status: JobStatus = "queued"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[dict] = None
    error: Optional[str] = None


_jobs: dict[str, UploadJob] = {}
_queue: asyncio.Queue = asyncio.Queue()
_pending_ids: list[str] = []          # ordered list of queued job_ids (for position tracking)
_recent_durations: deque = deque(maxlen=20)  # rolling window of processing times for ETA


def _sync_to_db(job: "UploadJob"):
    """Write the current job state to SQLite."""
    from models.database import SessionLocal, Job as JobModel
    with SessionLocal() as db:
        row = db.get(JobModel, job.job_id)
        if row is None:
            row = JobModel(job_id=job.job_id)
            db.add(row)
        row.site_id      = job.site_id
        row.site_plan    = job.site_plan
        row.tmp_path     = job.tmp_path
        row.ext          = job.ext
        row.filename     = job.filename
        row.status       = job.status
        row.created_at   = job.created_at
        row.started_at   = job.started_at
        row.completed_at = job.completed_at
        row.result       = json.dumps(job.result) if job.result is not None else None
        row.error        = job.error
        db.commit()


def recover_jobs():
    """Called once at startup: re-queue pending jobs; mark orphaned processing jobs as failed."""
    from models.database import SessionLocal, Job as JobModel
    with SessionLocal() as db:
        for row in db.query(JobModel).filter(JobModel.status == "processing").all():
            row.status = "failed"
            row.error = "Server restarted while job was processing"
            row.completed_at = time.time()
        db.commit()

        pending = (
            db.query(JobModel)
            .filter(JobModel.status == "queued")
            .order_by(JobModel.created_at)
            .all()
        )
        for row in pending:
            if not row.tmp_path or not os.path.exists(row.tmp_path):
                row.status = "failed"
                row.error = "Temp file lost after server restart"
                row.completed_at = time.time()
                continue
            job = UploadJob(
                job_id=row.job_id,
                site_id=row.site_id,
                site_plan=row.site_plan,
                tmp_path=row.tmp_path,
                ext=row.ext,
                filename=row.filename,
                status="queued",
                created_at=row.created_at,
            )
            _jobs[job.job_id] = job
            _pending_ids.append(job.job_id)
            _queue.put_nowait(job)
        db.commit()


def _purge_expired():
    now = time.time()
    expired = [
        jid for jid, job in _jobs.items()
        if job.status in ("done", "failed")
        and job.completed_at
        and now - job.completed_at > JOB_TTL_SECONDS
    ]
    for jid in expired:
        job = _jobs.pop(jid)
        if job.tmp_path and os.path.exists(job.tmp_path):
            try:
                os.unlink(job.tmp_path)
            except OSError:
                pass


def queue_position(job_id: str) -> int:
    """Return 1-based position in the pending queue, or 0 if not queued."""
    try:
        return _pending_ids.index(job_id) + 1
    except ValueError:
        return 0


def eta_seconds(position: int) -> Optional[int]:
    """Estimated seconds until the job starts processing, based on rolling average."""
    if not _recent_durations or position == 0:
        return None
    avg = sum(_recent_durations) / len(_recent_durations)
    return round(avg * position)


def create_job(site_id: int, site_plan: str, tmp_path: str, ext: str, filename: str) -> UploadJob:
    _purge_expired()
    job_id = "j_" + uuid.uuid4().hex[:12]
    job = UploadJob(
        job_id=job_id,
        site_id=site_id,
        site_plan=site_plan,
        tmp_path=tmp_path,
        ext=ext,
        filename=filename,
    )
    _jobs[job_id] = job
    _pending_ids.append(job_id)
    _queue.put_nowait(job)
    _sync_to_db(job)
    return job


def get_job(job_id: str, site_id: int) -> Optional[UploadJob]:
    """Return the job only if it belongs to the requesting site.
    Falls back to the DB for completed/failed jobs not in the in-memory cache."""
    job = _jobs.get(job_id)
    if job is not None:
        return job if job.site_id == site_id else None
    from models.database import SessionLocal, Job as JobModel
    with SessionLocal() as db:
        row = db.get(JobModel, job_id)
    if row is None or row.site_id != site_id:
        return None
    return UploadJob(
        job_id=row.job_id,
        site_id=row.site_id,
        site_plan=row.site_plan,
        tmp_path=row.tmp_path,
        ext=row.ext,
        filename=row.filename,
        status=row.status,
        created_at=row.created_at or 0.0,
        started_at=row.started_at,
        completed_at=row.completed_at,
        result=json.loads(row.result) if row.result else None,
        error=row.error,
    )


def requeue_job(job_id: str, site_id: int) -> Optional[UploadJob]:
    """Re-queue a failed job for retry. Returns None if not found or not in failed state."""
    job = get_job(job_id, site_id)
    if job is None or job.status != "failed":
        return None
    job.status = "queued"
    job.error = None
    job.result = None
    job.started_at = None
    job.completed_at = None
    _pending_ids.append(job_id)
    _queue.put_nowait(job)
    _sync_to_db(job)
    return job


async def run_worker(process_fn: Callable[["UploadJob"], Awaitable[dict]]):
    """
    Long-running background coroutine — launch once at app startup.
    Processes one job at a time; the embed_semaphore inside process_fn
    further serialises the CPU-heavy embedding step.
    """
    while True:
        job = await _queue.get()

        # Remove from pending list as we start processing
        if job.job_id in _pending_ids:
            _pending_ids.remove(job.job_id)

        # Guard against a job that was somehow superseded
        if job.status != "queued":
            _queue.task_done()
            continue

        job.status = "processing"
        job.started_at = time.time()
        _sync_to_db(job)

        try:
            job.result = await process_fn(job)
            job.status = "done"
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            logger.exception("Upload job %s failed: %s", job.job_id, exc)
        finally:
            job.completed_at = time.time()
            _sync_to_db(job)
            if job.started_at is not None:
                _recent_durations.append(job.completed_at - job.started_at)
            _queue.task_done()
            # Delete temp file on success.
            # On failure we keep it so the client can retry without re-uploading.
            if job.status == "done" and job.tmp_path and os.path.exists(job.tmp_path):
                try:
                    os.unlink(job.tmp_path)
                except OSError:
                    pass