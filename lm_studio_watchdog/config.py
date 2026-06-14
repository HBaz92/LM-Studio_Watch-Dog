from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


APP_DIR_NAME = "LM-Studio-WatchDog"
CONFIG_FILENAME = "config.json"
CUSTOM_PROJECT_TYPE = "custom"
CUSTOM_PROJECT_PREFIX = "custom:"
PROJECT_TYPES = (
    "generic",
    CUSTOM_PROJECT_TYPE,
    "laravel",
    "php",
    "wordpress",
    "drupal",
    "symfony",
    "python",
    "django",
    "flask",
    "fastapi",
    "node",
    "javascript",
    "typescript",
    "react",
    "nextjs",
    "vue",
    "nuxt",
    "svelte",
    "angular",
    "ruby",
    "rails",
    "java",
    "spring",
    "kotlin",
    "android",
    "csharp",
    "dotnet",
    "go",
    "rust",
    "c",
    "cpp",
    "swift",
    "ios",
    "dart",
    "flutter",
    "elixir",
    "phoenix",
    "erlang",
    "lua",
    "r",
    "julia",
    "scala",
    "clojure",
    "haskell",
    "zig",
    "shell",
    "powershell",
    "unity",
    "unreal",
)


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def app_data_dir() -> Path:
    return app_base_dir() / "data"


def default_config_path() -> Path:
    return app_data_dir() / CONFIG_FILENAME


@dataclass(slots=True)
class AppConfig:
    project_root: str = ""
    project_type: str = "generic"
    custom_preset_name: str = "custom"
    custom_presets: dict[str, dict[str, Any]] = field(default_factory=dict)
    output_dir: str = ""
    structure_filename: str = "project_structure.md"
    merged_filename: str = "merged-files.md"
    conversation_path: str = ""
    sync_lmstudio: bool = False
    backup_conversation: bool = True
    poll_interval_seconds: float = 1.0
    debounce_seconds: float = 0.8
    max_file_size_kb: int = 512
    exclude_dirs: list[str] = field(default_factory=list)
    exclude_files: list[str] = field(default_factory=list)
    exclude_globs: list[str] = field(default_factory=list)
    exclude_extensions: list[str] = field(default_factory=list)
    include_files: list[str] = field(default_factory=list)
    include_extensions: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        cleaned: dict[str, Any] = {}

        for key, value in data.items():
            if key not in allowed:
                continue
            cleaned[key] = value

        cfg = cls(**cleaned)
        cfg.normalize()
        return cfg

    def update_from_dict(self, data: dict[str, Any]) -> None:
        allowed = {field.name for field in self.__dataclass_fields__.values()}
        for key, value in data.items():
            if key in allowed:
                setattr(self, key, value)
        self.normalize()

    def normalize(self) -> None:
        project_type = str(self.project_type or "").strip()
        if is_custom_project_type(project_type):
            self.project_type = clean_custom_preset_key(project_type) or CUSTOM_PROJECT_TYPE
        elif project_type in PROJECT_TYPES:
            self.project_type = project_type
        else:
            self.project_type = "generic"

        self.project_root = clean_path_text(self.project_root)
        self.custom_preset_name = clean_label_text(self.custom_preset_name, "custom")
        self.custom_presets = normalize_custom_presets(self.custom_presets)
        self.output_dir = clean_path_text(self.output_dir)
        self.conversation_path = clean_path_text(self.conversation_path)
        self.structure_filename = safe_filename(self.structure_filename, "project_structure.md")
        self.merged_filename = safe_filename(self.merged_filename, "merged-files.md")

        self.poll_interval_seconds = clamp_float(self.poll_interval_seconds, 0.5, 30.0, 1.0)
        self.debounce_seconds = clamp_float(self.debounce_seconds, 0.1, 10.0, 0.8)
        self.max_file_size_kb = int(clamp_float(self.max_file_size_kb, 1, 102400, 512))

        self.exclude_dirs = clean_list(self.exclude_dirs)
        self.exclude_files = clean_list(self.exclude_files)
        self.exclude_globs = clean_list(self.exclude_globs, slash_paths=True)
        self.exclude_extensions = normalize_extensions(self.exclude_extensions)
        self.include_files = clean_list(self.include_files, slash_paths=True)
        self.include_extensions = normalize_extensions(self.include_extensions)
        if is_custom_project_type(self.project_type) and self.project_type not in self.custom_presets:
            self.custom_presets[self.project_type] = {
                "name": self.custom_preset_name,
                "exclude_dirs": list(self.exclude_dirs),
                "exclude_files": list(self.exclude_files),
                "exclude_globs": list(self.exclude_globs),
                "exclude_extensions": list(self.exclude_extensions),
                "include_files": list(self.include_files),
                "include_extensions": list(self.include_extensions),
            }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def project_path(self) -> Path:
        return Path(self.project_root).expanduser()

    @property
    def conversation_file(self) -> Path:
        return Path(self.conversation_path).expanduser()

    def resolved_output_dir(self) -> Path:
        project_root = self.project_path
        if self.output_dir:
            output = Path(self.output_dir).expanduser()
            if output.is_absolute():
                return output
            return project_root / output
        return project_root / ".lmstudio-watchdog"

    def structure_path(self) -> Path:
        return self.resolved_output_dir() / self.structure_filename

    def merged_path(self) -> Path:
        return self.resolved_output_dir() / self.merged_filename


def clean_path_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().strip('"')


def clean_label_text(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return text[:64] if text else default


def is_custom_project_type(value: Any) -> bool:
    text = str(value or "").strip()
    return text == CUSTOM_PROJECT_TYPE or text.startswith(CUSTOM_PROJECT_PREFIX)


def clean_custom_preset_key(value: Any) -> str:
    text = str(value or "").strip()
    if text == CUSTOM_PROJECT_TYPE:
        return CUSTOM_PROJECT_TYPE
    if not text.startswith(CUSTOM_PROJECT_PREFIX):
        return ""

    suffix = text[len(CUSTOM_PROJECT_PREFIX) :].strip().lower()
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in suffix)
    cleaned = cleaned.strip("-_")
    return f"{CUSTOM_PROJECT_PREFIX}{cleaned}" if cleaned else ""


def clean_list(value: Any, slash_paths: bool = False) -> list[str]:
    if isinstance(value, str):
        items = value.splitlines()
    elif isinstance(value, list):
        items = value
    else:
        items = []

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        if slash_paths:
            text = text.replace("\\", "/")
        if text not in seen:
            cleaned.append(text)
            seen.add(text)
    return cleaned


def normalize_extensions(value: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in clean_list(value):
        text = item.lower().strip()
        if not text:
            continue
        if not text.startswith("."):
            text = "." + text
        if text not in seen:
            result.append(text)
            seen.add(text)
    return result


def normalize_custom_presets(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}

    normalized: dict[str, dict[str, Any]] = {}
    for raw_key, raw_preset in value.items():
        key = clean_custom_preset_key(raw_key)
        if not key:
            continue

        preset = raw_preset if isinstance(raw_preset, dict) else {}
        fallback_name = "custom" if key == CUSTOM_PROJECT_TYPE else key.split(":", 1)[1]
        normalized[key] = {
            "name": clean_label_text(preset.get("name"), fallback_name),
            "exclude_dirs": clean_list(preset.get("exclude_dirs")),
            "exclude_files": clean_list(preset.get("exclude_files")),
            "exclude_globs": clean_list(preset.get("exclude_globs"), slash_paths=True),
            "exclude_extensions": normalize_extensions(preset.get("exclude_extensions")),
            "include_files": clean_list(preset.get("include_files"), slash_paths=True),
            "include_extensions": normalize_extensions(preset.get("include_extensions")),
        }
    return normalized


def safe_filename(value: Any, default: str) -> str:
    text = str(value or "").strip()
    if not text:
        return default
    forbidden = set('/\\:*?"<>|')
    cleaned = "".join("_" if char in forbidden else char for char in text)
    return cleaned or default


def clamp_float(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return min(max(number, minimum), maximum)


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or default_config_path()
    if not config_path.exists():
        return AppConfig()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppConfig()

    if not isinstance(data, dict):
        return AppConfig()

    return AppConfig.from_dict(data)


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    config.normalize()
    config_path = path or default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = config_path.with_suffix(config_path.suffix + ".tmp")
    payload = json.dumps(config.to_dict(), ensure_ascii=False, indent=2) + "\n"
    temp_path.write_text(payload, encoding="utf-8")

    try:
        replace_with_retry(temp_path, config_path)
    except PermissionError as replace_exc:
        try:
            config_path.write_text(payload, encoding="utf-8")
        except OSError:
            raise replace_exc
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    return config_path


def replace_with_retry(source: Path, target: Path, attempts: int = 5) -> None:
    delay_seconds = 0.08
    for attempt in range(attempts):
        try:
            source.replace(target)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay_seconds)
            delay_seconds *= 2
