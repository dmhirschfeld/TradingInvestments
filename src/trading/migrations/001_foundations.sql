-- Phase 1 foundations. Every fact carries known_at (when we learned it) so a
-- past decision only sees what was known then (FR1.1).

CREATE TABLE raw_responses (
    id          BIGSERIAL PRIMARY KEY,
    source      TEXT        NOT NULL,
    request     TEXT        NOT NULL,
    body        TEXT        NOT NULL,
    sha256      TEXT        NOT NULL,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE instruments (
    id          BIGSERIAL PRIMARY KEY,
    symbol      TEXT        NOT NULL,
    name        TEXT,
    kind        TEXT        NOT NULL,          -- stock | etf
    listed_on   DATE,
    delisted_on DATE,
    known_at    TIMESTAMPTZ NOT NULL,
    source      TEXT        NOT NULL,
    raw_id      BIGINT REFERENCES raw_responses(id),
    UNIQUE (symbol, known_at, source)
);

CREATE TABLE daily_bars (
    id          BIGSERIAL PRIMARY KEY,
    symbol      TEXT          NOT NULL,
    day         DATE          NOT NULL,
    open        NUMERIC(18,6) NOT NULL,
    high        NUMERIC(18,6) NOT NULL,
    low         NUMERIC(18,6) NOT NULL,
    close       NUMERIC(18,6) NOT NULL,
    volume      BIGINT        NOT NULL,
    known_at    TIMESTAMPTZ   NOT NULL,
    source      TEXT          NOT NULL,
    raw_id      BIGINT REFERENCES raw_responses(id),
    UNIQUE (symbol, day, known_at, source)
);
CREATE INDEX daily_bars_symbol_day ON daily_bars (symbol, day);

-- One table for every relationship (FR1.4).
CREATE TABLE links (
    id          BIGSERIAL PRIMARY KEY,
    from_entity TEXT        NOT NULL,
    to_entity   TEXT        NOT NULL,
    link_type   TEXT        NOT NULL,
    valid_from  DATE,
    valid_to    DATE,
    known_at    TIMESTAMPTZ NOT NULL,
    source      TEXT        NOT NULL
);
CREATE INDEX links_from ON links (from_entity, link_type);
CREATE INDEX links_to   ON links (to_entity, link_type);

-- Raw theme signals (FR13); smoothing happens on read.
CREATE TABLE theme_observations (
    id            BIGSERIAL PRIMARY KEY,
    theme         TEXT          NOT NULL,
    series        TEXT          NOT NULL,
    observed_for  DATE          NOT NULL,
    value         NUMERIC(20,6) NOT NULL,
    known_at      TIMESTAMPTZ   NOT NULL,
    source        TEXT          NOT NULL,
    raw_id        BIGINT REFERENCES raw_responses(id),
    UNIQUE (series, observed_for, known_at, source)
);

-- Each pipeline x account size is one virtual portfolio (FR15).
CREATE TABLE portfolios (
    id             BIGSERIAL PRIMARY KEY,
    name           TEXT          NOT NULL UNIQUE,
    pipeline       TEXT          NOT NULL,
    starting_cash  NUMERIC(18,2) NOT NULL,
    mirror_account TEXT,                       -- Alpaca paper account label, or NULL
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE orders (
    id              BIGSERIAL PRIMARY KEY,
    portfolio_id    BIGINT        NOT NULL REFERENCES portfolios(id),
    client_order_id TEXT          NOT NULL UNIQUE,
    run_day         DATE          NOT NULL,
    symbol          TEXT          NOT NULL,
    side            TEXT          NOT NULL,    -- buy | sell
    qty             NUMERIC(18,6) NOT NULL CHECK (qty > 0),
    limit_price     NUMERIC(18,6) NOT NULL CHECK (limit_price > 0),
    status          TEXT          NOT NULL,    -- proposed | vetoed | submitted | filled | expired
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE fills (
    id        BIGSERIAL PRIMARY KEY,
    order_id  BIGINT        NOT NULL REFERENCES orders(id),
    qty       NUMERIC(18,6) NOT NULL CHECK (qty > 0),
    price     NUMERIC(18,6) NOT NULL CHECK (price > 0),
    cost      NUMERIC(18,6) NOT NULL CHECK (cost >= 0),
    source    TEXT          NOT NULL,          -- ledger | broker
    filled_at TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- Step-completion records make every run restartable (NF2).
CREATE TABLE run_steps (
    run_day     DATE        NOT NULL,
    step        TEXT        NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_day, step)
);

-- Pivotal-event detector logs from phase 1; it does not trade yet (FR14).
CREATE TABLE pivotal_events (
    id          BIGSERIAL PRIMARY KEY,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    trigger     TEXT        NOT NULL,          -- news | market_shock
    headline    TEXT,
    sources     JSONB       NOT NULL DEFAULT '[]',
    status      TEXT        NOT NULL           -- unconfirmed | confirmed | pivotal | ordinary
);

-- Append-only audit log with a hash chain (FR11).
CREATE TABLE audit_log (
    id        BIGSERIAL PRIMARY KEY,
    at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    run_day   DATE,
    step      TEXT        NOT NULL,
    kind      TEXT        NOT NULL,
    payload   JSONB       NOT NULL,
    prev_hash TEXT        NOT NULL,
    hash      TEXT        NOT NULL UNIQUE
);

CREATE FUNCTION audit_log_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_no_update BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();
CREATE TRIGGER audit_log_no_truncate BEFORE TRUNCATE ON audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION audit_log_append_only();
