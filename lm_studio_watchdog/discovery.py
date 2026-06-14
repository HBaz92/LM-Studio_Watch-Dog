from __future__ import annotations

import os
from pathlib import Path

from .scanner import file_extensions


RULE_DISCOVERY_CATEGORIES = (
    "exclude_dirs",
    "exclude_files",
    "exclude_globs",
    "exclude_extensions",
    "include_files",
    "include_extensions",
)


def empty_rule_candidates() -> dict[str, list[str]]:
    return {category: [] for category in RULE_DISCOVERY_CATEGORIES}


def _sorted_values(values: set[str]) -> list[str]:
    return sorted(values, key=lambda item: (item.lower().lstrip("."), item.lower()))


def discover_rule_candidates(project_root: str, limit_per_category: int = 1200) -> dict[str, list[str]]:
    candidates = {category: set[str]() for category in RULE_DISCOVERY_CATEGORIES}
    root = Path(project_root).expanduser()

    try:
        root = root.resolve()
    except OSError:
        return empty_rule_candidates()

    if not root.exists() or not root.is_dir():
        return empty_rule_candidates()

    def add(category: str, value: str) -> None:
        if value and len(candidates[category]) < limit_per_category:
            candidates[category].add(value)

    for current_root, dirnames, filenames in os.walk(root):
        current = Path(current_root)
        dirnames[:] = sorted(
            [dirname for dirname in dirnames if dirname != ".git"],
            key=str.lower,
        )

        for dirname in dirnames:
            directory = current / dirname
            if directory.is_symlink():
                continue
            try:
                relative = directory.relative_to(root).as_posix()
            except ValueError:
                continue
            add("exclude_dirs", dirname)
            add("exclude_globs", f"{relative}/**")

        for filename in sorted(filenames, key=str.lower):
            file_path = current / filename
            if file_path.is_symlink():
                continue
            try:
                relative = file_path.relative_to(root).as_posix()
            except ValueError:
                continue
            add("exclude_files", filename)
            add("exclude_globs", relative)
            add("include_files", relative)
            for extension in file_extensions(file_path):
                add("exclude_extensions", extension)
                add("include_extensions", extension)

    return {category: _sorted_values(values) for category, values in candidates.items()}
