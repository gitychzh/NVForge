import os
for i in range(1,6):
    key = os.environ.get(f"HM_NV_KEY{i}")
    proxy = os.environ.get(f"HM_NV_PROXY_URL{i}")
    cooldown_key = os.environ.get('KEY_COOLDOWN_S', '38')
    cooldown_tier = os.environ.get('TIER_COOLDOWN_S', '38')
    print(f'K{i}: proxy={proxy}, key_present={bool(key)}, cooldown_key={cooldown_key}, cooldown_tier={cooldown_tier}')