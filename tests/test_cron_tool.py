"""Tests for CronTool."""

import pytest

from nanobot.agent.tools.cron import CronTool
from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule


@pytest.fixture
def cron_service(tmp_path):
    return CronService(tmp_path / "jobs.json")


@pytest.fixture
def tool(cron_service):
    t = CronTool(cron_service)
    t.set_context("matrix", "!room123")
    return t


def test_name(tool):
    assert tool.name == "cron"


def test_description(tool):
    assert "schedule" in tool.description.lower() or "cron" in tool.description.lower()


def test_parameters(tool):
    params = tool.parameters
    assert "action" in params["properties"]


def test_parameters_required_action(tool):
    params = tool.parameters
    assert "action" in params["required"]


def test_set_context(cron_service):
    t = CronTool(cron_service)
    t.set_context("email", "user@example.com")
    assert t._channel == "email"
    assert t._chat_id == "user@example.com"


@pytest.mark.asyncio
async def test_execute_add_every(tool):
    result = await tool.execute("add", message="hello world", every_seconds=60)
    assert "Created job" in result


@pytest.mark.asyncio
async def test_execute_add_cron(tool):
    result = await tool.execute("add", message="daily check", cron_expr="0 9 * * *")
    assert "Created job" in result


@pytest.mark.asyncio
async def test_execute_add_at(tool):
    result = await tool.execute("add", message="one time", at="2030-01-01T10:00:00")
    assert "Created job" in result


@pytest.mark.asyncio
async def test_execute_add_no_message(tool):
    result = await tool.execute("add", message="")
    assert "Error" in result


@pytest.mark.asyncio
async def test_execute_add_no_context(cron_service):
    t = CronTool(cron_service)  # no set_context
    result = await t.execute("add", message="hello", every_seconds=60)
    assert "Error" in result


@pytest.mark.asyncio
async def test_execute_add_tz_without_cron(tool):
    result = await tool.execute("add", message="hello", every_seconds=60, tz="UTC")
    assert "Error" in result


@pytest.mark.asyncio
async def test_execute_add_invalid_tz(tool):
    result = await tool.execute("add", message="hello", cron_expr="0 9 * * *", tz="Invalid/Zone")
    assert "Error" in result


@pytest.mark.asyncio
async def test_execute_add_no_schedule(tool):
    result = await tool.execute("add", message="hello")
    assert "Error" in result


@pytest.mark.asyncio
async def test_execute_add_valid_tz_with_cron(tool):
    result = await tool.execute(
        "add", message="morning", cron_expr="0 9 * * *", tz="America/Vancouver"
    )
    assert "Created job" in result


@pytest.mark.asyncio
async def test_execute_add_cron_invalid_expr_creates_job_without_schedule(tool, cron_service):
    """An invalid cron expression is handled gracefully: job is created but next_run_at_ms is None."""
    # croniter raises internally but CronService catches it and sets next_run_at_ms=None
    result = await tool.execute("add", message="hello", cron_expr="not-a-cron")
    assert "Created job" in result
    jobs = cron_service.list_jobs(include_disabled=True)
    assert len(jobs) == 1
    assert jobs[0].state.next_run_at_ms is None


@pytest.mark.asyncio
async def test_execute_list_empty(tool):
    result = await tool.execute("list")
    assert "No scheduled jobs" in result


@pytest.mark.asyncio
async def test_execute_list_with_jobs(tool, cron_service):
    cron_service.add_job("my task", CronSchedule(kind="every", every_ms=60000), "run me")
    result = await tool.execute("list")
    assert "my task" in result


@pytest.mark.asyncio
async def test_execute_list_shows_job_id(tool, cron_service):
    job = cron_service.add_job("listed", CronSchedule(kind="every", every_ms=60000), "check")
    result = await tool.execute("list")
    assert job.id in result


@pytest.mark.asyncio
async def test_execute_remove_no_id(tool):
    result = await tool.execute("remove")
    assert "Error" in result


@pytest.mark.asyncio
async def test_execute_remove_not_found(tool):
    result = await tool.execute("remove", job_id="nonexistent")
    assert "not found" in result


@pytest.mark.asyncio
async def test_execute_remove_found(tool, cron_service):
    job = cron_service.add_job("j", CronSchedule(kind="every", every_ms=60000), "hello")
    result = await tool.execute("remove", job_id=job.id)
    assert "Removed" in result


@pytest.mark.asyncio
async def test_execute_remove_clears_job(tool, cron_service):
    """After remove, the job no longer appears in list."""
    job = cron_service.add_job("todelete", CronSchedule(kind="every", every_ms=60000), "bye")
    await tool.execute("remove", job_id=job.id)
    list_result = await tool.execute("list")
    assert "todelete" not in list_result


@pytest.mark.asyncio
async def test_execute_unknown_action(tool):
    result = await tool.execute("unknown_action")
    assert "Unknown action" in result


@pytest.mark.asyncio
async def test_execute_add_stores_job_in_service(tool, cron_service):
    """Adding a job via execute stores it persistently in the cron service."""
    result = await tool.execute("add", message="persisted task", every_seconds=120)
    assert "Created job" in result
    jobs = cron_service.list_jobs()
    assert len(jobs) == 1
    assert "persisted task" in jobs[0].payload.message


@pytest.mark.asyncio
async def test_execute_add_sets_deliver_flag(tool, cron_service):
    """Jobs added via CronTool have deliver=True to route responses back to the channel."""
    await tool.execute("add", message="deliver me", every_seconds=30)
    jobs = cron_service.list_jobs()
    assert jobs[0].payload.deliver is True


@pytest.mark.asyncio
async def test_execute_add_sets_channel_and_to(tool, cron_service):
    """Jobs added via CronTool capture the session channel and chat_id."""
    await tool.execute("add", message="context check", every_seconds=30)
    jobs = cron_service.list_jobs()
    assert jobs[0].payload.channel == "matrix"
    assert jobs[0].payload.to == "!room123"


@pytest.mark.asyncio
async def test_execute_add_at_sets_delete_after_run(tool, cron_service):
    """One-shot 'at' jobs have delete_after_run=True set automatically."""
    result = await tool.execute("add", message="one shot", at="2030-06-15T08:00:00")
    assert "Created job" in result
    jobs = cron_service.list_jobs()
    assert jobs[0].delete_after_run is True
