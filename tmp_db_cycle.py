import os, psycopg2

conn = psycopg2.connect(
    host=os.environ["HM_DB_HOST"],
    port=os.environ["HM_DB_PORT"],
    user=os.environ["HM_DB_USER"],
    password=os.environ["HM_DB_PASSWORD"],
    database=os.environ["HM_DB_NAME"]
)
cur = conn.cursor()

# Check if key_cycle_429s exists and what values it has
cur.execute("""
    SELECT key_cycle_429s, COUNT(*) as cnt
    FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours' AND status=200
    GROUP BY key_cycle_429s ORDER BY key_cycle_429s
""")
print("KEY_CYCLE_429s DISTRIBUTION (successes):")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check how many successes have 0 cycle 429s (first key worked)
cur.execute("""
    SELECT COUNT(*) FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours' AND status=200 AND key_cycle_429s = 0
""")
print(f"\nFirst-key success (no cycles): {cur.fetchone()[0]}")

conn.close()