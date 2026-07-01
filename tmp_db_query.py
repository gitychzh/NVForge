import os, psycopg2, json
conn = psycopg2.connect(
    host=os.environ.get('HM_DB_HOST', 'cc_postgres'),
    port=os.environ.get('HM_DB_PORT', '5432'),
    user=os.environ.get('HM_DB_USER', 'litellm'),
    password=os.environ.get('HM_DB_PASSWORD', 'litellm_pg_2026'),
    dbname=os.environ.get('HM_DB_NAME', 'hermes_logs')
)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status=200 THEN 1 ELSE 0 END) as success, SUM(CASE WHEN status!=200 THEN 1 ELSE 0 END) as errors, ROUND(AVG(duration_ms)::numeric,1)::float as avg_ms, MAX(duration_ms) as max_ms FROM hm_requests WHERE created_at > NOW() - INTERVAL '60 minutes'")
for r in cur.fetchall(): print(r)
cur.execute("SELECT nv_key_idx, COUNT(*) as reqs, ROUND(AVG(duration_ms)::numeric,1)::float as avg_ms, SUM(CASE WHEN status=200 THEN 1 ELSE 0 END) as succ FROM hm_requests WHERE created_at > NOW() - INTERVAL '120 minutes' GROUP BY nv_key_idx ORDER BY nv_key_idx")
for r in cur.fetchall(): print(r)
cur.execute("SELECT error_type, COUNT(*) as cnt FROM hm_requests WHERE created_at > NOW() - INTERVAL '120 minutes' AND error_type IS NOT NULL GROUP BY error_type ORDER BY cnt DESC LIMIT 10")
for r in cur.fetchall(): print(r)
cur.execute("SELECT COUNT(*) as total_errors, SUM(CASE WHEN key_cycle_429s > 0 THEN 1 ELSE 0 END) as has_429 FROM hm_requests WHERE created_at > NOW() - INTERVAL '24 hours' AND status!='200'")
for r in cur.fetchall(): print(r)
cur.execute("SELECT COUNT(*) as total FROM hm_requests WHERE created_at > NOW() - INTERVAL '24 hours'")
for r in cur.fetchall(): print(r)
cur.execute("SELECT created_at, nv_key_idx, duration_ms, status, error_type, total_input_chars FROM hm_requests ORDER BY created_at DESC LIMIT 10")
for r in cur.fetchall(): print(r)
conn.close()