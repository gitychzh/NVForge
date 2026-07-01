import os, psycopg2, json
conn = psycopg2.connect(
    host=os.environ.get('HM_DB_HOST', 'cc_postgres'),
    port=os.environ.get('HM_DB_PORT', '5432'),
    user=os.environ.get('HM_DB_USER', 'litellm'),
    password=os.environ.get('HM_DB_PASSWORD', 'litellm_pg_2026'),
    dbname=os.environ.get('HM_DB_NAME', 'hermes_logs')
)
cur = conn.cursor()

# 24h error details
print("=== 24H ERROR DETAILS ===")
cur.execute("SELECT error_type, COUNT(*) as cnt, ROUND(AVG(duration_ms)::numeric,1)::float as avg_ms FROM hm_requests WHERE created_at > NOW() - INTERVAL '24 hours' AND status!='200' GROUP BY error_type ORDER BY cnt DESC")
for r in cur.fetchall(): print(r)

# 24h success latency distribution  
print("\n=== 24H SUCCESS LATENCY BUCKETS ===")
cur.execute("SELECT CASE WHEN duration_ms < 3000 THEN '<3s' WHEN duration_ms < 5000 THEN '3-5s' WHEN duration_ms < 10000 THEN '5-10s' WHEN duration_ms < 20000 THEN '10-20s' WHEN duration_ms < 50000 THEN '20-50s' WHEN duration_ms < 100000 THEN '50-100s' ELSE '>100s' END as bucket, COUNT(*) as cnt FROM hm_requests WHERE created_at > NOW() - INTERVAL '24 hours' AND status='200' GROUP BY 1 ORDER BY CASE WHEN duration_ms < 3000 THEN 1 WHEN duration_ms < 5000 THEN 2 WHEN duration_ms < 10000 THEN 3 WHEN duration_ms < 20000 THEN 4 WHEN duration_ms < 50000 THEN 5 WHEN duration_ms < 100000 THEN 6 ELSE 7 END")
for r in cur.fetchall(): print(r)

# 24h per-key success stats
print("\n=== 24H PER-KEY SUCCESS ===")
cur.execute("SELECT nv_key_idx, COUNT(*) as reqs, ROUND(AVG(duration_ms)::numeric,1)::float as avg_ms, SUM(CASE WHEN status=200 THEN 1 ELSE 0 END) as succ, SUM(CASE WHEN status!=200 THEN 1 ELSE 0 END) as fail FROM hm_requests WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY nv_key_idx ORDER BY nv_key_idx")
for r in cur.fetchall(): print(r)

# 24h per-key success avg (only 200)
print("\n=== 24H PER-KEY SUCCESS ONLY ===")
cur.execute("SELECT nv_key_idx, COUNT(*) as reqs, ROUND(AVG(duration_ms)::numeric,1)::float as ok_avg FROM hm_requests WHERE created_at > NOW() - INTERVAL '24 hours' AND status='200' GROUP BY nv_key_idx ORDER BY nv_key_idx")
for r in cur.fetchall(): print(r)

conn.close()