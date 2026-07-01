import os, psycopg2

conn = psycopg2.connect(
    host=os.environ["HM_DB_HOST"],
    port=os.environ["HM_DB_PORT"],
    user=os.environ["HM_DB_USER"],
    password=os.environ["HM_DB_PASSWORD"],
    database=os.environ["HM_DB_NAME"]
)
cur = conn.cursor()

# Per-key success latency in 13-17h window
cur.execute("""
    SELECT nv_key_idx, COUNT(*) as ok, 
           ROUND(AVG(duration_ms)::numeric, 0)::int as avg_ok
    FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours' 
      AND EXTRACT(HOUR FROM created_at) BETWEEN 13 AND 17
      AND status = 200
    GROUP BY nv_key_idx ORDER BY nv_key_idx
""")
print("KEY SUCCESS (13-17h):")
for row in cur.fetchall():
    print(f"  k{row[0]}: {row[1]} ok, avg {row[2]}ms")

# All successes by hour
cur.execute("""
    SELECT TO_CHAR(created_at, 'HH24'), COUNT(*), 
           ROUND(AVG(duration_ms)::numeric, 0)::int
    FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours' AND status = 200
    GROUP BY 1 ORDER BY 2 DESC
""")
print("\nHOURLY SUCCESS:")
for row in cur.fetchall():
    print(f"  {row[0]}h: {row[1]} reqs, avg {row[2]}ms")

conn.close()