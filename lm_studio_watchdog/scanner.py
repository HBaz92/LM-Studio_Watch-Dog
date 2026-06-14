from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import AppConfig
from .presets import RuleSet, build_rules


@dataclass(frozen=True, slots=True)
class FileRecord:
    absolute_path: Path
    relative_path: str
    size: int


def normalize_rel(path: Path) -> str:
    return path.as_posix()


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
    except OSError:
        return False


def file_extension(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".blade.php"):
        return ".blade.php"
    if name.lower() == "dockerfile":
        return ".dockerfile"
    return path.suffix.lower()


def file_extensions(path: Path) -> set[str]:
    name = path.name.lower()
    extensions = {path.suffix.lower()} if path.suffix else set()
    if name == "dockerfile":
        extensions.add(".dockerfile")
    suffixes = [suffix.lower() for suffix in path.suffixes]
    for index in range(len(suffixes)):
        extensions.add("".join(suffixes[index:]))
    return {extension for extension in extensions if extension}


def matches_any_glob(relative_path: str, patterns: Iterable[str]) -> bool:
    rel = relative_path.replace("\\", "/")
    basename = rel.rsplit("/", 1)[-1]
    for pattern in patterns:
        normalized = pattern.replace("\\", "/")
        if fnmatch.fnmatch(rel, normalized) or fnmatch.fnmatch(basename, normalized):
            return True
        if normalized.endswith("/**"):
            base = normalized[:-3].rstrip("/")
            if rel == base or rel.startswith(base + "/"):
                return True
    return False


def normalize_rule_path(value: str) -> str:
    path = str(value or "").strip().replace("\\", "/").strip("/")
    while path.startswith("./"):
        path = path[2:]
    return path


def file_rule_matches(relative_path: str, filename: str, patterns: Iterable[str]) -> bool:
    relative_key = normalize_rule_path(relative_path).lower()
    filename_key = filename.lower()
    for pattern in patterns:
        normalized = normalize_rule_path(pattern)
        if not normalized:
            continue
        pattern_key = normalized.lower()
        if "/" in pattern_key:
            if relative_key == pattern_key:
                return True
        elif filename_key == pattern_key:
            return True
    return False


def included_file_matches(relative_path: str, filename: str, rules: RuleSet) -> bool:
    return file_rule_matches(relative_path, filename, rules.include_files)


def directory_matches_exclude_dir(relative_path: str, dirname: str, rules: RuleSet) -> bool:
    relative_key = normalize_rule_path(relative_path).lower()
    dirname_key = dirname.lower()
    for pattern in rules.exclude_dirs:
        normalized = normalize_rule_path(pattern)
        if not normalized:
            continue
        pattern_key = normalized.lower()
        if "/" in pattern_key:
            if relative_key == pattern_key:
                return True
        elif dirname_key == pattern_key:
            return True
    return False


def has_excluded_parent(relative_path: str, rules: RuleSet) -> bool:
    parts = normalize_rule_path(relative_path).split("/")
    for index in range(1, len(parts)):
        parent = "/".join(parts[:index])
        if directory_matches_exclude_dir(parent, parts[index - 1], rules):
            return True
        if matches_any_glob(parent, rules.exclude_globs):
            return True
    return False


def directory_contains_included_file(relative_path: str, rules: RuleSet) -> bool:
    directory = normalize_rule_path(relative_path).lower().rstrip("/")
    if not directory:
        return False

    for include_file in rules.include_files:
        normalized = normalize_rule_path(include_file).lower()
        if "/" not in normalized:
            continue
        if normalized.startswith(directory + "/"):
            return True
    return False


def should_exclude(
    root: Path,
    path: Path,
    is_dir: bool,
    rules: RuleSet,
    output_dir: Path | None = None,
) -> tuple[bool, str]:
    try:
        relative = normalize_rel(path.relative_to(root))
    except ValueError:
        return True, "outside project root"

    if output_dir and is_relative_to(path, output_dir):
        return True, "generated output"

    name = path.name
    if is_dir:
        excluded_directory = (
            has_excluded_parent(relative, rules)
            or directory_matches_exclude_dir(relative, name, rules)
            or matches_any_glob(relative, rules.exclude_globs)
        )
        if excluded_directory:
            if directory_contains_included_file(relative, rules):
                return False, ""
            return True, f"excluded directory: {name}"
        return False, ""

    if not is_dir:
        if included_file_matches(relative, name, rules):
            return False, ""
        if has_excluded_parent(relative, rules):
            return True, "excluded parent directory"
        if file_rule_matches(relative, name, rules.exclude_files):
            return True, f"excluded file: {name}"
        matched_extensions = file_extensions(path) & rules.exclude_extensions
        if matched_extensions:
            return True, f"excluded extension: {sorted(matched_extensions, key=len)[-1]}"

    if matches_any_glob(relative, rules.exclude_globs):
        return True, "excluded glob"

    return False, ""


def is_mergeable_file(path: Path, rules: RuleSet, relative_path: str = "") -> bool:
    if relative_path and included_file_matches(relative_path, path.name, rules):
        return True
    if path.name in rules.include_filenames:
        return True
    return bool(file_extensions(path) & rules.include_extensions)


def iter_project_files(config: AppConfig, rules: RuleSet | None = None) -> Iterable[FileRecord]:
    root = config.project_path.resolve()
    output_dir = config.resolved_output_dir()
    active_rules = rules or build_rules(config)

    for current_root, dirnames, filenames in os.walk(root):
        current = Path(current_root)

        kept_dirs = []
        for dirname in sorted(dirnames, key=str.lower):
            directory = current / dirname
            excluded, _ = should_exclude(root, directory, True, active_rules, output_dir)
            if not excluded:
                kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in sorted(filenames, key=str.lower):
            file_path = current / filename
            excluded, _ = should_exclude(root, file_path, False, active_rules, output_dir)
            if excluded:
                continue

            try:
                stat = file_path.stat()
            except OSError:
                continue

            yield FileRecord(
                absolute_path=file_path,
                relative_path=normalize_rel(file_path.relative_to(root)),
                size=stat.st_size,
            )


def iter_mergeable_files(config: AppConfig, rules: RuleSet | None = None) -> Iterable[FileRecord]:
    active_rules = rules or build_rules(config)
    for record in iter_project_files(config, active_rules):
        if record.size > active_rules.max_file_size_bytes:
            continue
        if not is_mergeable_file(record.absolute_path, active_rules, record.relative_path):
            continue
        yield record


def generate_project_tree(config: AppConfig, rules: RuleSet | None = None) -> str:
    root = config.project_path.resolve()
    output_dir = config.resolved_output_dir()
    active_rules = rules or build_rules(config)
    project_name = root.name

    lines = [
        f"# Project Structure: {project_name}",
        "",
        "Generated by LM Studio Watch Dog.",
        "",
        "```text",
        f"{project_name}/",
    ]

    def visible_entries(directory: Path) -> list[Path]:
        try:
            children = list(directory.iterdir())
        except (OSError, PermissionError):
            return []

        entries = []
        for child in children:
            is_directory = child.is_dir() and not child.is_symlink()
            excluded, _ = should_exclude(root, child, is_directory, active_rules, output_dir)
            if not excluded:
                entries.append(child)

        return sorted(entries, key=lambda item: (item.is_file(), item.name.lower()))

    def walk(directory: Path, prefix: str = "") -> None:
        entries = visible_entries(directory)
        for index, item in enumerate(entries):
            is_last = index == len(entries) - 1
            connector = "`-- " if is_last else "|-- "
            is_directory = item.is_dir() and not item.is_symlink()
            suffix = "/" if is_directory else ""
            lines.append(f"{prefix}{connector}{item.name}{suffix}")

            if is_directory:
                next_prefix = prefix + ("    " if is_last else "|   ")
                walk(item, next_prefix)

    walk(root)
    lines.append("```")
    lines.append("")
    return "\n".join(lines)
