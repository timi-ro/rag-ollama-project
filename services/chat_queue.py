import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Literal, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

ChatJobStatus = Literal["queued", "processing", "done", "failed"]

JOB_TTL_SECONDS = 3600  # keep completed/failed jobs for 1 hour


@dataclass
class ChatJob:
    job_id: str
    site_id: int
    question: str
    conversation_history: list
    status: ChatJobStatus = "queued"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[dict] = None
    error: Optional[str] = None


_jobs: dict[str, ChatJob] = {}
_queue: asyncio.Queue = asyncio.Queue()


def _purge_expired():
    now = time.time()
    expired = [
        jid for jid, job in _jobs.items()
        if job.status in ("done", "failed")
        and job.completed_at
        and now - job.completed_at > JOB_TTL_SECONDS
    ]
    for jid in expired:
        del _jobs[jid]


def create_job(site_id: int, question: str, conversation_history: list) -> ChatJob:
    _purge_expired()
    job_id = "cj_" + uuid.uuid4().hex[:12]
    job = ChatJob(
        job_id=job_id,
        site_id=site_id,
        question=question,
        conversation_history=conversation_history,
    )
    _jobs[job_id] = job
    _queue.put_nowait(job)
    return job


def get_job(job_id: str, site_id: int) -> Optional[ChatJob]:
    job = _jobs.get(job_id)
    if job is None or job.site_id != site_id:
        return None
    return job


async def run_worker(process_fn: Callable[["ChatJob"], Awaitable[dict]]):
    """Long-running background coroutine — launch once at app startup."""
    while True:
        job = await _queue.get()
        if job.status != "queued":
            _queue.task_done()
            continue
        job.status = "processing"
        job.started_at = time.time()
        try:
            job.result = await process_fn(job)
            job.status = "done"
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            logger.exception("Chat job %s failed: %s", job.job_id, exc)
        finally:
            job.completed_at = time.time()
            _queue.task_done()