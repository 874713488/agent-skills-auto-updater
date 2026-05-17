#!/usr/bin/env python3
"""Check and safely update local Git-backed Codex skills."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass
class RepoResult:
    path: str
    name: str
    status: str
    branch: str = ""
    local: str = ""
    upstream: str = ""
    remote: str = ""
    message: str = ""


def config_path() -> Path:
    return codex_home() / "update-local-skills.json"


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {"auto_prompt": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"auto_prompt": False}
    return data if isinstance(data, dict) else {"auto_prompt": False}


def save_config(data: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def set_auto_prompt(enabled: bool) -> None:
    data = load_config()
    data["auto_prompt"] = enabled
    save_config(data)


def run_git(repo: Path, args: List[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo)] + args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def first_line(text: str) -> str:
    return text.strip().splitlines()[0] if text.strip() else ""


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def default_roots(include_plugin_cache: bool) -> List[Path]:
    home = codex_home()
    roots = [home / "skills"]
    if include_plugin_cache:
        roots.append(home / "plugins" / "cache")
    return roots


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def discover_repos(roots: Iterable[Path], include_system: bool) -> List[Path]:
    repos: List[Path] = []
    for root in roots:
        root = root.expanduser()
        if not root.exists():
            continue

        for current, dirs, _files in os.walk(root):
            path = Path(current)

            if not include_system and path.name == ".system":
                dirs[:] = []
                continue

            if ".git" in dirs:
                if not any(is_within(path, repo) for repo in repos):
                    repos.append(path)
                dirs[:] = []
                continue

            dirs[:] = [d for d in dirs if d != ".git"]

    return sorted(repos, key=lambda p: str(p).lower())


def rev_parse(repo: Path, ref: str, timeout: int) -> str:
    result = run_git(repo, ["rev-parse", "--short", ref], timeout)
    return first_line(result.stdout) if result.returncode == 0 else ""


def get_branch(repo: Path, timeout: int) -> str:
    result = run_git(repo, ["branch", "--show-current"], timeout)
    return first_line(result.stdout) if result.returncode == 0 else ""


def get_remote(repo: Path, timeout: int) -> str:
    result = run_git(repo, ["remote", "get-url", "origin"], timeout)
    return first_line(result.stdout) if result.returncode == 0 else ""


def get_upstream(repo: Path, branch: str, timeout: int) -> str:
    result = run_git(
        repo,
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        timeout,
    )
    if result.returncode == 0:
        return first_line(result.stdout)

    if branch:
        candidate = f"origin/{branch}"
        exists = run_git(repo, ["rev-parse", "--verify", "--quiet", candidate], timeout)
        if exists.returncode == 0:
            return candidate

    return ""


def worktree_dirty(repo: Path, timeout: int) -> bool:
    result = run_git(repo, ["status", "--porcelain"], timeout)
    return bool(result.stdout.strip()) if result.returncode == 0 else True


def classify(repo: Path, upstream: str, timeout: int) -> str:
    local = rev_parse(repo, "HEAD", timeout)
    remote = rev_parse(repo, upstream, timeout)
    if not local or not remote:
        return "unknown"
    if local == remote:
        return "current"

    base_result = run_git(repo, ["merge-base", "HEAD", upstream], timeout)
    base = first_line(base_result.stdout) if base_result.returncode == 0 else ""
    full_local = first_line(run_git(repo, ["rev-parse", "HEAD"], timeout).stdout)
    full_remote = first_line(run_git(repo, ["rev-parse", upstream], timeout).stdout)

    if base == full_local:
        return "behind"
    if base == full_remote:
        return "ahead"
    return "diverged"


def process_repo(repo: Path, apply: bool, timeout: int) -> RepoResult:
    name = repo.name
    branch = get_branch(repo, timeout)
    remote_url = get_remote(repo, timeout)
    local_sha = rev_parse(repo, "HEAD", timeout)

    if not branch:
        return RepoResult(
            path=str(repo),
            name=name,
            status="skipped",
            branch="detached",
            local=local_sha,
            remote=remote_url,
            message="detached HEAD",
        )

    if worktree_dirty(repo, timeout):
        return RepoResult(
            path=str(repo),
            name=name,
            status="skipped",
            branch=branch,
            local=local_sha,
            remote=remote_url,
            message="dirty worktree",
        )

    fetch = run_git(repo, ["fetch", "--prune", "origin"], timeout)
    if fetch.returncode != 0:
        return RepoResult(
            path=str(repo),
            name=name,
            status="failed",
            branch=branch,
            local=local_sha,
            remote=remote_url,
            message=first_line(fetch.stderr) or first_line(fetch.stdout),
        )

    upstream = get_upstream(repo, branch, timeout)
    if not upstream:
        return RepoResult(
            path=str(repo),
            name=name,
            status="skipped",
            branch=branch,
            local=local_sha,
            remote=remote_url,
            message="no upstream branch",
        )

    remote_sha = rev_parse(repo, upstream, timeout)
    state = classify(repo, upstream, timeout)

    if state == "current":
        return RepoResult(
            path=str(repo),
            name=name,
            status="current",
            branch=branch,
            local=local_sha,
            upstream=remote_sha,
            remote=remote_url,
            message=f"up to date with {upstream}",
        )

    if state != "behind":
        return RepoResult(
            path=str(repo),
            name=name,
            status="skipped",
            branch=branch,
            local=local_sha,
            upstream=remote_sha,
            remote=remote_url,
            message=f"local branch is {state} relative to {upstream}",
        )

    if not apply:
        return RepoResult(
            path=str(repo),
            name=name,
            status="update_available",
            branch=branch,
            local=local_sha,
            upstream=remote_sha,
            remote=remote_url,
            message=f"behind {upstream}",
        )

    pull = run_git(repo, ["pull", "--ff-only"], timeout)
    if pull.returncode != 0:
        return RepoResult(
            path=str(repo),
            name=name,
            status="failed",
            branch=branch,
            local=local_sha,
            upstream=remote_sha,
            remote=remote_url,
            message=first_line(pull.stderr) or first_line(pull.stdout),
        )

    new_sha = rev_parse(repo, "HEAD", timeout)
    return RepoResult(
        path=str(repo),
        name=name,
        status="updated",
        branch=branch,
        local=new_sha,
        upstream=remote_sha,
        remote=remote_url,
        message=f"{local_sha} -> {new_sha}",
    )


def print_table(results: List[RepoResult]) -> None:
    if not results:
        print("No Git-backed skill repositories found.")
        return

    widths = {
        "status": max(len("status"), *(len(r.status) for r in results)),
        "name": max(len("skill"), *(len(r.name) for r in results)),
        "branch": max(len("branch"), *(len(r.branch) for r in results)),
    }

    print(
        f"{'status':<{widths['status']}}  "
        f"{'skill':<{widths['name']}}  "
        f"{'branch':<{widths['branch']}}  "
        "local      upstream    message"
    )
    print(
        f"{'-' * widths['status']}  "
        f"{'-' * widths['name']}  "
        f"{'-' * widths['branch']}  "
        "-----      --------    -------"
    )
    for r in results:
        print(
            f"{r.status:<{widths['status']}}  "
            f"{r.name:<{widths['name']}}  "
            f"{r.branch:<{widths['branch']}}  "
            f"{r.local or '-':<10} {r.upstream or '-':<11} {r.message}"
        )


def run_update(args: argparse.Namespace) -> int:
    roots = args.root if args.root else default_roots(args.include_plugin_cache)
    repos = discover_repos(roots, args.include_system)
    results = [process_repo(repo, apply=args.apply, timeout=args.timeout) for repo in repos]

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        print_table(results)
        counts = {}
        for r in results:
            counts[r.status] = counts.get(r.status, 0) + 1
        if counts:
            summary = ", ".join(f"{key}: {counts[key]}" for key in sorted(counts))
            print(f"\nSummary: {summary}")

    return 1 if any(r.status == "failed" for r in results) else 0


def run_prompt(args: argparse.Namespace) -> int:
    config = load_config()
    if not config.get("auto_prompt", False):
        print("Auto prompt is disabled. Enable it with --enable-auto-prompt.")
        return 0

    print("Local skills update prompt")
    print("  u: update now")
    print("  c: check only")
    print("  s: skip this time")
    print("  d: disable future prompts")
    choice = input("Choose [u/c/s/d]: ").strip().lower()

    if choice == "d":
        set_auto_prompt(False)
        print("Auto prompt disabled.")
        return 0
    if choice == "s" or choice == "":
        print("Skipped.")
        return 0
    if choice == "c":
        args.apply = False
        return run_update(args)
    if choice == "u":
        args.apply = True
        return run_update(args)

    print(f"Unknown choice: {choice}", file=sys.stderr)
    return 2


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check and safely update local Git-backed Codex skills."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="check only; do not update")
    mode.add_argument("--apply", action="store_true", help="apply safe fast-forward updates")
    mode.add_argument(
        "--prompt",
        action="store_true",
        help="interactive update prompt; respects --enable-auto-prompt/--disable-auto-prompt",
    )
    mode.add_argument(
        "--enable-auto-prompt",
        action="store_true",
        help="enable future prompt-mode runs",
    )
    mode.add_argument(
        "--disable-auto-prompt",
        action="store_true",
        help="disable future prompt-mode runs",
    )
    mode.add_argument(
        "--auto-prompt-status",
        action="store_true",
        help="show whether prompt mode is enabled",
    )
    parser.add_argument(
        "--root",
        action="append",
        type=Path,
        help="skills root to scan; can be provided more than once",
    )
    parser.add_argument(
        "--include-system",
        action="store_true",
        help="include .system skills under scanned roots",
    )
    parser.add_argument(
        "--include-plugin-cache",
        action="store_true",
        help="also scan the Codex plugin cache",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--timeout", type=int, default=60, help="per-git-command timeout in seconds")
    args = parser.parse_args(argv)

    if args.enable_auto_prompt:
        set_auto_prompt(True)
        print(f"Auto prompt enabled in {config_path()}.")
        return 0

    if args.disable_auto_prompt:
        set_auto_prompt(False)
        print(f"Auto prompt disabled in {config_path()}.")
        return 0

    if args.auto_prompt_status:
        state = "enabled" if load_config().get("auto_prompt", False) else "disabled"
        print(f"Auto prompt is {state}. Config: {config_path()}")
        return 0

    if args.prompt:
        return run_prompt(args)

    return run_update(args)


if __name__ == "__main__":
    sys.exit(main())
