#!/usr/bin/env python3
"""Prepare a Codex automation prompt for this skill.

Codex automations are created through the Codex app, not by a skill install hook.
This helper makes installation repeatable by enabling this skill's local prompt
state and writing a ready-to-use automation request that Codex can turn into an
automation with its automation tool.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from textwrap import dedent


DEFAULT_NAME = "Check local agent skills"
DEFAULT_WORKSPACE = "/Users/cap/Desktop/Skk/skills"


def config_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")).expanduser()
    return base / "agent-skills-auto-updater"


def skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def updater_script() -> Path:
    return skill_dir() / "scripts" / "agent_skills_auto_updater.py"


def prompt_text(workspace: str, cadence: str, name: str) -> str:
    cadence_text = {
        "hourly": "every hour",
        "weekly": "weekly",
    }[cadence]

    return dedent(
        f"""\
        Create or update a Codex automation named "{name}".

        Schedule: {cadence_text}.
        Workspace: {workspace}.
        Automation type: prefer a Codex cron automation for a separate recurring run.

        Task prompt:
        Use [$agent-skills-auto-updater]({skill_dir() / "SKILL.md"}) to check local Git-backed AI agent skills. First run:

            python3 {updater_script()} --check

        If updates are available and the worktrees are clean, ask before applying them. Apply only safe fast-forward updates with:

            python3 {updater_script()} --apply

        Report updated, current, skipped, and failed repositories. Do not reset, rebase, force-pull, or overwrite local edits.
        """
    )


def write_auto_prompt_enabled() -> Path:
    path = config_dir() / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"auto_prompt": True}
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare the Codex automation request for agent skill updates."
    )
    parser.add_argument(
        "--workspace",
        default=DEFAULT_WORKSPACE,
        help="workspace directory the Codex automation should run in",
    )
    parser.add_argument(
        "--cadence",
        choices=["hourly", "weekly"],
        default="hourly",
        help="human-readable cadence to put in the generated request",
    )
    parser.add_argument(
        "--name",
        default=DEFAULT_NAME,
        help="Codex automation name to put in the generated request",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="print the generated request after writing it",
    )
    args = parser.parse_args()

    config_path = write_auto_prompt_enabled()
    request_path = config_dir() / "codex_automation_request.md"
    request = prompt_text(args.workspace, args.cadence, args.name)
    request_path.write_text(request, encoding="utf-8")

    print(f"Enabled local prompt state: {config_path}")
    print(f"Wrote Codex automation request: {request_path}")
    print("Paste or ask Codex to execute that request with its automation tool.")
    if args.print:
        print()
        print(request.rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
