---
name: update-local-skills
description: Check and update locally installed Codex skills that are backed by Git repositories. Use when the user asks to update skills, sync local skills with GitHub, check whether installed skills are outdated, audit local skill versions, or create/run an automation that keeps ~/.codex/skills current.
---

# Update Local Skills

## Workflow

1. Locate this skill folder and run the bundled updater:

```bash
python3 /path/to/update-local-skills/scripts/update_local_skills.py --apply
```

2. If the user only asks for a status check, use:

```bash
python3 /path/to/update-local-skills/scripts/update_local_skills.py --check
```

3. Report the summary table: updated, already current, skipped, and failed repositories.

## Prompt Mode

If the user asks for an "automatic update prompt" or wants to decide each time, use the script's prompt controls:

```bash
python3 /path/to/update-local-skills/scripts/update_local_skills.py --enable-auto-prompt
python3 /path/to/update-local-skills/scripts/update_local_skills.py --prompt
python3 /path/to/update-local-skills/scripts/update_local_skills.py --disable-auto-prompt
```

When prompt mode is enabled, ask the user in chat before applying updates. Offer four choices: update now, check only, skip this time, or disable future prompts. If the user disables future prompts, run `--disable-auto-prompt`.

## Defaults

- Scan `${CODEX_HOME:-~/.codex}/skills`.
- Skip `.system` skills unless the user explicitly asks to include system skills.
- Skip plugin cache skills unless the user explicitly asks to include plugin-managed skills.
- Update only Git-backed skill directories.
- Use `git fetch` plus fast-forward only; never reset, rebase, merge with conflicts, or overwrite local edits.
- Skip dirty worktrees and report them as requiring manual review.

## Options

- Add `--root <path>` to scan a specific skills directory.
- Add `--include-system` to include `.system` under the selected skills root.
- Add `--include-plugin-cache` to also scan `${CODEX_HOME:-~/.codex}/plugins/cache`.
- Add `--json` when machine-readable output is useful.

## Startup Automation

Skills do not run automatically just because Codex starts. This skill can provide the update logic and the enable/disable state, but it cannot attach itself to Codex application launch without an external automation.

If the user asks for startup or scheduled updating, explain that Codex must be triggered by a user request or an external automation, then offer one of these options:

- Create a shell alias or script that the user runs manually.
- Create a cron/launchd-style job outside Codex.
- Create a Codex automation if the current environment supports automations.

Do not claim this skill can ask on every Codex launch unless an external automation has been configured.
