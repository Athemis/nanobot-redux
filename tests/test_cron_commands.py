import json

from typer.testing import CliRunner

from nanobot.cli.commands import app

runner = CliRunner()


def test_cron_add_rejects_invalid_timezone(monkeypatch, tmp_path) -> None:
    """CLI should fail immediately for unknown cron timezones and not write jobs."""
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)

    result = runner.invoke(
        app,
        [
            "cron",
            "add",
            "--name",
            "demo",
            "--message",
            "hello",
            "--cron",
            "0 9 * * *",
            "--tz",
            "America/Vancovuer",
        ],
    )

    assert result.exit_code == 1
    assert "Error: unknown timezone 'America/Vancovuer'" in result.stdout
    assert not (tmp_path / "cron" / "jobs.json").exists()


def test_cron_add_skill_creates_skill_kind_job(monkeypatch, tmp_path) -> None:
    """--skill creates a job with kind='skill' and the skill name stored."""
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)

    result = runner.invoke(
        app,
        ["cron", "add", "--name", "weather-job", "--skill", "weather", "--every", "3600"],
    )

    assert result.exit_code == 0, result.stdout
    jobs_file = tmp_path / "cron" / "jobs.json"
    assert jobs_file.exists()
    data = json.loads(jobs_file.read_text())
    assert len(data["jobs"]) == 1
    payload = data["jobs"][0]["payload"]
    assert payload["kind"] == "skill"
    assert payload["skill"] == "weather"


def test_cron_add_requires_message_or_skill(monkeypatch, tmp_path) -> None:
    """CLI rejects a job that has neither --message nor --skill."""
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)

    result = runner.invoke(
        app,
        ["cron", "add", "--name", "empty-job", "--every", "3600"],
    )

    assert result.exit_code == 1
    assert "Must specify --message or --skill" in result.stdout


def test_cron_add_rejects_both_message_and_skill(monkeypatch, tmp_path) -> None:
    """CLI rejects a job that specifies both --message and --skill."""
    monkeypatch.setattr("nanobot.config.loader.get_data_dir", lambda: tmp_path)

    result = runner.invoke(
        app,
        [
            "cron",
            "add",
            "--name",
            "ambiguous-job",
            "--message",
            "hello",
            "--skill",
            "weather",
            "--every",
            "3600",
        ],
    )

    assert result.exit_code == 1
    assert "Cannot use both --message and --skill" in result.stdout
