# HM2 Optimize HM1 — Round R1449

## 1. 触发判定
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2, R1448)
- HM1 本地 git log 停留在 R1206 (243 轮落后)
- **判定: 误触发** (double-dispatch, 54th chain of R1395)

## 2. HM1 数据采集 (改前必有数据)

### 容器状态
- `nv_gw`: Up 47 minutes (healthy), 重启于 `2026-07-15T10:49:16Z`
- compose md5: `51079b89019ddfb1a08f65e79e847b51` (不同于 R1448 的 `3863a7c1`, R1292 外部循环变更, env vars 完全一致)

### 6h DB 数据 (nv_requests)
- **总计**: 35req / 14OK / 21err → **40.0% SR**
- **按模型**: glm5_2_nv 25/14 56.0%SR (avg 18342ms), dsv4p_nv 10/0 0.0%SR (avg 82725ms)
- **按 upstream**: nv_integrate 24/14 58.3%SR, 空 10/0 0.0%SR (ATE), nvcf_pexec 1/0 (zombie)
- **按小时**: 05:00(1/0), 06:00(5/3 60%), 07:00(5/1 20%), 08:00(5/2 40%), 09:00(8/4 50%), 10:00(6/2 33.3%), 11:00(5/2 40%)

### 错误详情
- `zombie_empty_completion`: 11 (10 glm5_2_nv integrate NVCF content-filter + 1 dsv4p_nv pexec), avg_ichars ~214K, avg_dur ~11s
- `all_tiers_exhausted`: 10 (9 dsv4p_nv 502 avg_dur 89456ms + 1 glm5_2_nv 502 avg_dur 187171ms)
- `NVStream_IncompleteRead`: 0
- tier_attempts: 0 (无 key cycling)
- fallback_occurred: 0 (无 ms_gw 救回)

### ms_gw 信号
- ms_gw: 24req / 20OK → 83.3% SR (ms_gw stream_cycle ModelScope upstream)

### 环境变量 (nv_gw)
```
UPSTREAM_TIMEOUT=66
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_TIER_BUDGET_DSV4P_NV=66
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FALLBACK_TIMEOUT=66
NVU_PEER_FB_SKIP_MODELS=
NV_INTEGRATE_KEY_COOLDOWN_S=0
NV_INTEGRATE_MODELS=glm5_2_nv
```

## 3. 决策分析

### 问题诊断
- **zombie_empty_completion × 11**: NVCF content-filter 行为 (avg input_chars 214K, output 6-17 chars, avg_dur 11s)。不是 nv_gw 配置可修复的问题。
- **all_tiers_exhausted × 10**: dsv4p_nv pexec 上游 504 (NVCF 返回 504 / 上游不可用), 1 个 glm5_2_nv。无 tier_attempts (key-level 未重试), 无 fallback_occurred。
- **ms_gw 24/20 83.3%SR**: ms_gw 正常运作但未触发 fallback (nv_gw 的 ATE 是 key-level 快速失败, 未到达 ms_gw 回退路径)。

### 参数评估
- 所有参数已在 floor/optimal 状态
- 无 config-fixable 错误 (zombie=NVCF 内容过滤, ATE=上游 504, 均非 nv_gw 配置可控)
- 0 tier_attempts, 0 key_cycle_429s → 冷却时间无误调

### 判决
**NOP** — 无可配置优化空间。zombie 和 ATE 均属上游问题 (NVCF content-filter + NVCF 504), 非 nv_gw 参数可调。

## 4. 执行
- 零参数修改
- 零 compose 变更
- 零容器重启
- 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
