from __future__ import annotations

from dataclasses import dataclass

from .config import AppConfig, is_custom_project_type


COMMON_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".lmstudio-watchdog",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    ".turbo",
    ".parcel-cache",
    ".next",
    ".nuxt",
    ".output",
    "coverage",
    "dist",
    "build",
    "tmp",
    "temp",
    "logs",
}

COMMON_EXCLUDE_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    "merged-files.md",
    "project_structure.md",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "composer.lock",
    "poetry.lock",
    "Pipfile.lock",
}

COMMON_EXCLUDE_GLOBS = {
    ".env",
    ".env.*",
    "**/.env",
    "**/.env.*",
    "*.log",
    "*.sqlite",
    "*.sqlite3",
    "*.db",
    "*.bak",
    "*.backup",
    "*.tmp",
}

BINARY_EXTENSIONS = {
    ".7z",
    ".avi",
    ".bmp",
    ".class",
    ".dll",
    ".dmg",
    ".doc",
    ".docx",
    ".eot",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jar",
    ".jpeg",
    ".jpg",
    ".lockb",
    ".mov",
    ".mp3",
    ".mp4",
    ".o",
    ".obj",
    ".otf",
    ".pdf",
    ".png",
    ".pyc",
    ".rar",
    ".so",
    ".tar",
    ".ttf",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
    ".zip",
}

COMMON_INCLUDE_EXTENSIONS = {
    ".bat",
    ".astro",
    ".c",
    ".cfg",
    ".conf",
    ".cpp",
    ".cs",
    ".cshtml",
    ".csproj",
    ".css",
    ".csv",
    ".clj",
    ".cljc",
    ".cljs",
    ".dart",
    ".dockerfile",
    ".edn",
    ".erl",
    ".ex",
    ".exs",
    ".fs",
    ".fsproj",
    ".fsx",
    ".go",
    ".gradle",
    ".graphql",
    ".groovy",
    ".h",
    ".hrl",
    ".hpp",
    ".htm",
    ".html",
    ".ini",
    ".java",
    ".jl",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".kts",
    ".less",
    ".lua",
    ".m",
    ".md",
    ".mm",
    ".mjs",
    ".nim",
    ".pl",
    ".pm",
    ".php",
    ".phtml",
    ".ps1",
    ".py",
    ".r",
    ".razor",
    ".rb",
    ".rmd",
    ".rs",
    ".sbt",
    ".sass",
    ".scala",
    ".scss",
    ".sh",
    ".sln",
    ".sql",
    ".swift",
    ".svelte",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".vb",
    ".vbproj",
    ".v",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
    ".zig",
    ".zon",
}

COMMON_INCLUDE_FILENAMES = {
    ".editorconfig",
    ".gitattributes",
    ".gitignore",
    "Dockerfile",
    "Makefile",
    "Procfile",
}

PRESET_EXCLUDES = {
    "generic": {
        "dirs": set(),
        "files": set(),
        "globs": set(),
        "extensions": set(),
        "include_extensions": set(),
    },
    "custom": {
        "dirs": set(),
        "files": set(),
        "globs": set(),
        "extensions": set(),
        "include_extensions": set(),
    },
    "laravel": {
        "dirs": {"node_modules", "vendor"},
        "files": set(),
        "globs": {
            "bootstrap/cache/**",
            "public/build/**",
            "public/hot",
            "storage/framework/cache/**",
            "storage/framework/sessions/**",
            "storage/framework/testing/**",
            "storage/framework/views/**",
            "storage/logs/**",
        },
        "extensions": set(),
        "include_extensions": {".blade.php"},
    },
    "wordpress": {
        "dirs": {"node_modules", "vendor", "wp-content/cache", "wp-content/uploads"},
        "files": {"wp-config.php"},
        "globs": {"wp-content/upgrade/**", "wp-content/backup*/**", "wp-content/uploads/**"},
        "extensions": set(),
        "include_extensions": {".php"},
    },
    "drupal": {
        "dirs": {"vendor", "sites/default/files"},
        "files": {"sites/default/settings.php"},
        "globs": {"sites/*/files/**"},
        "extensions": set(),
        "include_extensions": {".module", ".install", ".theme", ".php"},
    },
    "symfony": {
        "dirs": {"vendor", "var", "public/bundles"},
        "files": set(),
        "globs": {"var/cache/**", "var/log/**"},
        "extensions": set(),
        "include_extensions": {".php", ".twig", ".yaml", ".yml"},
    },
    "php": {
        "dirs": {"vendor"},
        "files": set(),
        "globs": set(),
        "extensions": set(),
        "include_extensions": set(),
    },
    "python": {
        "dirs": {".venv", "venv", "env", ".tox", ".nox", "htmlcov"},
        "files": set(),
        "globs": {"*.egg-info/**"},
        "extensions": set(),
        "include_extensions": set(),
    },
    "django": {
        "dirs": {".venv", "venv", "env", ".tox", ".nox", "htmlcov", "staticfiles", "media"},
        "files": set(),
        "globs": {"*.egg-info/**", "**/__pycache__/**", "**/staticfiles/**", "**/media/**"},
        "extensions": set(),
        "include_extensions": {".py", ".html", ".jinja", ".jinja2"},
    },
    "flask": {
        "dirs": {".venv", "venv", "env", ".tox", ".nox", "htmlcov", "instance"},
        "files": set(),
        "globs": {"*.egg-info/**", "instance/**"},
        "extensions": set(),
        "include_extensions": {".py", ".html", ".jinja", ".jinja2"},
    },
    "fastapi": {
        "dirs": {".venv", "venv", "env", ".tox", ".nox", "htmlcov"},
        "files": set(),
        "globs": {"*.egg-info/**"},
        "extensions": set(),
        "include_extensions": {".py"},
    },
    "node": {
        "dirs": {"node_modules"},
        "files": set(),
        "globs": {
            ".next/cache/**",
            ".nuxt/**",
            "coverage/**",
            "dist/**",
            "build/**",
        },
        "extensions": set(),
        "include_extensions": set(),
    },
    "javascript": {
        "dirs": {"node_modules"},
        "files": set(),
        "globs": {"coverage/**", "dist/**", "build/**"},
        "extensions": set(),
        "include_extensions": {".js", ".mjs", ".cjs", ".jsx", ".json"},
    },
    "typescript": {
        "dirs": {"node_modules"},
        "files": set(),
        "globs": {"coverage/**", "dist/**", "build/**", "*.tsbuildinfo"},
        "extensions": set(),
        "include_extensions": {".ts", ".tsx", ".js", ".jsx", ".json"},
    },
    "react": {
        "dirs": {"node_modules"},
        "files": set(),
        "globs": {"coverage/**", "dist/**", "build/**", "*.tsbuildinfo"},
        "extensions": set(),
        "include_extensions": {".js", ".jsx", ".ts", ".tsx", ".css", ".scss"},
    },
    "nextjs": {
        "dirs": {"node_modules", ".next", "out"},
        "files": set(),
        "globs": {".next/**", "out/**", "coverage/**", "*.tsbuildinfo"},
        "extensions": set(),
        "include_extensions": {".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".mdx"},
    },
    "vue": {
        "dirs": {"node_modules"},
        "files": set(),
        "globs": {"dist/**", "coverage/**", "*.tsbuildinfo"},
        "extensions": set(),
        "include_extensions": {".vue", ".js", ".ts", ".css", ".scss"},
    },
    "nuxt": {
        "dirs": {"node_modules", ".nuxt", ".output"},
        "files": set(),
        "globs": {".nuxt/**", ".output/**", "dist/**", "coverage/**"},
        "extensions": set(),
        "include_extensions": {".vue", ".js", ".ts", ".css", ".scss"},
    },
    "svelte": {
        "dirs": {"node_modules", ".svelte-kit"},
        "files": set(),
        "globs": {".svelte-kit/**", "build/**", "coverage/**"},
        "extensions": set(),
        "include_extensions": {".svelte", ".js", ".ts", ".css", ".scss"},
    },
    "angular": {
        "dirs": {"node_modules", ".angular"},
        "files": set(),
        "globs": {".angular/**", "dist/**", "coverage/**", "*.tsbuildinfo"},
        "extensions": set(),
        "include_extensions": {".ts", ".html", ".css", ".scss", ".json"},
    },
    "ruby": {
        "dirs": {"vendor/bundle", ".bundle"},
        "files": {"Gemfile.lock"},
        "globs": {"coverage/**", "tmp/**", "log/**"},
        "extensions": set(),
        "include_extensions": {".rb", ".erb", ".haml", ".slim"},
    },
    "rails": {
        "dirs": {"vendor/bundle", ".bundle", "tmp", "log", "storage", "public/assets", "node_modules"},
        "files": {"Gemfile.lock"},
        "globs": {"tmp/**", "log/**", "storage/**", "public/assets/**", "coverage/**"},
        "extensions": set(),
        "include_extensions": {".rb", ".erb", ".haml", ".slim", ".yml"},
    },
    "java": {
        "dirs": {".gradle", "target", "build", "out"},
        "files": set(),
        "globs": {"target/**", "build/**", "out/**"},
        "extensions": set(),
        "include_extensions": {".java", ".gradle", ".xml", ".properties", ".yml"},
    },
    "spring": {
        "dirs": {".gradle", "target", "build", "out"},
        "files": set(),
        "globs": {"target/**", "build/**", "out/**"},
        "extensions": set(),
        "include_extensions": {".java", ".kt", ".gradle", ".xml", ".properties", ".yml"},
    },
    "kotlin": {
        "dirs": {".gradle", "target", "build", "out"},
        "files": set(),
        "globs": {"target/**", "build/**", "out/**"},
        "extensions": set(),
        "include_extensions": {".kt", ".kts", ".java", ".gradle", ".xml"},
    },
    "android": {
        "dirs": {".gradle", ".idea", "build", "app/build"},
        "files": {"local.properties"},
        "globs": {"**/build/**", ".gradle/**"},
        "extensions": set(),
        "include_extensions": {".kt", ".kts", ".java", ".xml", ".gradle"},
    },
    "csharp": {
        "dirs": {".vs", "bin", "obj", "TestResults", "packages"},
        "files": set(),
        "globs": {"**/bin/**", "**/obj/**", "TestResults/**", "packages/**"},
        "extensions": set(),
        "include_extensions": {".cs", ".csproj", ".sln", ".razor", ".cshtml", ".json"},
    },
    "dotnet": {
        "dirs": {".vs", "bin", "obj", "TestResults", "packages"},
        "files": set(),
        "globs": {"**/bin/**", "**/obj/**", "TestResults/**", "packages/**"},
        "extensions": set(),
        "include_extensions": {".cs", ".fs", ".vb", ".csproj", ".fsproj", ".vbproj", ".sln", ".razor"},
    },
    "go": {
        "dirs": {"bin", "vendor"},
        "files": set(),
        "globs": {"coverage/**"},
        "extensions": set(),
        "include_extensions": {".go", ".mod", ".sum"},
    },
    "rust": {
        "dirs": {"target"},
        "files": {"Cargo.lock"},
        "globs": {"target/**"},
        "extensions": set(),
        "include_extensions": {".rs", ".toml"},
    },
    "c": {
        "dirs": {"build", "cmake-build-debug", "cmake-build-release", ".vs"},
        "files": set(),
        "globs": {"build/**", "cmake-build-*/**"},
        "extensions": set(),
        "include_extensions": {".c", ".h", ".cmake", ".txt"},
    },
    "cpp": {
        "dirs": {"build", "cmake-build-debug", "cmake-build-release", ".vs", "x64", "Debug", "Release"},
        "files": set(),
        "globs": {"build/**", "cmake-build-*/**", "x64/**", "Debug/**", "Release/**"},
        "extensions": set(),
        "include_extensions": {".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh", ".cmake", ".txt"},
    },
    "swift": {
        "dirs": {".build", "DerivedData"},
        "files": set(),
        "globs": {".build/**", "DerivedData/**"},
        "extensions": set(),
        "include_extensions": {".swift"},
    },
    "ios": {
        "dirs": {"Pods", "DerivedData", ".build"},
        "files": set(),
        "globs": {"Pods/**", "DerivedData/**", ".build/**"},
        "extensions": set(),
        "include_extensions": {".swift", ".m", ".mm", ".h", ".plist"},
    },
    "dart": {
        "dirs": {".dart_tool", "build"},
        "files": {".packages", "pubspec.lock"},
        "globs": {".dart_tool/**", "build/**"},
        "extensions": set(),
        "include_extensions": {".dart", ".yaml", ".yml"},
    },
    "flutter": {
        "dirs": {".dart_tool", "build", ".pub-cache"},
        "files": {".packages", "pubspec.lock"},
        "globs": {".dart_tool/**", "build/**", ".pub-cache/**"},
        "extensions": set(),
        "include_extensions": {".dart", ".yaml", ".yml"},
    },
    "elixir": {
        "dirs": {"_build", "deps"},
        "files": {"mix.lock"},
        "globs": {"_build/**", "deps/**"},
        "extensions": set(),
        "include_extensions": {".ex", ".exs", ".heex", ".eex"},
    },
    "phoenix": {
        "dirs": {"_build", "deps", "assets/node_modules", "priv/static"},
        "files": {"mix.lock"},
        "globs": {"_build/**", "deps/**", "assets/node_modules/**", "priv/static/**"},
        "extensions": set(),
        "include_extensions": {".ex", ".exs", ".heex", ".eex", ".js", ".ts"},
    },
    "erlang": {
        "dirs": {"_build", "deps", "ebin"},
        "files": {"rebar.lock"},
        "globs": {"_build/**", "deps/**", "ebin/**"},
        "extensions": set(),
        "include_extensions": {".erl", ".hrl", ".app.src"},
    },
    "lua": {
        "dirs": {".luarocks"},
        "files": set(),
        "globs": {".luarocks/**"},
        "extensions": set(),
        "include_extensions": {".lua"},
    },
    "r": {
        "dirs": {".Rproj.user", "renv/library", "packrat/lib"},
        "files": set(),
        "globs": {".Rhistory", ".RData", ".Rproj.user/**", "renv/library/**"},
        "extensions": set(),
        "include_extensions": {".r", ".rmd", ".qmd"},
    },
    "julia": {
        "dirs": {".julia"},
        "files": {"Manifest.toml"},
        "globs": {".julia/**"},
        "extensions": set(),
        "include_extensions": {".jl", ".toml"},
    },
    "scala": {
        "dirs": {"target", ".bsp", ".metals", ".mill"},
        "files": set(),
        "globs": {"target/**", ".bsp/**", ".metals/**"},
        "extensions": set(),
        "include_extensions": {".scala", ".sbt"},
    },
    "clojure": {
        "dirs": {"target", ".cpcache"},
        "files": set(),
        "globs": {"target/**", ".cpcache/**"},
        "extensions": set(),
        "include_extensions": {".clj", ".cljs", ".cljc", ".edn"},
    },
    "haskell": {
        "dirs": {".stack-work", "dist", "dist-newstyle"},
        "files": set(),
        "globs": {".stack-work/**", "dist/**", "dist-newstyle/**"},
        "extensions": set(),
        "include_extensions": {".hs", ".lhs", ".cabal"},
    },
    "zig": {
        "dirs": {"zig-cache", "zig-out", ".zig-cache"},
        "files": set(),
        "globs": {"zig-cache/**", "zig-out/**", ".zig-cache/**"},
        "extensions": set(),
        "include_extensions": {".zig", ".zon"},
    },
    "shell": {
        "dirs": set(),
        "files": set(),
        "globs": set(),
        "extensions": set(),
        "include_extensions": {".sh", ".bash", ".zsh", ".fish"},
    },
    "powershell": {
        "dirs": set(),
        "files": set(),
        "globs": set(),
        "extensions": set(),
        "include_extensions": {".ps1", ".psm1", ".psd1"},
    },
    "unity": {
        "dirs": {"Library", "Temp", "Obj", "Logs", "UserSettings", "Builds", "Build"},
        "files": set(),
        "globs": {"Library/**", "Temp/**", "Obj/**", "Logs/**", "Builds/**", "Build/**"},
        "extensions": set(),
        "include_extensions": {".cs", ".shader", ".asmdef", ".json", ".yaml"},
    },
    "unreal": {
        "dirs": {"Binaries", "DerivedDataCache", "Intermediate", "Saved"},
        "files": set(),
        "globs": {"Binaries/**", "DerivedDataCache/**", "Intermediate/**", "Saved/**"},
        "extensions": set(),
        "include_extensions": {".cpp", ".h", ".cs", ".ini", ".uproject", ".uplugin"},
    },
}


@dataclass(frozen=True, slots=True)
class RuleSet:
    exclude_dirs: frozenset[str]
    exclude_files: frozenset[str]
    exclude_globs: frozenset[str]
    exclude_extensions: frozenset[str]
    include_extensions: frozenset[str]
    include_filenames: frozenset[str]
    max_file_size_bytes: int


def build_rules(config: AppConfig) -> RuleSet:
    preset = preset_for_project_type(config.project_type)

    exclude_dirs = set(COMMON_EXCLUDE_DIRS) | set(preset["dirs"]) | set(config.exclude_dirs)
    exclude_files = set(COMMON_EXCLUDE_FILES) | set(preset["files"]) | set(config.exclude_files)
    exclude_globs = set(COMMON_EXCLUDE_GLOBS) | set(preset["globs"]) | set(config.exclude_globs)
    exclude_extensions = (
        set(BINARY_EXTENSIONS)
        | set(preset["extensions"])
        | {ext.lower() for ext in config.exclude_extensions}
    )

    if config.include_extensions:
        include_extensions = {ext.lower() for ext in config.include_extensions}
    else:
        include_extensions = set(COMMON_INCLUDE_EXTENSIONS) | set(preset["include_extensions"])

    return RuleSet(
        exclude_dirs=frozenset(exclude_dirs),
        exclude_files=frozenset(exclude_files),
        exclude_globs=frozenset(exclude_globs),
        exclude_extensions=frozenset(exclude_extensions),
        include_extensions=frozenset(include_extensions),
        include_filenames=frozenset(COMMON_INCLUDE_FILENAMES),
        max_file_size_bytes=max(1, int(config.max_file_size_kb)) * 1024,
    )


def preset_payload() -> dict[str, object]:
    return {
        "project_types": list(PRESET_EXCLUDES.keys()),
        "presets": {
            project_type: preset_rule_lists(project_type)
            for project_type in sorted(PRESET_EXCLUDES)
        },
        "common_exclude_dirs": sorted(COMMON_EXCLUDE_DIRS),
        "common_exclude_files": sorted(COMMON_EXCLUDE_FILES),
        "common_exclude_globs": sorted(COMMON_EXCLUDE_GLOBS),
        "common_exclude_extensions": sorted(BINARY_EXTENSIONS),
        "common_include_extensions": sorted(COMMON_INCLUDE_EXTENSIONS),
    }


def preset_rule_lists(project_type: str) -> dict[str, list[str]]:
    preset = preset_for_project_type(project_type)
    return {
        "exclude_dirs": sorted(preset["dirs"], key=str.lower),
        "exclude_files": sorted(preset["files"], key=str.lower),
        "exclude_globs": sorted(preset["globs"], key=str.lower),
        "exclude_extensions": sorted(preset["extensions"], key=str.lower),
        "include_extensions": sorted(preset["include_extensions"], key=str.lower),
    }


def preset_for_project_type(project_type: str) -> dict[str, set[str]]:
    if is_custom_project_type(project_type):
        return PRESET_EXCLUDES["custom"]
    return PRESET_EXCLUDES.get(project_type, PRESET_EXCLUDES["generic"])
