# R2051 (HM2→HM1): NVU_BIG_INPUT_COOLDOWN_S 3600→1800 (1h→30m)

## 数据 (CST ~14:55, 2026-07-20)

### 6h 窗口
- 29 req, 24 OK (82.8% SR), 5 fail
- 4 zombie_empty_completion (glm5_2_nv, output_tokens=0, duration 3.9-8.3s)
- 1 all_tiers_exhausted (glm5_2_nv, status=502, duration 40.0s)
- OK avg duration: 9,741ms, max 18,388ms
- 429 key cycling: 19×1 cycle, 3×2 cycles (22/29 = 76% of reqs cycled)
- Fallback: 0 occurrences
- Peer-fb: 0
- abs_cap: 0 errors
- docker logs: 0 errors/warnings

### 30min 窗口
- 2 req, 2 OK (100% SR), 0 errors

### 容器 env (live)
- UPSTREAM_TIMEOUT=25, TIER_TIMEOUT_BUDGET_S=153, KEY_COOLDOWN_S=0, TIER_COOLDOWN_S=0
- NVU_BIG_INPUT_THRESHOLD=100000, NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=3600→1800
- NVU_STREAM_FIRST_BYTE_DEADLINE_S=15, NVU_STREAM_TOTAL_DEADLINE_S=25
- NVU_PEER_FALLBACK_TIMEOUT=122, NVU_PEER_FALLBACK_ENABLED=1

## 分析

R2049 将 BIG_INPUT_COOLDOWN 从 10800→3600 (3h→1h) 已验证安全。6h 窗口 4 zombie 均为 glm5_2_nv output_tokens=0（NVCF function-level 空响应，非网关可修）。3600s cooldown 对于 4.8 req/h 的低流量仍偏保守 — 每个 zombie 触发后锁 1h，若 2h 内触发 2 次则合法大输入请求连续被阻。1800s (30m) 在相同低流量下安全：5 keys × 5 req/h 密度极低，30m 冷却足以吸收 zombie 簇，同时让 breaker 更快复位恢复合法大输入请求。

## 改动

NVU_BIG_INPUT_COOLDOWN_S: 3600 → 1800 (1h → 30m)

单参数对；铁律：只改 HM1 不改 HM2。

## 验证

- Compose 写入确认: `grep -n 'NVU_BIG_INPUT_COOLDOWN_S' /opt/cc-infra/docker-compose.yml` → 1800 ✓
- 容器重启: `docker compose up -d nv_gw` → Recreated/Started ✓
- Live env 确认: `docker exec nv_gw env | grep NVU_BIG_INPUT_COOLDOWN_S` → 1800 ✓
- Health check: `curl localhost:40006/health` → status: ok ✓
## ⏳ 轮到HM1优化HM2
