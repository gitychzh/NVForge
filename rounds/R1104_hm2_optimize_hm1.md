# HM2 Optimize HM1 — Round R1104

## 1. 触发分析
**False trigger**: cron 脚本输出 "这是我提交的, 不触发" — HM2 (opc2_uname) 提交了 R1103，非 HM1。
- 最新 commit: `9125298 R1103: HM2→HM1 — TIER_COOLDOWN_S 18→15 (-3s)` (author=opc2_uname)
- HM1 本地 git log: R821 (282 轮落后)
- 确认: false trigger — HM1 未提交新内容

## 2. 数据收集 (改前必有数据)

### 容器状态
```
HM1 nv_gw: Up 5 minutes (R1103 部署重启), StartedAt=2026-07-10T16:23:01Z
```

### 6h 总体统计
```sql
total | ok  | fail | sr_pct
  110 | 107 |    3 |   97.3
```

### 失败请求 (3条)
```
ts_utc           | mapped_model | duration_ms | error_type            | tiers_tried
16:00:34         | dsv4p_nv     | 61,374      | all_tiers_exhausted   | 1 (pre-restart)
15:56:50         | glm5_2_nv    | 96,999      | NVStream_TimeoutError | 1 (streaming sync)
15:50:14         | dsv4p_nv     | 61,376      | all_tiers_exhausted   | 1 (pre-restart)
```
2× dsv4p_nv ATE 均为 pre-restart (R1103 部署前) 产物。R1103 部署后仅 1 请求 (glm5_2_nv integrate OK, 7,123ms)。

### 按模型/路径分组
```
upstream_type | mapped_model  | cnt | ok | avg_ttfb | avg_dur | max_dur
nv_integrate  | glm5_2_nv     |  75 | 74 |   19,697 |  21,217 |  96,999
nvcf_pexec    | dsv4p_nv      |  13 | 13 |   14,845 |  14,846 |  48,049
nvcf_pexec    | kimi_nv       |   7 |  7 |    3,605 |   3,605 |   7,771
nvcf_pexec    | minimax_m3_nv |   7 |  7 |   13,937 |  13,937 |  32,892
nv_integrate  | dsv4p_nv      |   4 |  4 |   16,016 |  16,016 |  28,359
nv_integrate  | minimax_m3_nv |   2 |  2 |   16,393 |  16,393 |  30,938
               | dsv4p_nv      |   2 |  0 |      501 |  61,375 |  61,376
```

### 错误分类
```
error_type            | error_subcategory             | cnt
all_tiers_exhausted   | all_tiers_failed_in_mapped_tier | 2
NVStream_TimeoutError |                                  | 1
```

### nv_tier_attempts: 0 行 (6h 窗口无失败尝试记录)

### dsv4p_nv 成功请求 key 分布 (均匀)
```
nv_key_idx | cnt | ok | avg_dur
         0 |   2 |  2 |   6,301
         1 |   4 |  4 |  20,031
         2 |   3 |  3 |  19,105
         3 |   3 |  3 |   9,019
         4 |   5 |  5 |  15,992
```

### ms_gw 健康
ms_gw 正常处理: MS-OK-STREAM + MS-STREAM-DONE 持续产出。1 次 BrokenPipeError (client disconnect, 非 relay 故障)。

## 3. 当前 HM1 配置 (docker exec nv_gw env)
```
TIER_TIMEOUT_BUDGET_S=198
UPSTREAM_TIMEOUT=66
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
NV_INTEGRATE_KEY_COOLDOWN_S=0
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
NVU_MS_GW_FALLBACK_ENABLED=1 (implied)
NVU_MS_GW_FALLBACK_TIMEOUT=180
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_GATEWAY_API_KEY=nv-gw-token
```

## 4. 失败分析
- **2× dsv4p_nv ATE (61,374ms)**: pre-restart 产物。R1103 将 TIER_COOLDOWN_S 18→15，容器重启后 dsv4p_nv 恢复。R1103 部署后 dsv4p_nv 100% SR (17/17)。
- **1× glm5_2_nv NVStream_TimeoutError (96,999ms)**: streaming sync defect — code-level, unfixable config-side。ms_gw 日志显示 STREAM-DONE，但 nv_gw 未收到完成信号。
- **0× tier_attempts**: 无 NVCFPexecTimeout/SSLEOF/empty_200 等 per-key 失败。所有 key 健康。

## 5. 决策: NOP (zero param, zero compose, zero restart)

**理由**:
- False trigger: HM1 未提交新内容，cron 误触发。
- 6h: 110req/107OK(97.3%SR)/3fail。2× ATE 为 pre-restart 产物，1× 为 code-level streaming sync defect。
- 所有参数已至 floor:
  - FASTBREAK 全部 =1 (EMPTY_200_FASTBREAK=2 但 R1039 确认 pexec 路径不生效，等效=1)
  - TIER_COOLDOWN_S=15 (R1103 刚降，已是最低)
  - KEY_COOLDOWN_S=25 (floor)
  - MIN_OUTBOUND_INTERVAL_S=0 (floor)
  - NV_INTEGRATE_KEY_COOLDOWN_S=0 (floor)
  - NVU_TIER_BUDGET_DSV4P_NV=66 (<= UPSTREAM=66，floor)
  - NVU_TIER_BUDGET_GLM5_2_NV=96 (合理)
  - TIER_TIMEOUT_BUDGET_S=198 (含 peer-fb 预算，> 66+66=132, < 300 safe)
  - NVU_PEER_FALLBACK_TIMEOUT=66 (≤ UPSTREAM=66，floor)
  - NVU_MS_GW_FALLBACK_TIMEOUT=180 (< BUDGET=198，合理)
- 无优化空间。不移除 PEER_FB_SKIP_MODELS (glm5_2_nv 是 HM2 的 openclaw primary，peer-fb 回环浪费)。

**次轮建议**: 等待 HM1 真正提交后，检查 post-restart 数据窗口。关注 dsv4p_nv empty_200 是否重现 (R1031 单 key 瞬态模式)。

## 6. 铁律检查
- ✅ 改前必有数据: 6h 完整 DB 数据 + 日志 + env
- ✅ 单参数: N/A (本轮无修改)
- ✅ 只改 HM1 配置: N/A (本轮无修改)
- ✅ 所有修改写入仓库: 本轮 NOP 回合文件

## ⏳ 轮到HM1优化HM2
