"""Standalone runner — ``python -m devdash``.

Subcommands:
  serve (default)  build the dashboard app and serve it with uvicorn.
  db create        provision the devdash-owned database, then migrate.
"""

from __future__ import annotations

import argparse
import asyncio

from .config import DevDashConfig


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="devdash")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="serve the dashboard (default)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    db = sub.add_parser("db", help="database operations")
    db_sub = db.add_subparsers(dest="db_command")
    db_sub.add_parser("create", help="create the devdash-owned database, then migrate")

    imp = sub.add_parser("import-tokens", help="import Claude Code token usage into a dashboard")
    imp.add_argument("--dev", required=True, help="developer name to attribute rows to")
    imp.add_argument("--url", required=True, help="dashboard base URL, e.g. https://host/dev")
    imp.add_argument("--token", default=None, help="bearer token, if the dashboard requires auth")
    imp.add_argument("--glob", default=None, help="transcript glob (default ~/.claude/**/*.jsonl)")

    chk = sub.add_parser("check-commit-msg", help="validate a commit message's phase tag")
    chk.add_argument("msgfile", help="path to the commit message file (git passes $1)")
    chk.add_argument("--phases-file", required=True, help="JSON/YAML file of host phase keys")

    ins = sub.add_parser("install-hook", help="install the commit-msg hook into a git repo")
    ins.add_argument("--repo", default=".", help="repo root (default: cwd)")
    ins.add_argument("--phases-file", required=True, help="JSON/YAML file of host phase keys")

    args = parser.parse_args(argv)
    config = DevDashConfig()

    if args.command == "db" and args.db_command == "create":
        _db_create(config)
        return
    if args.command == "import-tokens":
        _import_tokens(dev=args.dev, url=args.url, token=args.token, pattern=args.glob)
        return
    if args.command == "check-commit-msg":
        _check_commit_msg(args.msgfile, args.phases_file)
        return
    if args.command == "install-hook":
        from .phases.hook import install_hook

        path = install_hook(args.repo, args.phases_file)
        print(f"installed commit-msg hook: {path}")
        return

    _serve(config, host=getattr(args, "host", "127.0.0.1"), port=getattr(args, "port", 8000))


def _import_tokens(*, dev: str, url: str, token: str | None, pattern: str | None) -> None:
    import json
    import urllib.request

    from .importers import claude_code

    rows = claude_code.discover(dev, pattern)
    if not rows:
        print("no token rows found")
        return
    payload = json.dumps([r.model_dump() for r in rows]).encode()
    req = urllib.request.Request(
        f"{url.rstrip('/')}/phases/tokens/import",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:  # noqa: S310 - operator-supplied URL
        print(resp.read().decode())


def _db_create(config: DevDashConfig) -> None:
    from .db import dispose_engine, make_engine
    from .migrations import create_database, migrate

    async def run() -> None:
        created = await create_database(config.database_url)
        print(f"database {'created' if created else 'already present'}: {_safe_url(config)}")
        engine = make_engine(config.database_url)
        try:
            await migrate(engine, config)
            print("migrate complete")
        finally:
            await dispose_engine(engine)

    asyncio.run(run())


def _check_commit_msg(msgfile: str, phases_file: str) -> None:
    import sys
    from pathlib import Path

    from .phases.hook import check_commit_message, load_phase_keys

    keys = load_phase_keys(phases_file)
    message = Path(msgfile).read_text(encoding="utf-8")
    ok, error = check_commit_message(message, keys)
    if not ok:
        print(f"devdash commit-msg: {error}", file=sys.stderr)
        raise SystemExit(1)


def _serve(config: DevDashConfig, *, host: str, port: int) -> None:
    import uvicorn

    from .dashboard import make_dashboard_app

    app = make_dashboard_app(config)
    uvicorn.run(app, host=host, port=port)


def _safe_url(config: DevDashConfig) -> str:
    from sqlalchemy.engine import make_url

    return make_url(config.database_url).render_as_string(hide_password=True)


if __name__ == "__main__":
    main()
