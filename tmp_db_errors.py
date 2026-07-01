import os, psycopg2

conn = psycopg2.connect(
    host=os.environ["HM_DB_HOST"],
    port=os.environ["HM_DB_PORT"],
    user=os.environ["HM_DB_USER"],
    password=os.environ["HM_DB_PASSWORD"],
    database=os.environ["HM_DB_NAME"]
)
cur = conn.cursor()

# Check hm_tier_attempts for error details
cur.execute("""
    SELECT error_type, COUNT(*) as cnt 
    FROM hm_tier_attempts 
    WHERE created_at > NOW() - INTERVAL '24 hours' AND error_type IS NOT NULL
    GROUP BY error_type ORDER BY cnt DESC LIMIT 10
""")
print("TIER ERROR TYPES 24H:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check actual error detail (the JSON field)
cur.execute("""
    SELECT error_detail FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours' AND status != 200
    LIMIT 3
""")
print("\nERROR DETAIL SAMPLES:")
for row in cur.fetchall():
    print(f"  {row[0][:200] if row[0] else 'NULL'}")

# Check fallback_tiers_used
cur.execute("""
    SELECT fallback_tiers_used, COUNT(*) as cnt
    FROM hm_requests
    WHERE created_at > NOW() - INTERVAL '24 hours' AND status=200
    GROUP BY fallback_tiers_used ORDER BY cnt DESC LIMIT 5
""")
print("\nFALLBACK TIERS (successes):")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()