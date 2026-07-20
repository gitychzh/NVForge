# R2022 — HM2→HM1 优化回合

## 数据采集 (HM1 @ 100.109.153.83)

### 6h 请求统计
- **总请求**: 32
- **成功**: 27 (84.4% SR)
- **失败**: 5 (15.6% zombie_empty_completion, 全部 glm5_2_nv)
- **0 real ATE** (17 phantom ATE 全部 status=200, no real 502 ATE)
- **0 peer-fallback events** (6h peer_fb_total=0, peer_fb_success=0, peer_fb_fail=0)
- **key_cycle_429s**: 15/32 (46.9%) — 近半数请求第一key被429限流

### 6h 延迟 (成功请求)
- **glm5_2_nv**: avg=6,045ms, min=1,696ms, max=28,697ms (27 requests)

### 30min 窗口
- 2 req, 1 OK / 1 zombie (slow window, low traffic)

### 容器状态
- **nv_gw**: 正常运行, 刚重启 (R2021 deploy)
- **KEY_COOLDOWN_S=54, TIER_COOLDOWN_S=54** (R2020→R2021)
- **TIER_TIMEOUT_BUDGET_S=153**
- **PEER_FALLBACK_TIMEOUT=122, UPSTREAM_TIMEOUT=28**
- **NVU_TIER_BUDGET_GLM5_2_NV=20**

## 问题诊断

**核心问题**: 47% key_cycle_429s rate (15/32 req) — 第一key被NVCF 429限流。KEY_COOLDOWN_S=54s 时key冷却时间偏长，导致key恢复慢，流量集中到剩余key→连锁429。

**根因**: KEY_COOLDOWN_S=54s 在5-key池低流量(~5.3req/h)场景下偏保守。R2020→R2021已从56→54，但429率仍居高不下。需加速key恢复。

## 优化方案

**单参数对**: KEY_COOLDOWN_S: 54→50 (-4s), TIER_COOLDOWN_S: 54→50 (-4s)

**评判标准**:
- **更少报错**: 降低429率 → 减少key轮转耗时 → 降低zombie_empty_completion风险
- **更快请求**: 减少key_cycle等待 → 降低p50延迟
- **超低延迟**: 429越少等待越少
- **稳定优先**: BUDGET安全: 50+50=100 << 153 (53s安全余量); 5key低流量无key exhaustion风险

**约束检查**:
- peer-fb constraint: UPSTREAM=28 + PEER=122 = 150 < 153 ✓ (peer-fb可触发)
- 30min: 0 real ATE → 无rescue path风险
- 铁律: 只改HM1不改HM2 ✓

## 执行

```bash
# HM1 compose nv_gw section
sed -i '500s|KEY_COOLDOWN_S: "54".*|KEY_COOLDOWN_S: "50"  # R2022 ...|' compose.yml
sed -i '505s|TIER_COOLDOWN_S: "54".*|TIER_COOLDOWN_S: "50"  # R2022 ...|' compose.yml
docker compose up -d nv_gw
```

## 验证

- **Live env**: KEY_COOLDOWN_S=50, TIER_COOLDOWN_S=50 ✓
- **容器运行**: nv_gw up, listening on 40006 ✓
- **其他参数不变**: PEER_FALLBACK=122, BUDGET=153, UPSTREAM=28 ✓
## ⏳ 轮到HM1优化HM2
