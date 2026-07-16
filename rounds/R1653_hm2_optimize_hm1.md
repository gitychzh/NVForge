# R1653 (HM2→HM1): NOP — insufficient post-change data for dsv4p BUDGET=90

## 数据 (6h, HM1 nv_gw restart 2026-07-16 20:49 UTC)

```sql
-- 6h 总览
SELECT COUNT(*) FILTER (WHERE status>=200 AND status<300) as ok,
       COUNT(*) FILTER (WHERE status<200 OR status>=300) as fail,
       COUNT(*) as total
FROM nv_requests WHERE ts > NOW() - INTERVAL '6 hours';
-- 16 OK / 14 fail / 30 total (53.3% SR)

-- 错误分类
SELECT mapped_model, error_type, error_subcategory, COUNT(*) as cnt
FROM nv_requests WHERE (status<200 OR status>=300) AND ts > NOW() - INTERVAL '6 hours'
GROUP BY mapped_model, error_type, error_subcategory ORDER BY cnt DESC;
-- glm5_2_nv | zombie_empty_completion |     | 9
-- dsv4p_nv  | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier | 5

-- 按模型
SELECT mapped_model, COUNT(*) FILTER (WHERE status>=200 AND status<300) as ok,
       COUNT(*) FILTER (WHERE status<200 OR status>=300) as fail,
       ROUND(AVG(duration_ms) FILTER (WHERE status>=200 AND status<300)) as avg_ok_ms
FROM nv_requests WHERE ts > NOW() - INTERVAL '6 hours'
GROUP BY mapped_model;
-- dsv4p_nv:  7 OK / 5 ATE, avg OK = 24,555ms
-- glm5_2_nv: 9 OK / 9 fail, avg OK = 6,482ms
```

### dsv4p ATE时间线 (全部pre-R1652)

```
ts                                | duration_ms | tiers_tried
2026-07-16 18:04:07.695888+00    | 64280       | 1
2026-07-16 18:03:58.438997+00    | 61652       | 1
2026-07-16 18:02:56.412244+00    | 61533       | 1
2026-07-16 18:01:45.752138+00    | 61822       | 1
2026-07-16 18:00:40.607973+00    | 62107       | 1
```

- 全部在 18:00-18:04 UTC，容器重启前 (20:49 UTC)
- 旧 BUDGET=76 下: 61.5-64.3s 用尽budget后abort
- tiers_tried=1: 仅试了 dsv4p_nv tier，peer-fb 未触发 (budget 76s 先砍)
- Post-R1652 (BUDGET=90): **ZERO dsv4p ATE** — BUDGET=90 需要更多观察

### 429 分析

```sql
SELECT key_cycle_429s, COUNT(*) FROM nv_requests
WHERE ts > NOW() - INTERVAL '6 hours' GROUP BY key_cycle_429s;
-- key_cycle_429s=0: 12 req
-- key_cycle_429s=1: 18 req (60% — single-key 429, 非级联)
```

18/30 req 有单次key 429 (60%)，但无级联 (无 multi-key 429 链)。KEY_COOLDOWN=60=TIER_COOLDOWN=60 对齐，KEY≥TIER 铁律满足。

### HM1 当前 env (docker exec nv_gw)

```
NVU_TIER_BUDGET_DSV4P_NV=90       # R1652: 76→90
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_TIMEOUT_BUDGET_S=195
UPSTREAM_TIMEOUT=66
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FALLBACK_TIMEOUT=72
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_SSLEOF_RETRY_DELAY_S=0.5
NVU_PEER_FB_SKIP_MODELS=
```

### HM2 peer budgets (for cross-reference)

```
NVU_TIER_BUDGET_DSV4P_NV=70       # HM2 compose
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_PEER_FALLBACK_TIMEOUT=25      # HM2→HM1
```

## 分析

### 可fix的问题: 0个

1. **glm5_2 zombie_empty_completion (9/30, 30%)**: NVCF server-side content-filter 返回空completion。典型zombie模式: 5-10s内返回200空body。非本地配置可修。

2. **dsv4p ATE (5/30, 16.7%)**: 全部pre-R1652 (旧BUDGET=76)。Post-R1652 ZERO dsv4p ATE。BUDGET=90 需要24h+ dsv4p流量积累才能判断是否充分。

3. **key_cycle_429s=1 (18/30, 60%)**: 单次key 429，非级联。KEY_COOLDOWN=60=TIER_COOLDOWN=60 满足 KEY≥TIER 铁律。单IP架构下60%单key 429率是NVCF rate-limit的固有特征，加大cooldown会拖慢成功路径。

### 所有参数状态

| 参数 | 当前值 | 状态 |
|------|--------|------|
| KEY_COOLDOWN_S | 60 | floor (KEY=TIER铁律) |
| TIER_COOLDOWN_S | 60 | floor (KEY=TIER铁律) |
| NVU_TIER_BUDGET_DSV4P_NV | 90 | R1652刚部署，待观察 |
| NVU_TIER_BUDGET_GLM5_2_NV | 120 | 2×mode切换，稳定 |
| TIER_TIMEOUT_BUDGET_S | 195 | 90+72=162<195 ✓ |
| UPSTREAM_TIMEOUT | 66 | floor (NVCFPexecTimeout max~62s) |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned with UPSTREAM |
| NVU_PEER_FALLBACK_TIMEOUT | 72 | HM2 BUDGET=70+2=72 ✓ |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | appropriate |
| NVU_SSLEOF_RETRY_DELAY_S | 0.5 | floor |

### 为何不继续调

- R1652 BUDGET 76→90 刚部署 (restart 20:49 UTC)，post-restart仅5个glm5_2请求，0个dsv4p
- dsv4p BUDGET=90 需要真实dsv4p流量验证 (至少24h或10+dsv4p请求)
- 所有其他参数已在floor: KEY_COOLDOWN=60 (不可再减，会破KEY≥TIER), UPSTREAM=66 (不可再减，接近NVCFPexecTimeout max=62s), MIN_OUTBOUND=0, CONNECT_RESERVE=0, NV_INTEGRATE_KEY=0
- 当前失败全为upstream/NVCF问题，非本地配置可修

## 决策: NOP

- 零参数变更
- 让R1652 BUDGET=90观察至少24h+ dsv4p流量
- 下次轮到时重评估: 若有dsv4p ATE复发 → 检查peer-fb是否触发 + 是否需调BUDGET
- 若zombie持续高发 → 考虑ms_gw fallback调整 (但zombie是NVCF server-side)

## 验证

- ✅ 改前必有数据: 6h DB + tier_attempts + env + peer-fb日志
- ✅ 改后必有验证: N/A
- ✅ 聚焦 nv_gw: 仅分析 nv_gw 链路
- ✅ 所有修改写入仓库: 本轮 NOP 仍记录
- ✅ 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
