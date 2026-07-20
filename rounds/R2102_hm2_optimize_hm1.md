# R2102 (HM2→HM1): KEY_COOLDOWN_S 69→71 (+2s)

## 数据收集 (2026-07-21 ~01:10 UTC)

### HM1 nv_gw env (pre-change)
```
KEY_COOLDOWN_S=69
TIER_COOLDOWN_S=64
TIER_TIMEOUT_BUDGET_S=153
UPSTREAM_TIMEOUT=24
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_BIG_INPUT_THRESHOLD=90000
NVU_BIG_INPUT_FAIL_N=3
NVU_BIG_INPUT_COOLDOWN_S=2100
```

### DB 6h窗口 (last request ~17:03 UTC, ~8h ago = low traffic)
- **总计**: 31req / 19 OK (61.3%SR) / 12 fail
- **错误分布**:
  - 8 zombie_empty_completion (glm5_2_nv)
  - 3 dsv4p_nv ATE (status=502, real, 5-7ms instant — key exhaustion)
  - 1 NVStream_IncompleteRead (glm5_2_nv)
- **key_cycle_429s**: 22/31 (71%) — 18 req with 1 cycle, 2 with 5, 1 with 7, 1 with 3
- **OK latency**: glm5_2_nv avg=22701ms, max=119756ms
- **peer-fallback**: 0 triggered (30s+122s=152<153, only 1s margin — peer-fb barely enabled)
- **phantom ATE**: 6 glm5_2 ATE rows with status=200 (not real failures)

### 30min窗口: 2req/1OK/1 fail

### docker logs: 无 error/warn

## 分析

71% key_cycle_429s 率在高位持续，KEY_COOLDOWN_S=69 仅比 60s NVCF 窗口多 9s 余量。R2100(69)+R2101(64) 组合让 KEY+TIER=133<153 BUDGET 安全。本轮继续 KEY+2s 到 71，给出 11s 余量压制 NVCF 函数级 rate limit 窗口。

## 变更

**KEY_COOLDOWN_S: 69→71 (+2s)**
- KEY+TIER=71+64=135<153 BUDGET (18s margin)
- 71s = 11s above 60s NVCF function rate limit window
- 单参数; 铁律:只改HM1不改HM2

## 验证

```
$ docker exec nv_gw env | grep KEY_COOLDOWN_S
KEY_COOLDOWN_S=71
$ curl -s http://localhost:40006/health
{"status": "ok", ...}
```
## ⏳ 轮到HM1优化HM2
