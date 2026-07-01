import os, psycopg2

conn = psycopg2.connect(
    host=os.environ["HM_DB_HOST"],
    port=os.environ["HM_DB_PORT"],
    user=os.environ["HM_DB_USER"],
    password=os.environ["HM_DB_PASSWORD"],
    database=os.environ["HM_DB_NAME"]
)
cur = conn.cursor()

# Per-key error types
cur.execute("""
    SELECT key_idx, error_type, COUNT(*) as cnt
    FROM hm_tier_attempts 
    WHERE created_at > NOW() - INTERVAL '24 hours' AND error_type IS NOT NULL
    GROUP BY key_idx, error_type ORDER BY cnt DESC
""")
print("PER-KEY TIER ERRORS 24H:")
for row in cur.fetchall():
    print(f"  k{row[0]}: {row[1]} x{row[2]}")

# Also check the hour-level error distribution
cur.execute("""
    SELECT TO_CHAR(created_at, 'HH24') as hr, COUNT(*) as cnt
    FROM hm_tier_attempts
    WHERE created_at > NOW() - INTERVAL '24 hours' AND error_type = 'NVCFPexecTimeout'
    GROUP BY hr ORDER BY cnt DESC LIMIT 10
""")
print("\nTIMEOUT BY HOUR:")
for row in cur.fetchall():
    print(f"  {row[0]}h: {row[1]}")

conn.close()