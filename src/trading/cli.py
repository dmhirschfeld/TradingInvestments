"""Command line: `uv run --env-file .env trading <command>`. Every failure exits non-zero."""

import argparse
from datetime import datetime, timedelta, timezone

from trading import audit, db, news, pipeline, variants
from trading.broker import AlpacaPaper

NEWS_FIRST_PULL = timedelta(days=1)   # how far back the very first news pull reaches


def _mirror_accounts() -> list[str]:
    """Alpaca accounts that mirror a portfolio active in the current phase."""
    return sorted({p.mirror_account for p in variants.PIPELINES
                   if p.mirror_account and p.active_from_phase <= pipeline.PHASE})


def cmd_migrate(_args) -> None:
    conn = db.connect()
    print("applied:", db.migrate(conn) or "nothing new")
    print("portfolios created:", variants.seed(conn))


def cmd_ingest_news(_args) -> None:
    conn = db.connect()
    now = datetime.now(timezone.utc)
    source = news.AlpacaNews()
    start = news.last_seen(conn, source.name) or now - NEWS_FIRST_PULL
    stored = news.ingest(conn, source, start, now, known_at=now)
    audit.append(conn, "ingest_news", "step_done", {"source": source.name, "stored": stored})
    print(f"news: {stored} new stories since {start.isoformat()}")


def cmd_check_brokers(_args) -> None:
    """Read-only: each mirrored account answers and its positions are listed."""
    for label in _mirror_accounts():
        held = AlpacaPaper(label).positions()
        print(f"{label}: ok, {len(held)} positions {dict(sorted(held.items()))}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="trading")
    sub = parser.add_subparsers(required=True)
    sub.add_parser("migrate", help="apply migrations and create portfolios").set_defaults(fn=cmd_migrate)
    sub.add_parser("ingest-news", help="pull new news stories").set_defaults(fn=cmd_ingest_news)
    sub.add_parser("check-brokers", help="read-only check of mirrored Alpaca accounts") \
        .set_defaults(fn=cmd_check_brokers)
    args = parser.parse_args(argv)
    args.fn(args)
