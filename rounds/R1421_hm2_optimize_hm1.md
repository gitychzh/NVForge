# HM2 Optimize HM1 — Round R1421

## ⏱️ 时间
2026-07-15 12:35 UTC (cron)

## 🔍 触发分析
cron 脚本输出: `"这是我提交的, 不触发"` — 自提交误触发 (double-dispatch, 577th chain of R1133)
- 最新 commit author = opc2_uname (HM2)
- R1420 已由 pre-run 脚本提交，symlink 已指向 R1420
- 本轮为 double-dispatch，创建 R1421 作为 chain NOP

## 📊 数据收集 (改前必有数据)

### nv_requests (6h, ~12:35 UTC)
```
total | ok | fail | sr_pct
  32  | 21 |  11  |  65.6
```

### 错误分类
```
error_type              | cnt | avg_dur_ms
zombie_empty_completion |  10 |      10755
all_tiers_exhausted     |   1 |     106052
```

### 逐小时成功率
```
hour (UTC)  | total | ok | fail | sr_pct
00:00       |   4   |  4 |   0  | 100.0
01:00       |   6   |  5 |   1  |  83.3
02:00       |   6   |  4 |   2  |  66.7
03:00       |   9   |  5 |   4  |  55.6
04:00       |   7   |  3 |   4  |  42.9
```

### ATE 详情
```
ts                  | model    | status | duration_ms | error_type          | fallback
02:06:05 2026-07-15 | dsv4p_nv | 502    | 106052      | all_tiers_exhausted | false
01:44:20 2026-07-15 | dsv4p_nv | 200    | 6113        | all_tiers_exhausted | true (ms_gw rescued)
```

### tier_attempts (6h): 0

### nv_gw 日志 (最近100行, 过滤error/warn/fail/empty/timeout)
- glm5_2_nv integrate: 全部成功 (k1-k5 first attempt), 延迟 2-10s
- zombie_empty_completion: glm5_2_nv (finish_reason=stop, content_chars=12) + dsv4p_nv (finish_reason=stop, content_chars=3-12)
- NV-ZOMBIE-ERROR-CHUNK: 正确发送 finish_reason=timeout 触发 openclaw fallback
- dsv4p_nv NV-THINKING-TIMEOUT: thinking request stream=True → extended timeout 66s (正常)

### ms_requests (6h)
```
total | ok | fail | sr_pct
  9   |  0 |   9  |   0.0
```
- 全部失败，error_type 均为 NULL
- ms_gw 日志: MS-FASTBREAK consecutive_empty=3 >= 3 breaking, MS-VARIANT-EXHAUSTED cycling variants 3-9
- 原因: Modelscope 后端全部返回 empty_200 (backend-side, not config-fixable)

### ms_gw env
```
EMPTY_200_FASTBREAK_THRESHOLD=3
KEY_COOLDOWN_S=60
UPSTREAM_TIMEOUT=300
```

### nv_gw env (全部参数)
```
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_EMPTY_200_FASTBREAK=2
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_PEER_FB_SKIP_MODELS=
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_TIER_BUDGET_DSV4P_NV=112
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
TIER_COOLDOWN_S=15
TIER_TIMEOUT_BUDGET_S=205
UPSTREAM_TIMEOUT=66
```

### Compose md5
`59dc3c54c49324859d1d31e7e422b31b` (与 R1420 相同，未变化)

## 🧠 分析

### zombie_empty_completion (NVCF content-filter, 不可配置修复)
- glm5_2_nv: finish_reason=stop, content_chars=12, input_chars≈210K — NVCF 内容过滤返回空响应
- dsv4p_nv: finish_reason=stop, content_chars=3-12, input_chars≈210K — 同上
- Gateway 正确检测并发送 finish_reason=timeout error chunk，触发 openclaw fallback
- R1405 修复已生效 (finish_reason=timeout)，openclaw 应能 fallback
- 10 zombie in 6h，与 R1420 (8 zombie) 相当

### ATE dsv4p_nv (单次异常)
- 106s ATE，NVCF 504 gateway timeout，非键级问题
- 无 fallback 触发 (fallback_occurred=false)
- 另一 ATE 被 ms_gw 成功 rescue (01:44, 6.1s, status=200)
- dsv4p_nv BUDGET=112 已足够，单次异常不值得调整

### ms_gw 0% SR (Modelscope 后端问题)
- 9 请求全部失败，error_type=NULL
- ms_gw 日志: EMPTY_200_FASTBREAK_THRESHOLD=3，每个 variant 试 3 keys 后 variant-exhausted
- Modelscope 后端全面 empty_200，非配置修复
- EMPTY_200_FASTBREAK_THRESHOLD 3→1 可节省 ~2 key cycles/variant (~6-10s/req)，但不改变 SR
- ms_gw 不是主要优化目标 (聚焦 nv_gw)，且变动无 SR 改善

### 参数状态
- 全部参数处于 floor/optimal
- UPSTREAM_TIMEOUT=66 (floor)
- TIER_COOLDOWN_S=15 (floor)
- KEY_COOLDOWN_S=25 (floor)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1 (optimal, function-level)
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 (optimal, function-level)
- NVU_EMPTY_200_FASTBREAK=2 (R1039 确认 buggy — pexec path 未生效，但 NVU_PEER_FB_SKIP_MODELS= 已启用 peer-fb rescue)
- NVU_PEER_FB_SKIP_MODELS= (空 — 全部模型可 peer-fb)
- TIER_TIMEOUT_BUDGET_S=205 (充足)
- 0 tier_attempts (零键循环，全键健康)

## ✅ 决策: NOP

**无参数可调整。** 全部参数已处于 floor/optimal。zombie_empty_completion 为 NVCF 内容过滤 (不可配置修复)。ATE 为单次 504 gateway timeout (不可配置修复)。ms_gw 0% SR 为 Modelscope 后端问题 (不可配置修复)。铁律:只改HM1不改HM2。

## ⏳ 轮到HM1优化HM2
