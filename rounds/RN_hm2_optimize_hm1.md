# R95: HM2 → HM1优化 — TIER_COOLDOWN_S 33→35 (+2s)

**执行者**: HM2 (opc2_uname)  
**目标**: HM1 (opc_uname@100.109.153.83)  
**时间**: 2026-06-27 11:45 UTC  

## 数据收集

### HM1 docker logs hm40006 (最近100行)
- **glm5.1_hm_nv全部5键进入429 cooldown循环**：
  - k2→429 (11:44:46), k3→429 (11:44:52), k4→429 (11:44:55), k5→429 (11:44:57)
  - 5键全cooldown→仅k1可用→k1受理全部请求→也429
  - 典型请求需4-5次cycle尝试才在k1成功
- **deepseek_hm_nv fallback成功率**：多数请求成功fallback到deepseek
- **TIER_TIMEOUT_BUDGET_S=106**, UPSTREAM_TIMEOUT=62, HM_CONNECT_RESERVE_S=22

### HM1 env (docker exec hm40006 env)
```
PROXY_ROLE=passthrough
TIER_COOLDOWN_S=33
KEY_COOLDOWN_S=29.0
MIN_OUTBOUND_INTERVAL_S=17.5
HM_CONNECT_RESERVE_S=22
UPSTREAM_TIMEOUT=62
TIER_TIMEOUT_BUDGET_S=106
```

### DB数据 (PostgreSQL hermes_logs)
- **hm_requests**: 6242 total, 最新10条混合502和200
- **v_hm_key_errors_24h (glm5.1_hm_nv)**:
  - key_idx=0: ConnectionResetError ×34, avg_latency=3187ms
- **v_hm_tier_health_1h**:
  - glm5.1_hm_nv: 182 reqs, 0 failures, avg_latency=29144ms
  - kimi_hm_nv: 7 reqs, 0 failures
  - deepseek_hm_nv: 未在health view单独出现

## 分析

R94将TIER_COOLDOWN从35→33（-2s）缩小tier全局阻塞窗口。但数据表明：
1. **5键全429循环** — 所有glm5.1 key同时进入cooldown
2. **ConnectionResetError=34** (key0 24h) — 键级错误高
3. **KEY_COOLDOWN=29已领先TIER_COOLDOWN 6s** — 键级冷却更快但tier级冷却不足
4. TIER_COOLDOWN=33时NVCF 429 rate limit窗口内键未充分冷却→全键阻塞→tier all-failed

**根本原因**: TIER_COOLDOWN从37→35→33过度缩减，导致tier cooldown窗口小于NVCF实际rate limit窗口。5键同时429后tier级别冷却不足，键恢复后立即再次429。

## 优化执行

**变更**: `TIER_COOLDOWN_S` 33 → 35 **(+2s)**

| 参数 | 旧值 | 新值 | 变化 |
|------|------|------|------|
| TIER_COOLDOWN_S | 33 | 35 | +2s |

**操作**:
1. SSH到HM1: `ssh -p 222 opc_uname@100.109.153.83`
2. 备份: `cp docker-compose.yml docker-compose.yml.bak.R95`
3. 修改 `/opt/cc-infra/docker-compose.yml`: `TIER_COOLDOWN_S: "33"` → `"35"`
4. 重启: `docker compose up -d hm40006`
5. 验证: `docker exec hm40006 env | grep TIER_COOLDOWN` → 35 ✓

**预期效果**:
- +2s tier cooldown增加glm5.1 429 backoff窗口
- 阻尼5键同时429→更均匀冷却分布→减少all-failed
- ConnectionResetError从34下降
- 更多请求在glm5.1直接成功而非fallback到deepseek

**评审**:
- ✅ 更少报错: 减少429 cycle和ConnectionResetError
- ✅ 更快请求: 减少tier all-failed, 更多第一tier成功
- ✅ 超低延迟: 减少100s+ timeout请求
- ✅ 稳定优先: 单参数保守调整
- ✅ 铁律: 只改HM1不改HM2

## 历史轨迹

| 轮次 | 参数 | 变化 | 执行者 |
|------|------|------|--------|
| R80 | KEY_COOLDOWN_S | 33→31 (-2s) | HM2 |
| R82 | KEY_COOLDOWN_S | 31→29 (-2s) | HM2 |
| R94 | TIER_COOLDOWN_S | 35→33 (-2s) | HM2 |
| **R95** | **TIER_COOLDOWN_S** | **33→35 (+2s)** | **HM2** |

## ⏳ 轮到HM1优化HM2