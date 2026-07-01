import sys, os
sys.path.insert(0, '/app/gateway')
import gateway
print("gateway __path__:", gateway.__path__)
print("gateway __file__:", getattr(gateway, '__file__', 'no __file__'))
# Try to import from gateway.config
from gateway import config
print("config __file__:", config.__file__)
# Print vars
print("UPSTREAM_TIMEOUT:", config.UPSTREAM_TIMEOUT)
print("TIER_TIMEOUT_BUDGET_S:", config.TIER_TIMEOUT_BUDGET_S)
print("MIN_OUTBOUND_INTERVAL_S:", config.MIN_OUTBOUND_INTERVAL_S)
print("KEY_COOLDOWN_S:", config.KEY_COOLDOWN_S)
print("TIER_COOLDOWN_S:", getattr(config, 'TIER_COOLDOWN_S', 'not found'))
print("NV_MODEL_TIERS:", getattr(config, 'NV_MODEL_TIERS', 'not found'))
print("HM_NUM_KEYS:", getattr(config, 'HM_NUM_KEYS', 'not found'))