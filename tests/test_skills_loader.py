from pathlib import Path

from nanobot.agent.skills import SkillsLoader


def _write_skill(workspace: Path, name: str, metadata_json: str) -> None:
    skill_dir = workspace / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"""---
description: {name}
metadata: '{metadata_json}'
---
Skill content.
""",
        encoding="utf-8",
    )


def test_get_always_skills_supports_openclaw_metadata(tmp_path: Path) -> None:
    _write_skill(tmp_path, "openclaw-skill", '{"openclaw":{"always":true}}')
    loader = SkillsLoader(tmp_path, builtin_skills_dir=tmp_path / "_no_builtin_skills")

    always_skills = loader.get_always_skills()

    assert always_skills == ["openclaw-skill"]


def test_build_skills_summary_workspace_only_excludes_builtin(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    builtin = tmp_path / "builtin"
    _write_skill(workspace, "ws-skill", "{}")
    _write_skill(builtin, "builtin-skill", "{}")
    loader = SkillsLoader(workspace, builtin_skills_dir=builtin)

    summary = loader.build_skills_summary(workspace_only=True)

    assert "ws-skill" in summary
    assert "builtin-skill" not in summary


def test_build_skills_summary_includes_builtin_by_default(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    builtin = tmp_path / "builtin"
    _write_skill(workspace, "ws-skill", "{}")
    _write_skill(builtin, "builtin-skill", "{}")
    loader = SkillsLoader(workspace, builtin_skills_dir=builtin)

    summary = loader.build_skills_summary()

    assert "ws-skill" in summary
    assert "builtin-skill" in summary


def test_get_always_skills_prefers_nanobot_metadata_over_openclaw(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "dual-metadata-skill",
        '{"nanobot":{"always":false},"openclaw":{"always":true}}',
    )
    loader = SkillsLoader(tmp_path, builtin_skills_dir=tmp_path / "_no_builtin_skills")

    always_skills = loader.get_always_skills()

    assert always_skills == []
