---
name: agent-skills-auto-updater
description: Check, prompt for, and safely update all locally installed Git-backed AI agent skills across Codex and other skill roots. Use when the user asks to update local skills, sync skills with GitHub, check whether installed skills are outdated, audit local skill versions, or create/run an automation that keeps local agent skills current.
---

# Agent Skills Auto Updater

## Workflow

1. Locate this skill folder and run the bundled updater:

```bash
python3 /path/to/agent-skills-auto-updater/scripts/agent_skills_auto_updater.py --apply
```

2. If the user only asks for a status check, use:

```bash
python3 /path/to/agent-skills-auto-updater/scripts/agent_skills_auto_updater.py --check
```

3. Report the summary table: updated, already current, skipped, and failed repositories.

## Install With Codex Automation

Skills do not have install-time hooks, so this skill cannot silently create a Codex automation merely by being cloned or copied. When the user asks to install this skill with Codex automation enabled, run the bundled installer helper:

```bash
python3 /path/to/agent-skills-auto-updater/scripts/install_codex_automation.py --print
```

The helper enables this skill's local prompt state and writes a ready-to-use Codex automation request to:

```text
~/.config/agent-skills-auto-updater/codex_automation_request.md
```

If the current environment exposes Codex automations, create or update a Codex automation from that generated request. Prefer updating an existing "Check local agent skills" automation instead of creating duplicates.

## Prompt Mode

If the user asks for an "automatic update prompt" or wants to decide each time, use the script's prompt controls:

```bash
python3 /path/to/agent-skills-auto-updater/scripts/agent_skills_auto_updater.py --enable-auto-prompt
python3 /path/to/agent-skills-auto-updater/scripts/agent_skills_auto_updater.py --prompt
python3 /path/to/agent-skills-auto-updater/scripts/agent_skills_auto_updater.py --disable-auto-prompt
```

When prompt mode is enabled, ask the user in chat before applying updates. Offer four choices: update now, check only, skip this time, or disable future prompts. If the user disables future prompts, run `--disable-auto-prompt`.

## Defaults

- Scan known local agent skill roots that exist, including Codex, Claude, Cursor, Gemini, OpenCode, and `~/ai-skills`.
- Skip `.system` skills unless the user explicitly asks to include system skills.
- Skip plugin cache skills unless the user explicitly asks to include plugin-managed skills.
- Update only Git-backed skill directories.
- Use `git fetch` plus fast-forward only; never reset, rebase, merge with conflicts, or overwrite local edits.
- Skip dirty worktrees and report them as requiring manual review.

## Options

- Add `--agent codex`, `--agent claude`, `--agent cursor`, `--agent gemini`, `--agent opencode`, or `--agent all` to choose known roots.
- Add `--root <path>` to scan a specific skills directory.
- Add `--include-system` to include `.system` under the selected skills root.
- Add `--include-plugin-cache` to also scan `${CODEX_HOME:-~/.codex}/plugins/cache`.
- Add `--list-roots` to show which roots would be scanned.
- Add `--json` when machine-readable output is useful.

## Startup Automation

Skills do not run automatically just because Codex starts. This skill can provide the update logic, an install helper, and the enable/disable state, but it cannot attach itself to Codex application launch without Codex automation or another external automation.

If the user asks for startup or scheduled updating, explain that Codex must be triggered by a user request or an external automation, then offer one of these options:

- Run `scripts/install_codex_automation.py --print`, then create a Codex automation from the generated request if the current environment supports automations.
- Create a shell alias or script that the user runs manually.
- Create a cron/launchd-style job outside Codex.

Do not claim this skill can ask on every Codex launch unless Codex provides a launch trigger or another external automation has been configured. Current Codex automations should be treated as scheduled recurring runs, not as guaranteed app-launch hooks.
