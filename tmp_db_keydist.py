import os, psycopg2

conn = psycopg2.connect(
    host=os.environ["HM_DB_HOST"],
    port=os.environ["HM_DB_PORT"],
    user=os.environ["HM_DB_USER"],
    password=os.environ["HM_DB_PASSWORD"],
    database=os.environ["HM_DB_NAME"]
)
cur = conn.cursor()

# Check successful key distribution
cur.execute("""
    SELECT nv_key_idx, COUNT(*) as cnt, 
           ROUND(AVG(duration_ms)::numeric, 0)::int as avg_ms
    FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours' AND status=200
    GROUP BY nv_key_idx ORDER BY nv_key_idx
""")
print("SUCCESSFUL KEY DISTRIBUTION:")
for row in cur.fetchall():
    print(f"  k{row[0]}: {row[1]} ok, avg {row[2]}ms")

# Check by hour in peak window
cur.execute("""
    SELECT TO_CHAR(created_at, 'HH24'), nv_key_idx, COUNT(*), 
           ROUND(AVG(duration_ms)::numeric, 0)::int
    FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours' AND status=200
    GROUP BY 1, 2 ORDER BY 1, 2
""")
print("\nHOURLY x KEY:")
for row in cur.fetchall():
    if row[0] in ('14','15','16','17','13'):
        print(f"  {row[0]}h k{row[1]}: {row[2]} reqs, avg {row[3]}ms")

conn.close()