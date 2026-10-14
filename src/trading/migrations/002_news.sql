-- News stories, collected from phase 1 for the pivotal-event detector and themes (FR14, FR13).
-- A story edited by its provider arrives again with a new updated_at and is kept as a new row.

CREATE TABLE news_items (
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT        NOT NULL,          -- adapter name, e.g. alpaca
    provider_id TEXT        NOT NULL,          -- the provider's story id
    origin      TEXT,                          -- who wrote it, e.g. benzinga
    headline    TEXT        NOT NULL,
    summary     TEXT,
    url         TEXT,
    symbols     TEXT[]      NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL,          -- when the provider published it
    updated_at  TIMESTAMPTZ NOT NULL,
    known_at    TIMESTAMPTZ NOT NULL,          -- when we fetched it
    raw_id      BIGINT REFERENCES raw_responses(id),
    UNIQUE (source, provider_id, updated_at)
);
CREATE INDEX news_items_created ON news_items (created_at);
CREATE INDEX news_items_symbols ON news_items USING GIN (symbols);
