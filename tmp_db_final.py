import os, psycopg2, json

conn = psycopg2.connect(
    host=os.environ["HM_DB_HOST"],
    port=os.environ["HM_DB_PORT"],
    user=os.environ["HM_DB_USER"],
    password=os.environ["HM_DB_PASSWORD"],
    database=os.environ["HM_DB_NAME"]
)
cur = conn.cursor()

# 24h summary
cur.execute("""
    SELECT COUNT(*) as total,
        SUM(CASE WHEN status=200 THEN 1 ELSE 0 END) as successes,
        SUM(CASE WHEN status!=200 THEN 1 ELSE 0 END) as failures,
        ROUND(AVG(CASE WHEN status=200 THEN duration_ms ELSE NULL END)::numeric, 0)::int as avg_ok_ms,
        ROUND(AVG(CASE WHEN status!=200 THEN duration_ms ELSE NULL END)::numeric, 0)::int as avg_err_ms
    FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours'
""")
row = cur.fetchone()
print(f"24H: total={row[0]}, success={row[1]}, fail={row[2]}, avg_ok={row[3]}ms, avg_err={row[4]}ms")

# Per-key 24h
cur.execute("""
    SELECT nv_key_idx, COUNT(*) as reqs,
        SUM(CASE WHEN status=200 THEN 1 ELSE 0 END) as ok,
        ROUND(AVG(CASE WHEN status=200 THEN duration_ms ELSE NULL END)::numeric, 0)::int as avg_ok_ms
    FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours'
    GROUP BY nv_key_idx ORDER BY nv_key_idx
""")
print("\nPER-KEY 24H:")
for row in cur.fetchall():
    print(f"  k{row[0]}: {row[1]} reqs, {row[2]} ok, avg_ok {row[3]}ms")

# Error types 24h
cur.execute("""
    SELECT error_subcategory, COUNT(*) as cnt, ROUND(AVG(duration_ms)::numeric, 0)::int as avg_ms
    FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours' AND status != 200
    GROUP BY error_subcategory ORDER BY cnt DESC LIMIT 10
""")
print("\nERRORS 24H:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}, avg {row[2]}ms")

# Latency buckets 24h (successes only)
cur.execute("""
    SELECT 
        CASE 
            WHEN duration_ms < 3000 THEN '<3s'
            WHEN duration_ms < 10000 THEN '3-10s'  
            WHEN duration_ms < 30000 THEN '10-30s'
            WHEN duration_ms < 50000 THEN '30-50s'
            WHEN duration_ms < 100000 THEN '50-100s'
            ELSE '>100s'
        END as bucket,
        COUNT(*) as cnt
    FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours' AND status=200
    GROUP BY 1 ORDER BY 2 DESC
""")
print("\nLATENCY BUCKETS (successes):")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Recent errors
cur.execute("""
    SELECT created_at, nv_key_idx, duration_ms, error_subcategory, model, key_cycle_429s
    FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours' AND status != 200
    ORDER BY created_at DESC LIMIT 10
""")
print("\nRECENT ERRORS:")
for row in cur.fetchall():
    print(f"  ts={row[0]}, k{row[1]}, dur={row[2]}ms, err={row[3][:40]}, model={row[4][:30]}, 429s={row[5]}")

conn.close()