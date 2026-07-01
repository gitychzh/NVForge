import os, psycopg2, json, datetime
conn = psycopg2.connect(
    host=os.environ.get('HM_DB_HOST', 'cc_postgres'),
    port=os.environ.get('HM_DB_PORT', '5432'),
    user=os.environ.get('HM_DB_USER', 'litellm'),
    password=os.environ.get('HM_DB_PASSWORD', 'litellm_pg_2026'),
    dbname='hermes_logs'
)
cur = conn.cursor()

# 24h summary
cur.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN status=200 THEN 1 ELSE 0 END) as success,
        SUM(CASE WHEN status!=200 THEN 1 ELSE 0 END) as errors,
        AVG(CASE WHEN status=200 THEN duration_ms ELSE NULL END)::int as avg_latency_ms,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY CASE WHEN status=200 THEN duration_ms ELSE NULL END)::int as p50,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY CASE WHEN status=200 THEN duration_ms ELSE NULL END)::int as p95,
        PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY CASE WHEN status=200 THEN duration_ms ELSE NULL END)::int as p99
    FROM hm_requests
    WHERE timestamp >= NOW() - INTERVAL '24 hours'
""")
row = cur.fetchone()
print("=== 24h SUMMARY ===")
print(f"Total: {row[0]}, Success: {row[1]}, Errors: {row[2]}, Avg: {row[3]}ms, P50: {row[4]}ms, P95: {row[5]}ms, P99: {row[6]}ms")

# Error breakdown
cur.execute("""
    SELECT error_subcategory, COUNT(*), AVG(duration_ms)::int
    FROM hm_requests
    WHERE status != 200 AND timestamp >= NOW() - INTERVAL '24 hours'
    GROUP BY error_subcategory ORDER BY 2 DESC
""")
print("\n=== ERROR BREAKDOWN ===")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} reqs, avg {row[2]}ms")

# Key-level breakdown (last 2h)
cur.execute("""
    SELECT model, 
           COUNT(*) as reqs,
           SUM(CASE WHEN status=200 THEN 1 ELSE 0 END) as ok,
           AVG(CASE WHEN status=200 THEN duration_ms ELSE NULL END)::int as avg_ok_ms
    FROM hm_requests
    WHERE timestamp >= NOW() - INTERVAL '2 hours'
    GROUP BY model ORDER BY 2 DESC
""")
print("\n=== KEY-LEVEL (2h) ===")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} reqs ({row[2]} ok), avg_ok {row[3]}ms")

# Latency buckets (24h, successes only)
cur.execute("""
    SELECT 
        CASE 
            WHEN duration_ms < 3000 THEN '<3s'
            WHEN duration_ms < 10000 THEN '3-10s'
            WHEN duration_ms < 50000 THEN '10-50s'
            WHEN duration_ms < 100000 THEN '50-100s'
            ELSE '>100s'
        END as bucket,
        COUNT(*)
    FROM hm_requests
    WHERE status=200 AND timestamp >= NOW() - INTERVAL '24 hours'
    GROUP BY 1 ORDER BY 2 DESC
""")
print("\n=== LATENCY BUCKETS (24h) ===")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Recent 20 requests
cur.execute("""
    SELECT request_id, timestamp, duration_ms, status, model, error_subcategory
    FROM hm_requests
    WHERE timestamp >= NOW() - INTERVAL '2 hours'
    ORDER BY timestamp DESC LIMIT 20
""")
print("\n=== RECENT 20 ===")
for row in cur.fetchall():
    print(f"  {row[0][:12]}... | {row[1].strftime('%H:%M:%S')} | {row[2]}ms | {row[3]} | {row[4][:20]}... | {row[5][:30] if row[5] else 'OK'}")

conn.close()