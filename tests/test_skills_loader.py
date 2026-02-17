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


def test_get_always_skills_prefers_nanobot_metadata_over_openclaw(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "dual-metadata-skill",
        '{"nanobot":{"always":false},"openclaw":{"always":true}}',
    )
    loader = SkillsLoader(tmp_path, builtin_skills_dir=tmp_path / "_no_builtin_skills")

    always_skills = loader.get_always_skills()

    assert always_skills == []
