from __future__ import annotations

import platform
import shutil
import subprocess
from pathlib import Path
from typing import Callable

Logger = Callable[[str], None]

GITNEXUS_INDEX_DIR = ".gitnexus"


def is_gitnexus_installed() -> bool:
    """Check that npx is reachable on PATH (GitNexus itself is invoked via npx)."""
    return shutil.which("npx") is not None


def _npx_command(args: list[str]) -> list[str]:
    """
    Build the command to run npx with the given args.

    On Windows, npx ships as npx.cmd (a batch script), and Windows' CreateProcess
    cannot execute .cmd files directly when subprocess.run is given a plain
    ["npx", ...] list -- it raises FileNotFoundError ([WinError 2]) even though
    npx is on PATH and shutil.which("npx") finds it. Routing through
    "cmd /c npx ..." lets cmd.exe resolve and run the .cmd file correctly.
    This keeps args as a list (no shell=True / no string interpolation), so it
    does not introduce shell-injection risk.
    """
    if platform.system() == "Windows":
        return ["cmd", "/c", "npx", *args]
    return ["npx", *args]


def _no_window_kwargs() -> dict:
    """
    Extra subprocess.run kwargs to stop a CMD window from flashing on screen.

    The desktop app is a windowed (non-console) PySide6 app. When it spawns
    `cmd /c npx ...`, Windows briefly opens a visible console window for the
    child process unless explicitly told not to. CREATE_NO_WINDOW only exists
    on Windows, so this is a no-op everywhere else.
    """
    if platform.system() == "Windows":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def has_index(project_root: Path) -> bool:
    """Check whether the project already has a GitNexus knowledge-graph index."""
    return (project_root / GITNEXUS_INDEX_DIR).is_dir()


def run_analyze(project_root: Path, logger: Logger | None = None, timeout: int = 300) -> bool:
    """
    Build (or refresh) the GitNexus knowledge graph for the project.
    Safe to call repeatedly; GitNexus does incremental updates after the first run.
    """
    if not is_gitnexus_installed():
        if logger:
            logger("GitNexus skipped: npx not found on PATH.")
        return False

    try:
        result = subprocess.run(
            _npx_command(
                [
                    "gitnexus",
                    "analyze",
                    # By default, `analyze` writes/overwrites AGENTS.md and CLAUDE.md
                    # in the repo root on every run. In a continuously-watched
                    # project that creates an infinite loop: analyze touches those
                    # files -> the watcher sees them change -> reruns the pipeline
                    # -> reruns analyze -> touches them again, forever. We only
                    # want the knowledge-graph index, not GitNexus's own
                    # editor/agent integration files, so skip that step.
                    #
                    # NOTE: an earlier version of this also passed --skip-skills,
                    # which does not exist in gitnexus 1.6.x ("unknown option") and
                    # was removed. Re-check `npx gitnexus analyze --help` if you
                    # upgrade GitNexus, in case this changes again.
                    "--skip-agents-md",
                ]
            ),
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=timeout,
            **_no_window_kwargs(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        if logger:
            logger(f"GitNexus analyze failed: {type(exc).__name__}: {exc}")
        return False

    if result.returncode != 0:
        if logger:
            combined = (result.stdout.strip() + "\n" + result.stderr.strip()).strip()
            logger(
                f"GitNexus analyze failed (exit {result.returncode}): "
                f"{combined[:500] or '(no output captured)'}"
            )
        return False

    if logger:
        logger("GitNexus index refreshed.")
    return True


def get_impact_summary(
    project_root: Path,
    scope: str = "unstaged",
    logger: Logger | None = None,
    timeout: int = 60,
) -> str:
    """
    Ask GitNexus what changed and what depends on it (blast-radius / impact data).

    Returns an empty string if GitNexus is unavailable, the project is not yet
    indexed, or the call fails. Callers should treat an empty result as
    "no impact data" and fall back to the full merged context, never as an error
    that should stop the pipeline.

    NOTE: the exact CLI subcommand surface for ad-hoc impact queries (outside the
    MCP stdio interface) may differ between GitNexus versions. Run
    `npx gitnexus --help` and `npx gitnexus detect-changes --help` once on your
    machine to confirm the available flags (including whether it is `--repo` or
    something else) before relying on this in production; adjust the args list
    below if your installed version exposes this differently.
    """
    if not is_gitnexus_installed():
        return ""

    if not has_index(project_root):
        if logger:
            logger(
                "GitNexus index not found. Run 'npx gitnexus analyze' once "
                "in the project root to enable impact summaries."
            )
        return ""

    # GitNexus keeps one global registry (~/.gitnexus/registry.json) shared across
    # every project on the machine. Once more than one repo has been analyzed,
    # commands that don't take an explicit target start failing with
    # 'Multiple repositories indexed. Specify which one with the "repo" parameter.'
    # The registry labels repos by folder name, so pass that explicitly.
    repo_label = project_root.name

    try:
        result = subprocess.run(
            _npx_command(["gitnexus", "detect_changes", "--scope", scope, "--repo", repo_label]),
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=timeout,
            **_no_window_kwargs(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        if logger:
            logger(f"GitNexus detect_changes failed: {type(exc).__name__}: {exc}")
        return ""

    if result.returncode != 0:
        if logger:
            combined = (result.stdout.strip() + "\n" + result.stderr.strip()).strip()
            logger(
                f"GitNexus detect_changes failed (exit {result.returncode}): "
                f"{combined[:500] or '(no output captured)'}"
            )
        return ""

    return result.stdout.strip()