import json
import pathlib
import time

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


async def test_on_timer_runs_due_jobs(tmp_path) -> None:
    """_on_timer executes jobs whose next_run_at_ms is in the past."""
    store_path = tmp_path / "cron" / "jobs.json"
    service = CronService(store_path)
    service._running = True

    executed: list[str] = []

    async def on_job(job):
        executed.append(job.name)

    service.on_job = on_job

    service.add_job(
        name="overdue job",
        schedule=CronSchedule(kind="every", every_ms=60_000),
        message="tick",
    )
    # Force next run into the past
    service._store.jobs[0].state.next_run_at_ms = int(time.time() * 1000) - 5_000

    await service._on_timer()

    assert "overdue job" in executed


async def test_on_timer_re_arms_after_save_store_oserror(tmp_path, monkeypatch) -> None:
    """_arm_timer is called even when _save_store raises OSError (e.g. disk full).

    In Python 3.14, Path.write_text() is distinct from Path.stat(), so patching
    Path.write_text only affects the explicit write inside _save_store.
    """
    store_path = tmp_path / "cron" / "jobs.json"
    service = CronService(store_path)
    service._running = True

    # Seed an overdue job directly so _on_timer has something to execute and save
    overdue_ms = int(time.time() * 1000) - 5_000
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps({
        "version": 1,
        "jobs": [{
            "id": "testjob1",
            "name": "overdue",
            "enabled": True,
            "schedule": {"kind": "every", "atMs": None, "everyMs": 60_000, "expr": None, "tz": None},
            "payload": {"kind": "agent_turn", "message": "tick", "deliver": False, "channel": None, "to": None},
            "state": {"nextRunAtMs": overdue_ms, "lastRunAtMs": None, "lastStatus": None, "lastError": None},
            "createdAtMs": overdue_ms,
            "updatedAtMs": overdue_ms,
            "deleteAfterRun": False,
        }],
    }))
    service._load_store()

    # Make write_text fail to simulate disk-full or permission error
    _real_write_text = pathlib.Path.write_text

    def write_text_raises(self, *args, **kwargs):
        if self == store_path:
            raise OSError("injected disk full")
        return _real_write_text(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "write_text", write_text_raises)

    await service._on_timer()

    # Timer must still be armed — the cron loop must survive a save failure
    assert service._timer_task is not None
    service.stop()


async def test_on_external_change_reloads_store(tmp_path) -> None:
    """_on_external_change reloads the in-memory store from disk."""
    store_path = tmp_path / "cron" / "jobs.json"
    service = CronService(store_path)
    service._running = True
    service._load_store()  # primes empty in-memory store

    # Write a job to disk simulating external CLI add
    job_ms = int(time.time() * 1000) + 60_000
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps({
        "version": 1,
        "jobs": [{
            "id": "ext1",
            "name": "external job",
            "enabled": True,
            "schedule": {"kind": "every", "atMs": None, "everyMs": 3_600_000, "expr": None, "tz": None},
            "payload": {"kind": "agent_turn", "message": "tick", "deliver": False, "channel": None, "to": None},
            "state": {"nextRunAtMs": job_ms, "lastRunAtMs": None, "lastStatus": None, "lastError": None},
            "createdAtMs": job_ms,
            "updatedAtMs": job_ms,
            "deleteAfterRun": False,
        }],
    }))

    # Simulate watchdog notification
    service._on_external_change()
    service.stop()

    assert len(service.list_jobs()) == 1
    assert service.list_jobs()[0].name == "external job"
