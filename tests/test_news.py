"""News collection: raw page saved first, paging followed, reruns add nothing."""

import json
from datetime import datetime, timezone

import httpx
import pytest

from trading import news


def _story(i: int, updated: str = "2026-10-13T01:00:01Z") -> dict:
    return {"id": i, "source": "benzinga", "headline": f"story {i}", "summary": "",
            "url": f"https://example.com/{i}", "symbols": ["AAPL"],
            "created_at": "2026-10-13T01:00:00Z", "updated_at": updated}


def _alpaca(pages: list[list[dict]], seen: list[dict]) -> news.AlpacaNews:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params))
        n = int(request.url.params.get("page_token", "0"))
        body = {"news": pages[n], "next_page_token": str(n + 1) if n + 1 < len(pages) else None}
        return httpx.Response(200, json=body)
    client = httpx.Client(base_url="https://data.example", transport=httpx.MockTransport(handler))
    return news.AlpacaNews(client)


def test_ingest_follows_pages_saves_raw_and_is_idempotent(conn, monkeypatch):
    monkeypatch.setenv("ALPACA_PAPER_1_KEY_ID", "k")
    monkeypatch.setenv("ALPACA_PAPER_1_SECRET_KEY", "s")
    seen: list[dict] = []
    pages = [[_story(1), _story(2)], [_story(3)]]
    src = _alpaca(pages, seen)
    start = datetime(2026, 10, 13, tzinfo=timezone.utc)
    end = datetime(2026, 10, 14, tzinfo=timezone.utc)

    assert news.ingest(conn, src, start, end, known_at=end) == 3
    assert [p.get("page_token") for p in seen] == [None, "1"]
    raws = conn.execute("SELECT body FROM raw_responses WHERE source = 'alpaca' ORDER BY id").fetchall()
    assert [len(json.loads(b)["news"]) for (b,) in raws] == [2, 1]
    assert conn.execute("SELECT count(*) FROM news_items WHERE raw_id IS NULL").fetchone()[0] == 0

    assert news.ingest(conn, src, start, end, known_at=end) == 0       # rerun adds nothing
    assert news.last_seen(conn, "alpaca") == datetime(2026, 10, 13, 1, tzinfo=timezone.utc)


def test_edited_story_is_kept_as_a_new_version(conn, monkeypatch):
    monkeypatch.setenv("ALPACA_PAPER_1_KEY_ID", "k")
    monkeypatch.setenv("ALPACA_PAPER_1_SECRET_KEY", "s")
    t = datetime(2026, 10, 14, tzinfo=timezone.utc)
    news.ingest(conn, _alpaca([[_story(1)]], []), t, t, known_at=t)
    news.ingest(conn, _alpaca([[_story(1, "2026-10-13T02:00:00Z")]], []), t, t, known_at=t)
    assert conn.execute("SELECT count(*) FROM news_items WHERE provider_id = '1'").fetchone()[0] == 2


def test_missing_keys_stop_loudly(monkeypatch):
    monkeypatch.delenv("ALPACA_PAPER_1_KEY_ID", raising=False)
    with pytest.raises(RuntimeError, match="ALPACA_PAPER_1_KEY_ID"):
        news.AlpacaNews()
