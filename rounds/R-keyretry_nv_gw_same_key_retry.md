# R-keyretry: NVCF key1 同 key 间隔重试 3 次 (2s→4s→8s)

**时间**: 2026-07-27 09:26 CST
**作者**: opc_uname (HM1, 用户直接指令)
**部署**: HM2 only

## 背景

用户要求: cc4101-primary 固定绑 key1, NVCF 失败后不应立刻 fallback ms_gw,
应同 key1 间隔重试 3 次 (2s→4s→8s), 3 次全败才 fallback. 要真实数据日志.

## 改前数据 (6h, R-buffer-post6 记录)

- cc4101-primary: 383×200 / 3×buffer_exhausted → SR 99.2% (但含 ms_gw fallback)
- NVCF primary SR: 152/389 = 39.1% (61.9% 请求 fallback 到 ms_gw)
- ms_gw 兜底全 200, 整体 SR 99.2%, 但 NVCF 利用率只有 39.1%

## 改动

### config.py
- 新增 `NVU_CALLER_RETRY` (int, env, 默认 0=禁用)
- 新增 `NVU_CALLER_RETRY_INTERVALS` (list, env, 默认 "2,4,8")

### upstream.py `_try_glm52_mode_chain`
- caller-bound 分支: `_chain_max_attempts` 从 1 → `NVU_CALLER_RETRY` (3)
- 同 key 不轮转 (`key_idx = start_key` 固定)
- 重试间隔: 第 2 次 sleep 2s, 第 3 次 sleep 4s (按 NVU_CALLER_RETRY_INTERVALS)
- 跳过 key cooldown 检查 (cooldown 会阻断同 key 重试)
- `_glm52_single_attempt` 传 `attempt_idx=attempt` (触发指数退避 timeout 60/120/240)
- 每次重试记 `NV-GLM52-RETRY-SLEEP` + `NV-GLM52-KEY-FAULT` (含 attempt=N/3, remaining=M)

### docker-compose.yml
- `NVU_CALLER_RETRY=3`
- `NVU_CALLER_RETRY_INTERVALS=2,4,8`

### 备份
- upstream.py.bak.R-keyretry
- config.py.bak.R-keyretry
- docker-compose.yml.bak.R-keyretry

## 验证

- py_compile OK ✓
- health OK ✓
- env 生效 ✓
- 实测 req=644bbd2b:
  - CALLER_BIND → k2 (same-key retry=3, intervals=[2.0, 4.0, 8.0]s)
  - attempt 1/3 → fault → sleep 2s → attempt 2/3 → fault → sleep 4s → attempt 3/3 → fault → CHAIN-FAIL → ms_gw fallback ✓
- 日志标签完整: NV-GLM52-CHAIN / NV-GLM52-RETRY-SLEEP / NV-GLM52-KEY-FAULT / NV-GLM52-CHAIN-FAIL

## 期望

- NVCF key1 间歇故障 (网络抖动/瞬时 429) 在 2-8s 间隔后重试可能成功
- primary SR 从 39.1% 提升 (目标: >50%)
- ms_gw fallback 率从 61.9% 下降
- 若 NVCF 持续故障 (账户级限流/端点死), 重试也救不回, SR 不变 → 记数据 NOP

## 风险

- 3 次重试 + 间隔 (2+4+8=14s) 增加单请求 NVCF 层耗时
- chain budget (NVU_TIER_BUDGET_GLM5_2_NV=230s) 可能限制第 3 次重试的机会
- buffer 层 (580s 总预算) 可吸收 NVCF 层增加的耗时, 不影响 CC 端体验

## 回滚

- env: `NVU_CALLER_RETRY=0` (即刻生效, 不改代码)
- 源码: `cp upstream.py.bak.R-keyretry upstream.py && docker compose restart nv_gw`
