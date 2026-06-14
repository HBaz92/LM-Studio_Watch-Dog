from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from .config import AppConfig
from .lmstudio import sync_first_message
from .presets import build_rules
from .scanner import generate_project_tree, iter_mergeable_files


Logger = Callable[[str], None]


@dataclass(slots=True)
class PipelineResult:
    ok: bool
    structure_path: str = ""
    merged_path: str = ""
    files_merged: int = 0
    lmstudio_synced: bool = False
    messages: list[str] = field(default_factory=list)


LANGUAGE_BY_EXTENSION = {
    ".bat": "batch",
    ".blade.php": "php",
    ".c": "c",
    ".cfg": "ini",
    ".conf": "ini",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".css": "css",
    ".csv": "csv",
    ".dockerfile": "dockerfile",
    ".go": "go",
    ".graphql": "graphql",
    ".h": "c",
    ".hpp": "cpp",
    ".htm": "html",
    ".html": "html",
    ".ini": "ini",
    ".java": "java",
    ".js": "javascript",
    ".json": "json",
    ".jsx": "jsx",
    ".less": "less",
    ".lua": "lua",
    ".md": "markdown",
    ".mjs": "javascript",
    ".php": "php",
    ".phtml": "php",
    ".ps1": "powershell",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".sass": "sass",
    ".scss": "scss",
    ".sh": "bash",
    ".sql": "sql",
    ".svelte": "svelte",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".txt": "text",
    ".vue": "vue",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def file_extension(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".blade.php"):
        return ".blade.php"
    if name == "dockerfile":
        return ".dockerfile"
    return path.suffix.lower()


def language_for(path: Path) -> str:
    return LANGUAGE_BY_EXTENSION.get(file_extension(path), "text")


def code_fence_for(content: str) -> str:
    longest = 0
    current = 0
    for char in content:
        if char == "`":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return "`" * max(3, longest + 1)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(text, encoding="utf-8", errors="replace")
    os.replace(temp_path, path)


def build_merged_markdown(config: AppConfig, structure_text: str) -> tuple[str, int]:
    root = config.project_path.resolve()
    rules = build_rules(config)
    parts: list[str] = [
        "# Merged Project Context",
        "",
        f"Project: `{root.name}`",
        f"Source folder: `{root}`",
        f"Generated: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        "",
        "---",
        "",
        "## Project Structure",
        "",
        structure_text.strip(),
        "",
        "---",
        "",
        "## Files",
        "",
    ]

    count = 0
    for record in iter_mergeable_files(config, rules):
        path = record.absolute_path
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        fence = code_fence_for(content)
        language = language_for(path)
        parts.extend(
            [
                f"### File: `{record.relative_path}`",
                "",
                f"--- START OF FILE: {record.relative_path} ---",
                "",
                f"{fence}{language}",
                content.rstrip(),
                fence,
                "",
                f"--- END OF FILE: {record.relative_path} ---",
                "",
            ]
        )
        count += 1

    return "\n".join(parts).rstrip() + "\n", count


def run_pipeline(config: AppConfig, logger: Logger | None = None) -> PipelineResult:
    messages: list[str] = []

    def log(message: str) -> None:
        messages.append(message)
        if logger:
            logger(message)

    config.normalize()
    if not config.project_root.strip():
        log("Project folder is required.")
        return PipelineResult(False, messages=messages)

    project_root = config.project_path
    if not project_root.exists() or not project_root.is_dir():
        log(f"Project folder not found: {project_root}")
        return PipelineResult(False, messages=messages)

    structure_path = config.structure_path()
    merged_path = config.merged_path()

    try:
        log(f"Scanning project: {project_root}")
        structure_text = generate_project_tree(config)
        atomic_write_text(structure_path, structure_text)
        log(f"Project structure written: {structure_path}")

        merged_text, files_merged = build_merged_markdown(config, structure_text)
        atomic_write_text(merged_path, merged_text)
        log(f"Merged {files_merged} file(s): {merged_path}")

        lmstudio_synced = False
        if config.sync_lmstudio:
            if not config.conversation_path:
                log("LM Studio sync skipped: no conversation path configured.")
            else:
                sync_first_message(
                    merged_text,
                    config.conversation_file,
                    backup=config.backup_conversation,
                    logger=log,
                )
                lmstudio_synced = True
                log(f"LM Studio conversation synced: {config.conversation_file}")

        return PipelineResult(
            ok=True,
            structure_path=str(structure_path),
            merged_path=str(merged_path),
            files_merged=files_merged,
            lmstudio_synced=lmstudio_synced,
            messages=messages,
        )

    except Exception as exc:
        log(f"Pipeline failed: {type(exc).__name__}: {exc}")
        return PipelineResult(
            ok=False,
            structure_path=str(structure_path),
            merged_path=str(merged_path),
            messages=messages,
        )
