# GitHub Issue & PR Templates Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add three issue templates (Bug, Feature, Upstream-Intake) and one PR template with a type selector to `.github/`.

**Architecture:** Static Markdown files with YAML front matter for issue templates; a single Markdown file for the PR template. No Python code changes. A `config.yml` disables blank issues. An `upstream` label must be created on GitHub before the upstream-intake template can use it.

**Tech Stack:** GitHub issue/PR templates (Markdown + YAML front matter), `gh` CLI

---

### Task 1: Create `upstream` label on GitHub

**Files:** none (GitHub label via API)

**Step 1: Create the label**

```bash
gh label create upstream \
  --repo Athemis/nanobot-redux \
  --description "Upstream intake candidate or tracking issue" \
  --color "0075ca"
```

Expected: `✓ Label "upstream" created`

**Step 2: Verify**

```bash
gh label list --repo Athemis/nanobot-redux --json name --jq '.[].name' | grep upstream
```

Expected: `upstream`

---

### Task 2: Create issue template config

**Files:**
- Create: `.github/ISSUE_TEMPLATE/config.yml`

**Step 1: Create the file**

```yaml
blank_issues_enabled: false
contact_links:
  - name: Upstream PR tracker
    url: https://github.com/HKUDS/nanobot/pulls
    about: Browse upstream PRs to find intake candidates
```

**Step 2: Verify YAML parses**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/ISSUE_TEMPLATE/config.yml'))" && echo OK
```

Expected: `OK`

**Step 3: Commit**

```bash
git add .github/ISSUE_TEMPLATE/config.yml
git commit -S -m "chore(github): add issue template config"
```

---

### Task 3: Create Bug issue template

**Files:**
- Create: `.github/ISSUE_TEMPLATE/bug.md`

**Step 1: Create the file**

```markdown
---
name: Bug report
about: Something is broken or behaving unexpectedly
labels: bug
---

## Description

<!-- What is broken? -->

## Steps to reproduce

1.
2.
3.

## Expected behavior

## Actual behavior

## Environment

- Python version: <!-- e.g. 3.14.0 -->
- Platform: <!-- e.g. Linux x86_64 -->
- Install method: <!-- pip install / editable / docker -->

## Logs

<details>
<summary>Relevant output</summary>

```
paste here
```

</details>
```

**Step 2: Verify front matter**

```bash
python3 -c "
import re, sys
content = open('.github/ISSUE_TEMPLATE/bug.md').read()
match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
assert match, 'no front matter'
import yaml; yaml.safe_load(match.group(1))
print('OK')
"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add .github/ISSUE_TEMPLATE/bug.md
git commit -S -m "chore(github): add bug issue template"
```

---

### Task 4: Create Feature/Enhancement issue template

**Files:**
- Create: `.github/ISSUE_TEMPLATE/feature.md`

**Step 1: Create the file**

```markdown
---
name: Feature / Enhancement
about: Propose new functionality or an improvement
labels: enhancement
---

## Problem / motivation

<!-- What gap or friction does this address? -->

## Proposed solution

## Alternatives considered

<!-- Other approaches you ruled out, and why -->

---

> Before opening, check that the idea fits the fork's goals: [`docs/redux-manifest.md`](../docs/redux-manifest.md).
```

**Step 2: Verify front matter**

```bash
python3 -c "
import re, sys
content = open('.github/ISSUE_TEMPLATE/feature.md').read()
match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
assert match, 'no front matter'
import yaml; yaml.safe_load(match.group(1))
print('OK')
"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add .github/ISSUE_TEMPLATE/feature.md
git commit -S -m "chore(github): add feature issue template"
```

---

### Task 5: Create Upstream-Intake issue template

**Files:**
- Create: `.github/ISSUE_TEMPLATE/upstream-intake.md`

**Step 1: Create the file**

```markdown
---
name: Upstream intake
about: Track adoption, deferral, or rejection of an upstream change
labels: upstream
---

## Upstream reference

<!-- Link to the upstream PR or commit, e.g. https://github.com/HKUDS/nanobot/pull/123 -->

## What it does

<!-- One paragraph summary of the upstream change -->

## Why relevant for redux

<!-- How does it fit the fork's goals? See docs/redux-manifest.md -->

## Known risks

<!-- Dependencies added, breaking changes, areas without test coverage -->

## Decision

- [ ] Adopt
- [ ] Defer — reason:
- [ ] Reject — reason:

---

> Follow the intake workflow in [`docs/upstream-intake.md`](../docs/upstream-intake.md).
```

**Step 2: Verify front matter**

```bash
python3 -c "
import re, sys
content = open('.github/ISSUE_TEMPLATE/upstream-intake.md').read()
match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
assert match, 'no front matter'
import yaml; yaml.safe_load(match.group(1))
print('OK')
"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add .github/ISSUE_TEMPLATE/upstream-intake.md
git commit -S -m "chore(github): add upstream-intake issue template"
```

---

### Task 6: Create PR template

**Files:**
- Create: `.github/pull_request_template.md`

**Step 1: Create the file**

```markdown
## Type

- [ ] Feature
- [ ] Bugfix
- [ ] Upstream-Intake

## Summary

<!-- 2-3 bullets describing what changed and why -->

-
-

## Test plan

- [ ] `pytest` passes
- [ ] `ruff check .` passes
- [ ] Relevant tests added or updated

## Upstream-Intake only

<!-- Fill in this section only for Upstream-Intake PRs. Delete otherwise. -->

**Upstream SHA / PR:** <!-- e.g. https://github.com/HKUDS/nanobot/pull/123 -->

- [ ] Entry added to `docs/upstream-log.md`
- [ ] Entry added to `docs/redux-changes.md` (if fork-specific adaptation)
```

**Step 2: Verify file exists and is non-empty**

```bash
test -s .github/pull_request_template.md && echo OK
```

Expected: `OK`

**Step 3: Commit**

```bash
git add .github/pull_request_template.md
git commit -S -m "chore(github): add PR template"
```

---

### Task 7: Push and verify on GitHub

**Step 1: Push**

```bash
git push
```

**Step 2: Verify issue picker on GitHub**

Open: `https://github.com/Athemis/nanobot-redux/issues/new/choose`

Expected: Three template cards (Bug report, Feature / Enhancement, Upstream intake) and no blank-issue option.

**Step 3: Remove docs/plans (ephemeral)**

```bash
git rm -r docs/plans/
git commit -S -m "chore: remove ephemeral template plan docs"
git push
```
