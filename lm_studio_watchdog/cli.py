from __future__ import annotations

import argparse
from pathlib import Path

from .config import AppConfig
from .pipeline import run_pipeline
from .web import run_web_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LM Studio Watch Dog")
    subparsers = parser.add_subparsers(dest="command")

    serve = subparsers.add_parser("serve", help="Start the local web UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--no-browser", action="store_true")

    run_once = subparsers.add_parser("run-once", help="Run the pipeline once without the web UI")
    run_once.add_argument("--project", required=True, help="Project folder to scan")
    run_once.add_argument("--type", default="generic", dest="project_type")
    run_once.add_argument("--output-dir", default="")
    run_once.add_argument("--conversation", default="")
    run_once.add_argument("--sync-lmstudio", action="store_true")
    run_once.add_argument("--no-backup", action="store_true")
    run_once.add_argument("--max-file-size-kb", type=int, default=512)

    parser.set_defaults(command="serve", host="127.0.0.1", port=8765, no_browser=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run-once":
        config = AppConfig(
            project_root=str(Path(args.project).expanduser()),
            project_type=args.project_type,
            output_dir=args.output_dir,
            conversation_path=args.conversation,
            sync_lmstudio=args.sync_lmstudio,
            backup_conversation=not args.no_backup,
            max_file_size_kb=args.max_file_size_kb,
        )
        result = run_pipeline(config, logger=print)
        return 0 if result.ok else 1

    run_web_app(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
