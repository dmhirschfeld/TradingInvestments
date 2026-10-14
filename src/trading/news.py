"""News adapters (DR1). Collected from phase 1 so the pivotal-event detector
and themes have history from day one (FR14, FR13)."""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Protocol

import httpx
import psycopg

from trading import raw_store

ALPACA_DATA_URL = "https://data.alpaca.markets"
ALPACA_NEWS_KEYS = "ALPACA_PAPER_1"   # any Alpaca account's keys can read the news feed
ALPACA_NEWS_PAGE = 50                 # the provider's maximum page size


@dataclass(frozen=True)
class Story:
    provider_id: str
    origin: str | None
    headline: str
    summary: str | None
    url: str | None
    symbols: list[str]
    created_at: datetime
    updated_at: datetime


class NewsSource(Protocol):
    name: str

    def fetch_pages(self, start: datetime, end: datetime) -> Iterator[tuple[str, str]]:
        """Yield (request description, raw response body) per page, oldest stories first."""

    def parse(self, body: str) -> list[Story]: ...


class AlpacaNews:
    """Alpaca's news feed (Benzinga stories), included on the free plan."""

    name = "alpaca"

    def __init__(self, client: httpx.Client | None = None):
        key_id = os.environ.get(f"{ALPACA_NEWS_KEYS}_KEY_ID")
        secret = os.environ.get(f"{ALPACA_NEWS_KEYS}_SECRET_KEY")
        if not key_id or not secret:
            raise RuntimeError(f"{ALPACA_NEWS_KEYS}_KEY_ID / {ALPACA_NEWS_KEYS}_SECRET_KEY are not set")
        self._http = client or httpx.Client(base_url=ALPACA_DATA_URL, timeout=30)
        self._headers = {"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret}

    def fetch_pages(self, start: datetime, end: datetime) -> Iterator[tuple[str, str]]:
        params = {"start": start.isoformat(), "end": end.isoformat(),
                  "limit": ALPACA_NEWS_PAGE, "sort": "asc"}
        while True:
            r = self._http.get("/v1beta1/news", headers=self._headers, params=params)
            r.raise_for_status()
            yield f"alpaca news {json.dumps(params, sort_keys=True)}", r.text
            token = r.json().get("next_page_token")
            if not token:
                return
            params = {**params, "page_token": token}

    def parse(self, body: str) -> list[Story]:
        return [Story(str(n["id"]), n.get("source"), n["headline"], n.get("summary") or None,
                      n.get("url"), list(n.get("symbols") or []),
                      datetime.fromisoformat(n["created_at"]), datetime.fromisoformat(n["updated_at"]))
                for n in json.loads(body)["news"]]


def ingest(conn: psycopg.Connection, source: NewsSource, start: datetime, end: datetime,
           known_at: datetime) -> int:
    """Save each raw page first, then its stories. Returns how many new rows were stored."""
    stored = 0
    for request, body in source.fetch_pages(start, end):
        raw_id = raw_store.save(conn, source.name, request, body)
        for s in source.parse(body):
            row = conn.execute(
                "INSERT INTO news_items (source, provider_id, origin, headline, summary, url, symbols,"
                " created_at, updated_at, known_at, raw_id)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (source, provider_id, updated_at) DO NOTHING RETURNING id",
                (source.name, s.provider_id, s.origin, s.headline, s.summary, s.url, s.symbols,
                 s.created_at, s.updated_at, known_at, raw_id),
            ).fetchone()
            stored += row is not None
    return stored


def last_seen(conn: psycopg.Connection, source_name: str) -> datetime | None:
    """Newest story time already stored, so the next pull starts there."""
    return conn.execute("SELECT MAX(created_at) FROM news_items WHERE source = %s",
                        (source_name,)).fetchone()[0]
