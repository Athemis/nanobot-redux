# GitHub Issue & PR Templates Design

**Date:** 2026-02-18
**Status:** Approved

## Goal

Add GitHub issue and PR templates to standardize contributions and reduce friction for the solo-maintainer workflow.

## Decisions

- **Issue templates:** Three separate files in `.github/ISSUE_TEMPLATE/` — GitHub renders these natively as a picker.
- **PR template:** Single `pull_request_template.md` with a type-selector checkbox (Feature / Bugfix / Upstream-Intake) and conditional sections below.
- **Language:** English (consistent with all docs and commit messages).
- **Tone:** Compact. Reference governance docs only where directly relevant.
- **Blank issues disabled** via `config.yml`; the config also links upstream PR tracker for upstream-intake candidates.

## File Structure

```
.github/
  ISSUE_TEMPLATE/
    bug.md
    feature.md
    upstream-intake.md
    config.yml
  pull_request_template.md
```

## Issue Templates

### bug.md
- Label: `bug`
- Fields: description, reproduction steps, expected vs actual behavior, environment (Python version, platform), optional logs

### feature.md
- Label: `enhancement`
- Fields: problem/motivation, proposed solution, alternatives considered
- Brief reference to `docs/redux-manifest.md`

### upstream-intake.md
- Label: `upstream`
- Fields: upstream PR/commit link, what it does, why relevant for redux, known risks
- Reference to `docs/upstream-intake.md`

## PR Template

Single file with:
1. Type selector at top: `[ ] Feature  [ ] Bugfix  [ ] Upstream-Intake`
2. Summary section (bullet points)
3. Test plan checklist
4. Upstream-intake section (upstream SHA, `docs/upstream-log.md` entry checkbox) — visually marked as "fill in for Upstream-Intake only"
