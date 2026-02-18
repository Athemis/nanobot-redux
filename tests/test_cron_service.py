import json
import pathlib
import time
import uuid

import pytest

from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule


def test_add_job_rejects_unknown_timezone(tmp_path) -> None:
    """Reject invalid IANA tz names and avoid persisting dead cron jobs."""
    service = CronService(tmp_path / "cron" / "jobs.json")

    with pytest.raises(ValueError, match="unknown timezone 'America/Vancovuer'"):
        service.add_job(
            name="tz typo",
            schedule=CronSchedule(kind="cron", expr="0 9 * * *", tz="America/Vancovuer"),
            message="hello",
        )

    assert service.list_jobs(include_disabled=True) == []


def test_add_job_accepts_valid_timezone(tmp_path) -> None:
    """Accept valid IANA tz names and compute an initial next run."""
    service = CronService(tmp_path / "cron" / "jobs.json")

    job = service.add_job(
        name="tz ok",
        schedule=CronSchedule(kind="cron", expr="0 9 * * *", tz="America/Vancouver"),
        message="hello",
    )

    assert job.schedule.tz == "America/Vancouver"
    assert job.state.next_run_at_ms is not None


def test_check_disk_changes_reloads_when_file_is_newer(tmp_path) -> None:
    """_check_disk_changes reloads in-memory store when the file has been updated externally."""
    store_path = tmp_path / "cron" / "jobs.json"
    service = CronService(store_path)
    service._load_store()  # prime with empty store (file does not exist yet → _store_mtime = 0.0)

    # Simulate external write: a second instance (CLI) adds a job
    service2 = CronService(store_path)
    service2.add_job(
        name="external job",
        schedule=CronSchedule(kind="every", every_ms=3_600_000),
        message="tick",
    )

    # File is now newer than what service knows about
    service._check_disk_changes()

    assert len(service.list_jobs()) == 1
    assert service.list_jobs()[0].name == "external job"


def test_check_disk_changes_noop_when_file_unchanged(tmp_path) -> None:
    """_check_disk_changes does not reload when the file mtime has not changed."""
    store_path = tmp_path / "cron" / "jobs.json"
    service = CronService(store_path)
    service.add_job(
        name="my job",
        schedule=CronSchedule(kind="every", every_ms=3_600_000),
        message="tick",
    )

    store_before = service._store

    # No external changes — mtime still matches
    service._check_disk_changes()

    assert service._store is store_before  # same object, no reload


async def test_on_timer_picks_up_externally_added_jobs(tmp_path) -> None:
    """_on_timer reloads the store from disk and executes overdue jobs added externally."""
    store_path = tmp_path / "cron" / "jobs.json"
    service = CronService(store_path)
    service._running = True
    service._load_store()  # empty store, primes _store_mtime = 0.0

    executed: list[str] = []

    async def on_job(job):
        executed.append(job.name)

    service.on_job = on_job

    # Write an overdue job directly to disk (simulating CLI add while gateway runs)
    overdue_ms = int(time.time() * 1000) - 5_000
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps({
        "version": 1,
        "jobs": [{
            "id": str(uuid.uuid4())[:8],
            "name": "overdue job",
            "enabled": True,
            "schedule": {"kind": "every", "atMs": None, "everyMs": 60_000, "expr": None, "tz": None},
            "payload": {"kind": "agent_turn", "message": "tick", "deliver": False, "channel": None, "to": None},
            "state": {"nextRunAtMs": overdue_ms, "lastRunAtMs": None, "lastStatus": None, "lastError": None},
            "createdAtMs": overdue_ms,
            "updatedAtMs": overdue_ms,
            "deleteAfterRun": False,
        }],
    }))

    await service._on_timer()

    assert "overdue job" in executed


async def test_arm_timer_creates_poll_task_when_no_jobs(tmp_path) -> None:
    """_arm_timer schedules a timer even with no jobs so disk changes are polled."""
    service = CronService(tmp_path / "cron" / "jobs.json")
    service._running = True
    service._load_store()  # empty store

    service._arm_timer()

    assert service._timer_task is not None
    assert not service._timer_task.done()
    service.stop()


def test_load_store_preserves_jobs_on_stat_error(tmp_path, monkeypatch) -> None:
    """Jobs survive _load_store even when stat() raises during mtime tracking.

    In Python 3.14, Path.exists() uses os.path.exists(), not Path.stat(), so
    patching Path.stat only affects the explicit stat() call inside _load_store.
    """
    store_path = tmp_path / "cron" / "jobs.json"

    seeder = CronService(store_path)
    seeder.add_job(name="canary", schedule=CronSchedule(kind="every", every_ms=3_600_000), message="tick")

    service = CronService(store_path)

    _real_stat = pathlib.Path.stat

    def stat_raises_for_store(self, **kwargs):
        if self == store_path:
            raise OSError("injected stat failure")
        return _real_stat(self, **kwargs)

    monkeypatch.setattr(pathlib.Path, "stat", stat_raises_for_store)

    store = service._load_store()

    assert len(store.jobs) == 1
    assert store.jobs[0].name == "canary"
