# LM Studio Watch Dog

LM Studio Watch Dog is a local project-context builder for LM Studio and other LLM workflows. It scans a project folder, writes a clean project tree, merges allowed source files into one Markdown context file, and can optionally replace the first message in an LM Studio conversation JSON with the latest merged context.

The main application is a native desktop app built with PySide6/Qt. The browser UI is a separate local web interface, not a WebView embedded inside the desktop app.

## What It Is For

- Build one reusable context file for a codebase.
- Keep LM Studio project context updated while you work.
- Exclude generated, cached, binary, and dependency files from the merged context.
- Use project presets for common stacks, then customize rules per project.
- Optionally sync the merged context into the first message of an LM Studio conversation.

## Features

- Native Windows desktop UI with a WinUI-style layout.
- System tray icon while the watcher is running.
- Clear running state with locked settings while watching files.
- Manual `Run Once` and continuous `Start Watcher` workflows.
- Built-in presets for many project types, including Laravel, PHP, WordPress, Python, Django, FastAPI, Node, JavaScript, TypeScript, React, Next.js, Vue, Java, Go, Rust, C#, Flutter, and more.
- Multiple custom presets with editable names and independent rule sets.
- Rule search, add, remove, and duplicate prevention.
- Generates:
  - `project_structure.md`
  - `merged-files.md`
- Optional LM Studio first-message sync with optional backup.
- Optional local web UI.
- Optional GitNexus impact-summary integration: prepends a focused "what changed / what depends on it" summary (from GitNexus's code knowledge graph) to the merged context, instead of relying on the model to re-read the whole project.
- CLI commands for one-shot runs and local web serving.
- Portable Windows EXE build through PyInstaller.

## Requirements

- Python 3.10 or newer.
- PySide6 6.7 or newer.
- Windows is recommended for the full native desktop, tray, and Mica experience.
- PyInstaller is only needed when building the portable EXE.
- LM Studio is optional and only required for conversation JSON sync.

Install runtime dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install build dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

## Run the Native Desktop App

On Windows:

```powershell
.\run-desktop.ps1
```

Or directly with Python:

```powershell
python -m lm_studio_watchdog.desktop
```

## Desktop Workflow

1. Select the project folder.
2. Pick a project preset.
3. Adjust rules from the `Rules` tab when needed.
4. Leave the output folder empty to use the default:

```text
.lmstudio-watchdog/
```

5. Select an LM Studio `*.conversation.json` file if you want sync.
6. Save settings.
7. Run once or start the watcher.

When the watcher is running, settings and rules are locked until it stops. This prevents changes while the app is reading files and writing outputs.

## Project Presets and Rules

The final rule set is built from:

1. Common defaults.
2. The selected project type preset.
3. Your custom rules.

Custom presets support:

- Editable preset names.
- Excluded folders.
- Excluded files.
- Excluded globs.
- Excluded extensions.
- Included files, which can override broader folder or glob exclusions for specific relative paths.
- Included merge extensions.

If you edit rules while a built-in preset is selected, the app automatically switches to a custom preset. This keeps built-in presets stable and makes the custom behavior explicit.

## Local Web UI

Start the web UI:

```powershell
python -m lm_studio_watchdog serve
```

Or on Windows:

```powershell
.\run-web.ps1
```

Default URL:

```text
http://127.0.0.1:8765/
```

If port `8765` is busy, the app tries the next available port. The web UI supports the same preset model as the desktop app, including multiple custom presets, rule search, add/remove controls, dirty save state, and locked settings while the watcher is running.

## GitNexus Integration (Optional)

[GitNexus](https://github.com/abhigyanpatwari/GitNexus) builds a local knowledge graph of a codebase (symbols, calls, imports, dependencies) and can report the blast radius of a change: which functions and files are affected by what you just edited. Watch Dog can use this to prepend a short, targeted impact summary to the merged context instead of, or in addition to, the full project merge.

### Requirements

- Node.js and `npx` available on `PATH`.
- GitNexus installed globally (recommended) or resolvable via `npx`:

```powershell
npm i -g gitnexus
```

### Enabling It

1. Open the **Context Intelligence** section in the desktop app or web UI.
2. Check **"Prepend GitNexus impact summary"**.
3. Save settings and run once or start the watcher.

The first run in a project indexes it automatically (equivalent to `npx gitnexus analyze`). This first index can take a while on large projects; later runs are incremental and fast. The index is stored in a `.gitnexus/` folder inside the project root and is excluded from the project scan and from the merged context by default, just like `.git`.

### Notes

- GitNexus keeps a single global registry (`~/.gitnexus/registry.json`) shared across every project analyzed on the machine. If GitNexus is not installed or a command fails, Watch Dog logs the failure and falls back to the full merged context; this setting never blocks a pipeline run.
- Watch Dog calls GitNexus with flags that skip GitNexus's own `AGENTS.md` / `CLAUDE.md` / `.claude/skills/` generation, since those files being rewritten on every run would otherwise look like a project change and trigger the watcher again.
- This integration is unrelated to `.lmstudio-watchdog/`, the folder used for this app's own generated output.

## Docker

Docker is intended for the local web UI and CLI workflows. The native PySide6 desktop app should be run directly on Windows or packaged as an EXE.

Run with Docker:

```powershell
docker pull hassanbaz92/lm-studio-watchdog:latest
docker run --rm -p 8765:8765 `
  -v "C:\path\to\your\project:/workspace/project" `
  -v "lm-studio-watchdog-data:/app/data" `
  hassanbaz92/lm-studio-watchdog:latest
```

Open:

```text
http://127.0.0.1:8765/
```

Inside the web UI, use container paths such as:

```text
/workspace/project
```

When running inside Docker, type paths manually in the web UI. Native file/folder dialogs are meant for direct host runs and may not be available inside the container.

If you want LM Studio sync from Docker, mount the LM Studio folder too:

```powershell
docker run --rm -p 8765:8765 `
  -v "C:\path\to\your\project:/workspace/project" `
  -v "C:\Users\you\.lmstudio:/lmstudio" `
  -v "lm-studio-watchdog-data:/app/data" `
  hassanbaz92/lm-studio-watchdog:latest
```

Then select conversation files through container paths like:

```text
/lmstudio/conversations/...
```

## CLI Usage

Run once without a UI:

```powershell
python -m lm_studio_watchdog run-once --project "C:\path\to\project" --type laravel
```

Run once and sync LM Studio:

```powershell
python -m lm_studio_watchdog run-once `
  --project "C:\path\to\project" `
  --type laravel `
  --conversation "C:\Users\you\.lmstudio\conversations\...\123.conversation.json" `
  --sync-lmstudio
```

Useful options:

```powershell
python -m lm_studio_watchdog run-once `
  --project "C:\path\to\project" `
  --type python `
  --output-dir ".context" `
  --max-file-size-kb 10240
```

Run once with GitNexus impact summaries enabled (requires `npx gitnexus analyze` support; see [GitNexus Integration](#gitnexus-integration-optional)):

```powershell
python -m lm_studio_watchdog run-once `
  --project "C:\path\to\project" `
  --type python `
  --use-gitnexus
```

## LM Studio Conversation Sync

LM Studio conversations are usually stored under a path similar to:

```text
C:\Users\<you>\.lmstudio\conversations\...
```

Select the `*.conversation.json` file in the UI. When sync is enabled, the app updates the first message with the generated merged context.

For modern LM Studio conversation files, the app updates:

```text
messages[0].versions[0].content[0].text
```

If the conversation uses a simpler message format, it falls back to updating the first message content directly.

Use the backup option before syncing important conversations.

## Build a Portable Windows EXE

```powershell
.\build_exe.ps1
```

Output:

```text
dist\LM-Studio-WatchDog.exe
```

The EXE is a native desktop app. It does not open a browser and does not depend on the web UI.

## Ignored Local Files

The project ignores local configuration, generated output, and build artifacts:

```text
data/
.lmstudio-watchdog/
.gitnexus/
build/
dist/
project_structure.md
merged-files.md
__pycache__/
.venv/
venv/
env/
```

Avoid sharing LM Studio conversation files or backups. They may contain private project context or personal data.

## Project Layout

```text
lm_studio_watchdog/
  cli.py          # CLI entry points
  config.py       # persisted settings and normalization
  presets.py      # project preset rules
  scanner.py      # file discovery and project tree generation
  pipeline.py     # structure + merge + optional LM Studio sync
  lmstudio.py     # conversation JSON update logic
  gitnexus_bridge.py  # optional GitNexus impact-summary integration
  watcher.py      # polling watcher
  desktop.py      # native PySide6 desktop app
  win_mica.py     # Windows Mica support helper
  web.py          # local HTTP API and web server
  static/         # web UI assets
```

## Privacy and Safety

The app runs locally and does not send project files to an external server. However, generated files and synced LM Studio messages may include code, secrets, or private project details that already exist in your project. Review include/exclude rules before sharing generated context files.

If GitNexus integration is enabled, GitNexus itself runs locally via `npx` and stores its index in `.gitnexus/` inside the project. Watch Dog does not send any data to GitNexus's own cloud services; see the [GitNexus repository](https://github.com/abhigyanpatwari/GitNexus) for its own privacy details.
