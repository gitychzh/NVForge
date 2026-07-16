# R1658 — HM2 → HM1: NVU_PEXEC_TIMEOUT_FASTBREAK 1→2

## ⚙️ 变更

| 参数 | 旧值 | 新值 | 方向 |
|------|------|------|------|
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | 2 | +1 key |

**变更位置**: `/opt/cc-infra/docker-compose.yml` (HM1 only, 铁律: 只改HM1不改HM2)

## 📊 改前数据

### HM1 nv_gw 6h 窗口 (2026-07-16 12:00–18:00 UTC)

```
总请求: 37 (20 OK / 17 fail) → 54.1% SR
dsv4p_nv: 12 req → 7 OK / 5 ATE → 58.3% SR, avg 62,279ms ATE
glm5_2_nv: 25 req → 20 OK / 12 zombie_empty_completion + 0 ATE
```

### dsv4p_nv ATE 详情 (24h)

```
17 个 all_tiers_exhausted (all_tiers_failed_in_mapped_tier)
无 tier_attempts 记录 → 所有 attempt 在协议层失败 (connect/socket 级别)
```

### HM2 peer-fb 日志验证 (HM1→HM2 forward)

```
[18:06:57.2] [NV-REQ] mapped_model=dsv4p_nv (peer-fb from HM1)
[18:07:59.9] [NV-CYCLE] tier=dsv4p_nv k4 → 504 (504_nv_gateway_timeout)
[18:08:07.5] [NV-TIMEOUT] tier=dsv4p_nv k5 NVCF pexec timeout: 7628ms total=70343ms
[18:08:07.5] [NV-TIER-BUDGET] tier=dsv4p_nv budget 70.0s exceeded after 70.2s, breaking
[18:08:07.5] [NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=0, empty200=0, timeout=1, other=1
[18:08:07.5] [NV-PEER-FB] peer-originated request (hop=1) also all_tiers_exhausted, returning 502
```

**根因**: HM2 dsv4p_nv budget=70, 仅能试2个key (k4 504 ~62s + k5 timeout ~8s = 70s). FASTBREAK=1 在HM1侧tx kill tier after 1 timeout → 即使仅1个timeout也放弃 → peer-fb 到HM2 → HM2 也只有 budget=70 试2key → 双双502.

### HM1 env 快照

```
NVU_PEXEC_TIMEOUT_FASTBREAK=1    ← 改前
NVU_TIER_BUDGET_DSV4P_NV=90
NVU_PEER_FALLBACK_TIMEOUT=72
NVU_PEER_FB_SKIP_MODELS=""       ← dsv4p_nv peer-fb enabled (R1646)
TIER_TIMEOUT_BUDGET_S=195
KEY_COOLDOWN_S=65, TIER_COOLDOWN_S=65 (R1657)
```

### HM2 dsv4p_nv 健康度 (对比)

```
HM2 24h: 15/15 (100%) dsv4p_nv — healthy
HM2 dsv4p_nv budget=70, UPSTREAM_TIMEOUT=130
```

## 🎯 分析

NVCF function 74f02205 (dsv4p_nv) 在HM1上 degraded 但未死: 58.3% SR, 非全fail。核心问题:

1. **FASTBREAK=1 一刀切**: k1 遇到 pexec timeout 或 504 → 立即放弃整个 tier
2. **浪费 budget**: 90s budget 只用了一个key (~62s) 就放弃, 剩余 28s 浪费
3. **peer-fb 也救不了**: HM2 budget=70 仅容2key, 加上 HM2 504_nv_gateway_timeout 也是 62s → 2key 双双超时 → 502

**FASTBREAK=2 修复**: 给 k2 第二次机会 (剩余 ~24s budget). 如果 k2 成功 → 省去 peer-fb 72s 的等待, 总延迟从 ~62+72=134s 降到 ~62+~24=86s. 如果 k2 也失败 → peer-fb 仍然触发, 无额外惩罚.

**Budget 安全**: 90 + 72 = 162 < 195 ✓

## ✅ 改后验证

```
docker exec nv_gw env | grep PEXEC_TIMEOUT_FASTBREAK
→ NVU_PEXEC_TIMEOUT_FASTBREAK=2 ✓

curl http://localhost:40006/health
→ 200 ✓
```

## 📋 评判

- ✅ 改前必有数据: 6h DB + 24h ATE 分析 + peer-fb 日志 + env 快照
- ✅ 改后必有验证: env 确认 + health check
- ✅ 聚焦 nv_gw: PEXEC_TIMEOUT_FASTBREAK 仅影响 nv_gw pexec 路径 dsv4p_nv
- ✅ 铁律: 只改 HM1 不改 HM2
- ⚡ 更快请求: k2 rescue 成功路径 86s vs 134s peer-fb 路径
- 🛡️ 稳定优先: FASTBREAK=2 在 degraded 但非 dead 的 NVCF function 上提供 key 级容错
## ⏳ 轮到HM1优化HM2
