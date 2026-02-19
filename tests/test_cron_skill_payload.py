"""Tests for CronPayload kind='skill' — add_job, serialization, and dispatch."""

from pathlib import Path

from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule


def _make_service(tmp_path: Path) -> CronService:
    return CronService(tmp_path / "cron" / "jobs.json")


def test_add_job_with_skill_sets_kind(tmp_path: Path) -> None:
    """add_job(skill='weather') creates a job with kind='skill'."""
    svc = _make_service(tmp_path)
    schedule = CronSchedule(kind="every", every_ms=3600_000)

    job = svc.add_job(name="weather", schedule=schedule, skill="weather")

    assert job.payload.kind == "skill"
    assert job.payload.skill == "weather"
    assert job.payload.message == ""


def test_add_job_with_message_keeps_agent_turn(tmp_path: Path) -> None:
    """add_job(message='hello') keeps kind='agent_turn' unchanged."""
    svc = _make_service(tmp_path)
    schedule = CronSchedule(kind="every", every_ms=3600_000)

    job = svc.add_job(name="greet", schedule=schedule, message="hello")

    assert job.payload.kind == "agent_turn"
    assert job.payload.skill is None


def test_skill_payload_roundtrips_through_json(tmp_path: Path) -> None:
    """skill and kind fields survive a save/load cycle."""
    svc = _make_service(tmp_path)
    schedule = CronSchedule(kind="every", every_ms=3600_000)
    svc.add_job(name="news", schedule=schedule, skill="news-summary")

    # Force reload from disk
    svc2 = _make_service(tmp_path)
    jobs = svc2.list_jobs()

    assert len(jobs) == 1
    assert jobs[0].payload.kind == "skill"
    assert jobs[0].payload.skill == "news-summary"


def test_skill_payload_with_extra_message(tmp_path: Path) -> None:
    """message field is preserved alongside skill for additional context."""
    svc = _make_service(tmp_path)
    schedule = CronSchedule(kind="every", every_ms=3600_000)

    job = svc.add_job(
        name="weather-detailed",
        schedule=schedule,
        skill="weather",
        message="Duesseldorf",
    )

    assert job.payload.kind == "skill"
    assert job.payload.skill == "weather"
    assert job.payload.message == "Duesseldorf"


def test_existing_agent_turn_job_loads_without_skill_field(tmp_path: Path) -> None:
    """Existing jobs.json without a 'skill' key still deserializes correctly."""
    import json

    store_path = tmp_path / "cron" / "jobs.json"
    store_path.parent.mkdir(parents=True)
    store_path.write_text(json.dumps({
        "version": 1,
        "jobs": [{
            "id": "abc12345",
            "name": "legacy",
            "enabled": True,
            "schedule": {"kind": "every", "atMs": None, "everyMs": 3600000, "expr": None, "tz": None},
            "payload": {"kind": "agent_turn", "message": "hello", "deliver": False, "channel": None, "to": None},
            "state": {"nextRunAtMs": None, "lastRunAtMs": None, "lastStatus": None, "lastError": None},
            "createdAtMs": 0,
            "updatedAtMs": 0,
            "deleteAfterRun": False,
        }]
    }))

    svc = CronService(store_path)
    jobs = svc.list_jobs()

    assert len(jobs) == 1
    assert jobs[0].payload.skill is None
    assert jobs[0].payload.kind == "agent_turn"
