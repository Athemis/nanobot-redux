import json
import pathlib
import time
import uuid

import pytest

from nanobot.cron.service import CronService, _compute_next_run
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


@pytest.mark.asyncio
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
    store_path.write_text(
        json.dumps(
            {
                "version": 1,
                "jobs": [
                    {
                        "id": str(uuid.uuid4())[:8],
                        "name": "overdue job",
                        "enabled": True,
                        "schedule": {
                            "kind": "every",
                            "atMs": None,
                            "everyMs": 60_000,
                            "expr": None,
                            "tz": None,
                        },
                        "payload": {
                            "kind": "agent_turn",
                            "message": "tick",
                            "deliver": False,
                            "channel": None,
                            "to": None,
                        },
                        "state": {
                            "nextRunAtMs": overdue_ms,
                            "lastRunAtMs": None,
                            "lastStatus": None,
                            "lastError": None,
                        },
                        "createdAtMs": overdue_ms,
                        "updatedAtMs": overdue_ms,
                        "deleteAfterRun": False,
                    }
                ],
            }
        )
    )

    await service._on_timer()

    assert "overdue job" in executed


@pytest.mark.asyncio
async def test_arm_timer_creates_poll_task_when_no_jobs(tmp_path) -> None:
    """_arm_timer schedules a timer even with no jobs so disk changes are polled."""
    service = CronService(tmp_path / "cron" / "jobs.json")
    service._running = True
    service._load_store()  # empty store

    service._arm_timer()

    assert service._timer_task is not None
    assert not service._timer_task.done()
    service.stop()


@pytest.mark.asyncio
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
    store_path.write_text(
        json.dumps(
            {
                "version": 1,
                "jobs": [
                    {
                        "id": "testjob1",
                        "name": "overdue",
                        "enabled": True,
                        "schedule": {
                            "kind": "every",
                            "atMs": None,
                            "everyMs": 60_000,
                            "expr": None,
                            "tz": None,
                        },
                        "payload": {
                            "kind": "agent_turn",
                            "message": "tick",
                            "deliver": False,
                            "channel": None,
                            "to": None,
                        },
                        "state": {
                            "nextRunAtMs": overdue_ms,
                            "lastRunAtMs": None,
                            "lastStatus": None,
                            "lastError": None,
                        },
                        "createdAtMs": overdue_ms,
                        "updatedAtMs": overdue_ms,
                        "deleteAfterRun": False,
                    }
                ],
            }
        )
    )
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


def test_load_store_preserves_jobs_on_stat_error(tmp_path, monkeypatch) -> None:
    """Jobs survive _load_store even when stat() raises during mtime tracking.

    In Python 3.14, Path.exists() uses os.path.exists(), not Path.stat(), so
    patching Path.stat only affects the explicit stat() call inside _load_store.
    """
    store_path = tmp_path / "cron" / "jobs.json"

    seeder = CronService(store_path)
    seeder.add_job(
        name="canary", schedule=CronSchedule(kind="every", every_ms=3_600_000), message="tick"
    )

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


# ===== Additional coverage tests =====


def test_load_store_creates_fresh_store_when_file_missing(tmp_path) -> None:
    """_load_store returns an empty CronStore when the file does not exist."""
    service = CronService(tmp_path / "nonexistent_dir" / "jobs.json")
    store = service._load_store()
    assert store.jobs == []


def test_load_store_handles_corrupt_json(tmp_path) -> None:
    """_load_store returns an empty CronStore when JSON is invalid."""
    store_path = tmp_path / "jobs.json"
    store_path.write_text("{not valid json!!!}")
    service = CronService(store_path)
    store = service._load_store()
    assert store.jobs == []


def test_save_store_creates_parent_dirs(tmp_path) -> None:
    """_save_store creates missing parent directories before writing."""
    store_path = tmp_path / "nested" / "deep" / "jobs.json"
    service = CronService(store_path)
    service.add_job("j", CronSchedule(kind="every", every_ms=1000), "msg")
    assert store_path.exists()


def test_list_jobs_excludes_disabled_by_default(tmp_path) -> None:
    """list_jobs() without include_disabled should not return disabled jobs."""
    service = CronService(tmp_path / "jobs.json")
    job = service.add_job("j", CronSchedule(kind="every", every_ms=1000), "msg")
    service.enable_job(job.id, enabled=False)
    assert service.list_jobs(include_disabled=False) == []
    assert len(service.list_jobs(include_disabled=True)) == 1


def test_list_jobs_returns_sorted_by_next_run(tmp_path) -> None:
    """list_jobs() returns jobs sorted by next_run_at_ms ascending."""
    service = CronService(tmp_path / "jobs.json")
    # Add two jobs; every_ms=1000 will have a sooner next run than every_ms=100000
    service.add_job("slow", CronSchedule(kind="every", every_ms=100_000), "msg")
    service.add_job("fast", CronSchedule(kind="every", every_ms=1_000), "msg")
    jobs = service.list_jobs(include_disabled=True)
    assert len(jobs) == 2
    # fast has shorter interval so its next_run_at_ms is smaller (first in sorted list)
    assert jobs[0].name == "fast"


def test_list_jobs_include_disabled_true_returns_all(tmp_path) -> None:
    """list_jobs(include_disabled=True) returns both enabled and disabled jobs."""
    service = CronService(tmp_path / "jobs.json")
    job = service.add_job("j", CronSchedule(kind="every", every_ms=1000), "msg")
    service.enable_job(job.id, enabled=False)
    all_jobs = service.list_jobs(include_disabled=True)
    assert len(all_jobs) == 1
    assert all_jobs[0].id == job.id


def test_remove_job_not_found(tmp_path) -> None:
    """remove_job returns False when the job ID does not exist."""
    service = CronService(tmp_path / "jobs.json")
    assert service.remove_job("nonexistent") is False


def test_remove_job_delete_after_run(tmp_path) -> None:
    """Jobs with delete_after_run=True can be removed directly via remove_job."""
    future_ms = int(time.time() * 1000) + 60_000
    service = CronService(tmp_path / "jobs.json")
    job = service.add_job(
        "once",
        CronSchedule(kind="at", at_ms=future_ms),
        "msg",
        delete_after_run=True,
    )
    assert len(service.list_jobs(include_disabled=True)) == 1
    removed = service.remove_job(job.id)
    assert removed is True
    assert service.list_jobs(include_disabled=True) == []


def test_enable_job_not_found(tmp_path) -> None:
    """enable_job returns None when the job ID does not exist."""
    service = CronService(tmp_path / "jobs.json")
    assert service.enable_job("nonexistent") is None


def test_enable_job_disable(tmp_path) -> None:
    """enable_job sets enabled=False and clears next_run_at_ms."""
    service = CronService(tmp_path / "jobs.json")
    job = service.add_job("j", CronSchedule(kind="every", every_ms=1000), "msg")
    result = service.enable_job(job.id, enabled=False)
    assert result is not None
    assert result.enabled is False
    assert result.state.next_run_at_ms is None


def test_enable_job_re_enable(tmp_path) -> None:
    """enable_job re-enables a disabled job and recomputes next_run_at_ms."""
    service = CronService(tmp_path / "jobs.json")
    job = service.add_job("j", CronSchedule(kind="every", every_ms=1000), "msg")
    service.enable_job(job.id, enabled=False)
    result = service.enable_job(job.id, enabled=True)
    assert result is not None
    assert result.enabled is True
    assert result.state.next_run_at_ms is not None


def test_update_next_run_for_every_schedule(tmp_path) -> None:
    """Every-schedule jobs get a next_run_at_ms set after add."""
    service = CronService(tmp_path / "jobs.json")
    job = service.add_job("j", CronSchedule(kind="every", every_ms=5000), "msg")
    assert job.state.next_run_at_ms is not None
    assert job.state.next_run_at_ms > int(time.time() * 1000)


def test_update_next_run_for_cron_schedule(tmp_path) -> None:
    """Cron-expression jobs get a next_run_at_ms set after add."""
    service = CronService(tmp_path / "jobs.json")
    job = service.add_job("j", CronSchedule(kind="cron", expr="0 9 * * *"), "msg")
    assert job.state.next_run_at_ms is not None


def test_update_next_run_for_at_schedule(tmp_path) -> None:
    """One-shot 'at' jobs get next_run_at_ms equal to the provided at_ms."""
    future_ms = int(time.time() * 1000) + 3_600_000
    service = CronService(tmp_path / "jobs.json")
    job = service.add_job("j", CronSchedule(kind="at", at_ms=future_ms), "msg")
    assert job.state.next_run_at_ms == future_ms


def test_update_next_run_at_in_past_returns_none(tmp_path) -> None:
    """One-shot 'at' jobs with a past timestamp compute next_run_at_ms as None."""
    past_ms = int(time.time() * 1000) - 5_000
    service = CronService(tmp_path / "jobs.json")
    job = service.add_job("j", CronSchedule(kind="at", at_ms=past_ms), "msg")
    assert job.state.next_run_at_ms is None


def test_compute_next_run_every_ms_zero_returns_none() -> None:
    """Every-schedule with every_ms=0 yields next_run_at_ms=None."""
    result = _compute_next_run(CronSchedule(kind="every", every_ms=0), int(time.time() * 1000))
    assert result is None


def test_compute_next_run_at_none_returns_none() -> None:
    """_compute_next_run returns None for an 'at' schedule with at_ms=None."""
    result = _compute_next_run(CronSchedule(kind="at", at_ms=None), int(time.time() * 1000))
    assert result is None


def test_compute_next_run_cron_bad_expr() -> None:
    """_compute_next_run returns None (and logs warning) for an invalid cron expr."""
    result = _compute_next_run(
        CronSchedule(kind="cron", expr="not a cron expr"),
        int(time.time() * 1000),
    )
    assert result is None


def test_compute_next_run_cron_no_expr() -> None:
    """_compute_next_run returns None when cron kind has no expr."""
    result = _compute_next_run(CronSchedule(kind="cron", expr=None), int(time.time() * 1000))
    assert result is None


@pytest.mark.asyncio
async def test_run_job_disabled_without_force(tmp_path) -> None:
    """run_job returns False for a disabled job without force=True."""
    service = CronService(tmp_path / "jobs.json")
    job = service.add_job("j", CronSchedule(kind="every", every_ms=1000), "msg")
    service.enable_job(job.id, enabled=False)
    result = await service.run_job(job.id, force=False)
    assert result is False


@pytest.mark.asyncio
async def test_run_job_disabled_with_force(tmp_path) -> None:
    """run_job executes a disabled job when force=True."""
    executed: list[str] = []

    async def on_job(job):
        executed.append(job.name)

    service = CronService(tmp_path / "jobs.json", on_job=on_job)
    job = service.add_job("j", CronSchedule(kind="every", every_ms=1000), "msg")
    service.enable_job(job.id, enabled=False)
    result = await service.run_job(job.id, force=True)
    assert result is True
    assert "j" in executed


@pytest.mark.asyncio
async def test_run_job_not_found(tmp_path) -> None:
    """run_job returns False when the job ID does not exist."""
    service = CronService(tmp_path / "jobs.json")
    result = await service.run_job("nonexistent")
    assert result is False


@pytest.mark.asyncio
async def test_execute_job_sets_last_status_ok(tmp_path) -> None:
    """_execute_job sets last_status='ok' on success."""
    executed: list[str] = []

    async def on_job(job):
        executed.append(job.id)

    service = CronService(tmp_path / "jobs.json", on_job=on_job)
    job = service.add_job("j", CronSchedule(kind="every", every_ms=1000), "msg")
    await service._execute_job(job)
    assert job.state.last_status == "ok"
    assert job.id in executed


@pytest.mark.asyncio
async def test_execute_job_sets_last_status_error(tmp_path) -> None:
    """_execute_job sets last_status='error' when on_job raises."""

    async def failing_on_job(job):
        raise RuntimeError("boom")

    service = CronService(tmp_path / "jobs.json", on_job=failing_on_job)
    job = service.add_job("j", CronSchedule(kind="every", every_ms=1000), "msg")
    await service._execute_job(job)
    assert job.state.last_status == "error"
    assert "boom" in job.state.last_error


@pytest.mark.asyncio
async def test_execute_job_at_schedule_disables_job(tmp_path) -> None:
    """_execute_job disables an 'at' job (without delete_after_run) after execution."""
    future_ms = int(time.time() * 1000) + 60_000
    service = CronService(tmp_path / "jobs.json")
    job = service.add_job(
        "once", CronSchedule(kind="at", at_ms=future_ms), "msg", delete_after_run=False
    )
    await service._execute_job(job)
    assert job.enabled is False
    assert job.state.next_run_at_ms is None


@pytest.mark.asyncio
async def test_execute_job_at_schedule_delete_after_run(tmp_path) -> None:
    """_execute_job removes an 'at' job with delete_after_run=True from the store."""
    future_ms = int(time.time() * 1000) + 60_000
    service = CronService(tmp_path / "jobs.json")
    job = service.add_job(
        "once", CronSchedule(kind="at", at_ms=future_ms), "msg", delete_after_run=True
    )
    assert len(service.list_jobs(include_disabled=True)) == 1
    await service._execute_job(job)
    assert service.list_jobs(include_disabled=True) == []


@pytest.mark.asyncio
async def test_schedule_loop_guard_not_running(tmp_path) -> None:
    """_arm_timer does nothing when _running is False."""
    service = CronService(tmp_path / "jobs.json")
    service._running = False
    service._load_store()
    service._arm_timer()
    assert service._timer_task is None


@pytest.mark.asyncio
async def test_start_and_stop(tmp_path) -> None:
    """start() sets _running=True and creates a timer; stop() cancels it."""
    service = CronService(tmp_path / "jobs.json")
    await service.start()
    assert service._running is True
    assert service._timer_task is not None
    service.stop()
    assert service._running is False
    assert service._timer_task is None


def test_status_returns_expected_keys(tmp_path) -> None:
    """status() returns a dict with 'enabled', 'jobs', and 'next_wake_at_ms'."""
    service = CronService(tmp_path / "jobs.json")
    s = service.status()
    assert "enabled" in s
    assert "jobs" in s
    assert "next_wake_at_ms" in s
