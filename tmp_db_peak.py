import os, psycopg2

conn = psycopg2.connect(
    host=os.environ["HM_DB_HOST"],
    port=os.environ["HM_DB_PORT"],
    user=os.environ["HM_DB_USER"],
    password=os.environ["HM_DB_PASSWORD"],
    database=os.environ["HM_DB_NAME"]
)
cur = conn.cursor()

# Check cycle 429s in peak vs off-peak
cur.execute("""
    SELECT 
        CASE WHEN EXTRACT(HOUR FROM created_at) BETWEEN 14 AND 16 THEN 'peak(14-16)' ELSE 'offpeak' END as period,
        COUNT(*) as reqs,
        ROUND(AVG(duration_ms)::numeric, 0)::int as avg_ms,
        SUM(CASE WHEN key_cycle_429s > 0 THEN 1 ELSE 0 END) as with_cycles,
        ROUND(AVG(key_cycle_429s)::numeric, 2) as avg_cycles
    FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours' AND status=200
    GROUP BY 1
""")
print("PEAK vs OFFPEAK:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} reqs, avg {row[2]}ms, cycles={row[3]}, avg_cycles={row[4]}")

conn.close()