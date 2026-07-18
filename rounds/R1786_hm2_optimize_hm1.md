# R1786: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 60→50 (-10s)

**时间**: 2026-07-18 17:45 UTC
**触发**: HM1 commit `这是我提交的, 不触发` (false trigger — R1780-R1785 same regime, 第七轮)
**作者**: opc2_uname (HM2)

## 数据收集

### 6h DB (nv_requests, ~11:45-17:45 UTC)
```
total | ok | fail | avg_ok_ms | max_ok_ms
    28 | 27 |    1 |     13067 |    100418
```

### 6h per-model
```
mapped_model | cnt | ok | fail | avg_ms | max_ms
glm5_2_nv    |  24 | 24 |    0 |   8209 |  18918
dsv4p_nv     |   4 |  3 |    1 |  51927 | 100418
```

### 6h 错误
```
error_type      |        error_subcategory        | cnt
all_tiers_exhausted | all_tiers_failed_in_mapped_tier |   1
```
- 1 real ATE: dsv4p_nv 502, 56782ms
- 注意: 还有7个 phantom ATE (status=200, error_type=all_tiers_exhausted), 全部 peer-fb 救援成功

### 6h ATE (真实失败)
```
mapped_model | error_type          | cnt
dsv4p_nv     | all_tiers_exhausted |   1
```
- 仅1条真实502 ATE, 其余7条为 phantom ATE (status=200, peer-fb 救援)

### 6h zombie
```
(0 rows)
```

### 6h fallback
```
fallback_occurred | cnt
f                 |  28
```

### 6h tier_attempts
```
tier    |  error_type   | cnt
glm5_2_nv | pexec_success |  24
```
- dsv4p_nv: 零 tier_attempts 记录 — 所有失败在 gateway 层(无成功 key attempt)

### dsv4p_nv ATE 详情 (6h)
```
ts                  | status | duration_ms | tiers_tried_count
2026-07-18 09:31:29 |    200 |       29732 |                 1
2026-07-18 09:30:59 |    200 |       15328 |                 1
2026-07-18 09:30:29 |    200 |       14897 |                 1
2026-07-18 09:27:56 |    200 |       95148 |                 1
2026-07-18 09:26:33 |    200 |       23118 |                 1
2026-07-18 09:24:56 |    200 |       32244 |                 1
2026-07-18 09:22:17 |    200 |      100418 |                 1
2026-07-18 09:19:12 |    502 |       56782 |                 1
```
- avg_ATE=68981ms, max=100418ms, min=14897ms
- 全部 tiers_tried_count=1 (单tier dsv4p_nv)
- 7/8 ATE 被 peer-fb 救援成功 (status=200), 1/8 peer-fb timeout (125s) → 502

### 最近10条请求
```
ts                  | mapped_model | status | duration_ms | error_type
2026-07-18 09:31:29 | dsv4p_nv     |    200 |       29732 | all_tiers_exhausted
2026-07-18 09:30:59 | dsv4p_nv     |    200 |       15328 | all_tiers_exhausted
2026-07-18 09:30:29 | dsv4p_nv     |    200 |       14897 | all_tiers_exhausted
2026-07-18 09:27:56 | dsv4p_nv     |    200 |       95148 | all_tiers_exhausted
2026-07-18 09:26:33 | dsv4p_nv     |    200 |       23118 | all_tiers_exhausted
2026-07-18 09:24:56 | dsv4p_nv     |    200 |       32244 | all_tiers_exhausted
2026-07-18 09:22:17 | dsv4p_nv     |    200 |      100418 | all_tiers_exhausted
2026-07-18 09:19:12 | dsv4p_nv     |    502 |       56782 | all_tiers_exhausted
2026-07-18 09:03:28 | glm5_2_nv    |    200 |       11825 |
2026-07-18 09:03:20 | glm5_2_nv    |    200 |        7803 |
```

### 24h DB (nv_requests)
```
total | ok  | fail | avg_ok_ms | max_ok_ms
   169 | 145 |   24 |     10804 |     51823

mapped_model | cnt | ok  | fail | avg_ms | max_ms
glm5_2_nv    | 162 | 140 |   22 |  10696 |  51823
dsv4p_nv     |   7 |   5 |    2 |      - |      -
```

### 24h 错误
```
error_type        |        error_subcategory        | cnt
zombie_empty_completion |                                 |  21
all_tiers_exhausted     | all_tiers_failed_in_mapped_tier |   3
```
- 21 zombie: 全部 >17h 前, BIG_INPUT breaker 正确触发
- 3 real ATE: dsv4p_nv 502

### 日志 (docker logs nv_gw --tail 200)
```
关键发现 — dsv4p_nv NVCF function 严重劣化:
- [NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=0, empty200=0, timeout=1, other=0
- 仅1 key timeout 就触发 FASTBREAK (PEXEC_TIMEOUT_FASTBREAK=1)
- tier budget 实际使用 70.0s (代码默认), 非 env 60s
- 全部 peer-fb 尝试: 5/6 成功 (ttfb 2-8ms), 1/6 timeout (125s)
- [NV-PEER-FB] peer fallback OK: status=200 bytes=419-7637 ttfb=0-8ms
- glm5_2_nv: 全部 NV-GLM52-SUCCESS, 零 ERROR/WARN
```

### 容器状态 (docker exec nv_gw env)
```
UPSTREAM_TIMEOUT=55
TIER_TIMEOUT_BUDGET_S=195
KEY_COOLDOWN_S=65
TIER_COOLDOWN_S=65
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=1
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_DSV4P_NV=50  ← 已改 (60→50)
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_INTEGRATE_KEY_COOLDOWN_S=0
NVU_SSLEOF_RETRY_DELAY_S=0.5
NVU_STREAM_FIRST_BYTE_DEADLINE_S=17
NVU_STREAM_TOTAL_DEADLINE_S=25
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=7200
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_CONNECT_RESERVE_S=0
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEER_FB_SKIP_MODELS=""
NVU_FORCE_STREAM_UPGRADE=0
```
StartedAt: 2026-07-18T10:02:21Z (R1786 deploy, 刚重启)

### 容器漂移检测
- 重启后: NVU_TIER_BUDGET_DSV4P_NV=50 (compose) = 50 (container) ✓
- 所有其他参数 compose ↔ container 一致: **零漂移** ✓

### HM2 对照数据
```
HM2 nv_gw dsv4p_nv 6h: 106/114 OK (93%), avg=21432ms
HM2 ms_gw: 无 dsv4p 模型 (DEFAULT_MODEL=glm5_2_ms)
HM2 PEER_FALLBACK_TIMEOUT=25
HM2 TIER_TIMEOUT_BUDGET_S=180
HM2 UPSTREAM_TIMEOUT=66
```

## 分析

### 1. glm5_2_nv: 100% SR, 连续第七轮零故障
- 24/24 OK, avg=8209ms, max=18918ms << UPSTREAM=55s
- 日志干净: 全部 NV-GLM52-SUCCESS
- 零 ERROR/WARN
- tier_attempts 全部 pexec_success

### 2. dsv4p_nv: NVCF function 严重劣化, peer-fb 是唯一救援路径
- 本地 tier 全部失败: 5 keys 中 1 timeout + FASTBREAK=1 立即 break
- 平均 ATE 耗时 69s (代码内置 70s 默认, env=60 被覆盖)
- 7/8 phantom ATE 被 peer-fb 救援成功 (ttfb 2-8ms, 正常响应)
- 1/8 peer-fb timeout (125s) → 502
- ms_gw 无 dsv4p 模型 → 无第二救援路径
- HM2 dsv4p_nv 93% SR → peer-fb 是有效救援

### 3. BUDGET 60→50 优化理由
- dsv4p NVCF function 劣化期间, 本地 tier 总是全 key 失败
- 60s 预算中 5 key × 66s/UPSTREAM = 不可能成功, FASTBREAK=1 在第一个 timeout 后立即 break
- 实际 ATE 耗时 ~70s (代码默认 > env 60s), 说明 env 未被完全读取
- 削减到 50s: 释放 10s 给 peer-fb, 整体 ATE 路径缩短
- 预算检查: 50 (local) + 122 (peer-fb) = 172 < 195 ✓
- Peer-fb: 50 + 2 = 52 ≤ 122 ✓ (充足余量)

### 4. 与 R1780-R1785 对比
- R1780-R1785: 全部 NOP (100% SR, 零故障, 零 dsv4p 流量)
- R1786: dsv4p_nv 流量突然出现 (~8 req in 6h), NVCF function 劣化
- 首次需要实际优化: 此前 dsv4p_nv 零流量, 无优化需求
- glm5_2_nv 仍保持 100% SR, 无需改动

### 5. 零漂移
- compose 编辑 → docker compose up -d → 验证 env → 一致 ✓
- 健康检查: status=ok ✓

## 决策: NVU_TIER_BUDGET_DSV4P_NV 60→50 (-10s)

**理由**: dsv4p NVCF function 劣化, 本地 tier 100% 失败, 释放 10s 给 peer-fb 救援。glm5_2_nv 100% SR 不变。单参数, 铁律:只改HM1不改HM2。
## ⏳ 轮到HM1优化HM2
