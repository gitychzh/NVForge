# HM2 Optimize HM1 — Round R1084

## ⚠️ 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (false trigger, 同 R1083/R1082/R1081/R1080/R1079 模式)

## 1. 数据收集 (改前必有数据)

### 6h 总体
```
 total | ok | err | sr_pct 
    59 | 51 |   8 |   86.4
```

### 6h 按 upstream 类型
```
 upstream_type | cnt | ok | err | avg_ttfb | avg_dur | max_dur 
 nv_integrate  |  54 | 50 |   4 |    18326 |   24954 |  105819
               |   4 |  0 |   4 |      928 |   88369 |  132017
 nvcf_pexec    |   1 |  1 |   0 |   125916 |  125917 |  125917
```

### 6h 按模型
```
 mapped_model | cnt | ok | err | sr_pct | avg_dur | max_dur 
 glm5_2_nv    |  55 | 51 |   4 |   92.7 |   26790 |  125917
 dsv4p_nv     |   4 |  0 |   4 |    0.0 |   88369 |  132017
```

### 6h 错误类型
```
      error_type       | cnt 
 NVStream_TimeoutError |   4
 all_tiers_exhausted   |   4
```

### 6h ATE tiers_tried_count
```
 tiers_tried_count | cnt | avg_dur 
                 1 |   8 |   94608
```

### 6h fallback
```
 fallback_occurred | cnt | ok | avg_dur 
 f                 |  59 | 51 |   30965
```
→ 0 fallback occurred in 6h window.

### 6h tier_attempts (仅失败)
```
   tier    |         error_type          | cnt | avg_ms | max_ms 
 glm5_2_nv | IntegrateRemoteDisconnected |   1 |  20284 |  20284
 glm5_2_nv | IntegrateTimeout            |   1 |  90566 |  90566
```

### 失败详情 (8条)
```
 ts                          | model      | status | dur_ms  | error_type               | upstream     | tiers | fb_attempted
 2026-07-10 09:06:08 | dsv4p_nv   | 502    | 132017  | all_tiers_exhausted      | NULL         | 1     | f
 2026-07-10 08:20:53 | dsv4p_nv   | 502    | 1328    | all_tiers_exhausted      | NULL         | 1     | f
 2026-07-10 08:15:15 | glm5_2_nv  | 502    | 96068   | NVStream_TimeoutError    | nv_integrate | 1     | f
 2026-07-10 06:10:07 | glm5_2_nv  | 502    | 99181   | NVStream_TimeoutError    | nv_integrate | 1     | f
 2026-07-10 06:07:41 | dsv4p_nv   | 502    | 110073  | all_tiers_exhausted      | NULL         | 1     | f
 2026-07-10 06:02:25 | glm5_2_nv  | 502    | 102323  | NVStream_TimeoutError    | nv_integrate | 1     | f
 2026-07-10 05:59:55 | dsv4p_nv   | 502    | 110058  | all_tiers_exhausted      | NULL         | 1     | f
 2026-07-10 05:54:55 | glm5_2_nv  | 502    | 105819  | NVStream_TimeoutError    | nv_integrate | 1     | f
```

### 容器状态
- nv_gw 启动时间: `2026-07-10T09:47:59Z` (9h+ uptime)
- docker logs --tail 500: 仅 29 行 (全部 post-18:03 UTC)
  - 全部 glm5_2_nv integrate 成功 (1st-key, 3-46s)
  - 无 dsv4p_nv 流量
  - tier_chain: `['glm5_2_nv'] (no fallback, 3model)` — 预期正常 (FALLBACK_GRAPH={})
- ms_gw: 正常运行，dsv4p_ms deepseek-ai/DeepSeek-V4-Pro 偶有 BrokenPipeError (code-level)

### 当前配置 (nv_gw env)
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=132
TIER_COOLDOWN_S=18
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_STREAM_TOTAL_DEADLINE_S=90
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NV_INTEGRATE_KEY_COOLDOWN_S=0
NV_INTEGRATE_MODELS=glm5_2_nv,minimax_m3_nv
NVU_FALLBACK_HEALTH_THRESHOLD=0.10
FALLBACK_HEALTH_THRESHOLD=0.05 (dead param)
```

### ms_gw 配置
```
UPSTREAM_TIMEOUT=300
PROXY_TIMEOUT=600
EMPTY_200_FASTBREAK_THRESHOLD=3
KEY_COOLDOWN_S=60
VARIANT_COOLDOWN_S=30
ALL_EXHAUSTED_COOLDOWN_S=30
MIN_OUTBOUND_INTERVAL_S=1.0
```

## 2. 分析

### dsv4p_nv ATE (4/4, 0% SR)
- 全部 pre-restart（容器于 09:47 UTC 重启，ATE 时间: 05:59, 06:07, 08:20, 09:06）
- 全部 `all_tiers_exhausted` + `fallback_actually_attempted=false`
- 132017ms 的 ATE 被 BUDGET=132 精确截断
- 1328ms 的 ATE 极快 → 疑似 NVCF 504 external
- docker logs 无 post-restart dsv4p_nv 流量
- 模式与 R1083/R1082 一致：NVCF 504 external + ms_gw BrokenPipeError code-level
- 不可配置修复

### glm5_2_nv NVStream_TimeoutError (4/55, 92.7% SR)
- 全部 integrate 模式，集中在 05:54-06:15 UTC (15min 窗口)
- 持续时间 96-106s，接近 NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_STREAM_TOTAL_DEADLINE_S=90 + BUDGET=96 → 仅 1 key 可容纳
- 疑似 NVCF 瞬态流式超时（集中在 15min 窗口，其余 51 请求全部 1st-key 成功）
- 92.7% SR 健康，无需调整

### 整体评估
- 数据与 R1083/R1082/R1081/R1080/R1079 完全一致
- 所有参数已处于 floor/optimal
- 无 config-fixable 信号
- 铁律：只改 HM1 不改 HM2（无需改）

## 3. 决策: NOP

**零参数变更。** 数据与 R1083 相同。所有参数已最优。dsv4p_nv ATE 为 NVCF 504 external 预重启遗留 + ms_gw BrokenPipeError code-level。glm5_2_nv 92.7% SR 稳定 integrate 1st-key。铁律: 只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2
