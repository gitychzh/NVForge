-- R683: ms_gw request logging schema. Idempotent.
-- Mirrors the legacy jsonl-importer ms_requests columns + adds host_machine
-- (per-machine attribution) and normalized_backend_model (variant-case grouping).

CREATE TABLE IF NOT EXISTS ms_requests (
    request_id                  TEXT PRIMARY KEY,
    ts                          TIMESTAMPTZ,
    ts_ms                       BIGINT,
    host_machine                TEXT NOT NULL DEFAULT 'unknown',
    caller                      TEXT,
    agent_model                 TEXT,
    backend                     TEXT,
    backend_model               TEXT,
    normalized_backend_model    TEXT,
    is_stream                   BOOLEAN,
    variant_idx                 INTEGER,
    key_idx                     INTEGER,
    cycle_attempts              INTEGER,
    status                      TEXT,
    resp_status                 INTEGER,
    duration_ms                 INTEGER DEFAULT 0,
    bytes_relayed               INTEGER,
    error_type                  TEXT,
    error_message               TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ms_req_ts          ON ms_requests (ts DESC);
CREATE INDEX IF NOT EXISTS idx_ms_req_status      ON ms_requests (status, ts DESC);
CREATE INDEX IF NOT EXISTS idx_ms_req_host        ON ms_requests (host_machine, ts DESC);
CREATE INDEX IF NOT EXISTS idx_ms_req_norm_model  ON ms_requests (normalized_backend_model, ts DESC);
CREATE INDEX IF NOT EXISTS idx_ms_req_agent       ON ms_requests (agent_model, ts DESC);

-- If the table pre-existed (legacy jsonl importer on HM2) without new columns,
-- add them idempotently (ALTER ... ADD COLUMN IF NOT EXISTS needs PG 9.6+).
ALTER TABLE ms_requests ADD COLUMN IF NOT EXISTS host_machine TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE ms_requests ADD COLUMN IF NOT EXISTS normalized_backend_model TEXT;
ALTER TABLE ms_requests ADD COLUMN IF NOT EXISTS caller TEXT;
ALTER TABLE ms_requests ADD COLUMN IF NOT EXISTS resp_status INTEGER;
