# HM2 Optimize HM1 — Round R1275

## 触发分析

cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发（连续第9轮NOP/优化链）
- HM1 git log 为空 → HM1 未提交任何新内容
- 本次触发虽为误触发，但数据发现真实优化机会（见下）

## 数据概览 (6h 窗口, 容器重启后)

| 指标 | 值 |
|------|-----|
| 总请求 | 67 |
| 成功 (200) | 52 |
| 失败 | 15 |
| 总体 SR | 77.6% |

### 按模型拆分

| 模型 | 总计 | 成功 | 失败 | SR | zombie | ATE | IncompleteRead |
|------|------|------|------|-----|--------|-----|----------------|
| dsv4p_nv | 13 | 10 | 3 | 76.9% | 0 | 3 | 0 |
| glm5_2_nv | 54 | 42 | 12 | 77.8% | 11 | 0 | 1 |

### 失败明细

| 错误类型 | 数量 | 平均延迟 |
|----------|------|----------|
| zombie_empty_completion (glm5_2_nv) | 11 | 10,032ms |
| all_tiers_exhausted (dsv4p_nv) | 3 | 72,019ms |
| NVStream_IncompleteRead (glm5_2_nv) | 1 | 24,019ms |

### dsv4p_nv ATE 详细分析

- 3 ATE, 全部 `fallback_actually_attempted=false`
- 平均延迟 72,019ms ≈ NVU_TIER_BUDGET_DSV4P_NV=72s → tier budget cap hit
- 0 NV-TIER-FAIL 日志 → tier 静默耗尽
- 0 NV-MS-FB 日志 → ms_gw 从未被调用
- 根因: **NVU_MS_GW_FALLBACK_MODELMAP 缺少 dsv4p_nv:dsv4p_ms 映射**

### glm5_2_nv zombie 分析

- 11 zombie_empty_completion (NVCF content-filter stop, 207K-211K input, 8-12 chars output)
- 代码级 zombie 检测正确 (3-16s 快速 abort vs 旧 96s 超时)
- 0 tier_attempts, 0 ATE → glm5_2_nv 仅 zombie 失败，NVCF 函数健康
- **不可配置修复** — NVCF 上游模型行为

### 其他关键数据

- 0 tier_attempts (6h) → 无 per-key timeout/429/SSLEOF
- 0 NV-GLOBAL-COOLDOWN, 0 NV-EMPTY, 0 NV-TIER-FAIL
- FALLBACK_GRAPH={} → (no fallback, 3model) 为预期状态
- ms_gw dsv4p_ms: 24h 内 17 次成功确认 (MS-OK-STREAM + MS-OK status=200), 10 variants, DeepSeek-V4-Pro via ModelScope
- KEY_AUTHFAIL_COOLDOWN_S=60 ✓
- 全部其他参数 floor/optimal

## 决策与变更

### 变更: NVU_MS_GW_FALLBACK_MODELMAP 添加 dsv4p_nv:dsv4p_ms

**改前**: `"glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms"`
**改后**: `"glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms"`

**证据链**:
1. dsv4p_nv 3 ATE/6h, 全部 `fallback_actually_attempted=false` — ms_gw 从未尝试
2. MODELMAP 缺少 `dsv4p_nv` → 代码不触发 ms_gw 兜底
3. ms_gw dsv4p_ms 确认可用: MODEL_REGISTRY 含 `dsv4p_ms`, 10 variants, 17 次日志成功
4. 预算安全: BUDGET=210 - TIER_BUDGET_DSV4P_NV=72 = 138s headroom >> dsv4p_ms 典型延迟 (30-90s)
5. MS_GW_FALLBACK_TIMEOUT=200 > BUDGET → BUDGET 先于 fallback timeout 触发，138s 足够

**预期效果**:
- dsv4p_nv ATE 触发 ms_gw dsv4p_ms 兜底 → 3/6h ATE 中部分可被 ModelScope DeepSeek-V4-Pro 救援
- 零风险: 若 dsv4p_ms 失败，peer-fb 到 HM2 仍可用 (NVU_PEER_FB_SKIP_MODELS 为空)
- **铁律**: 只改 HM1，不改 HM2

### 其他参数: 零变更

- UPSTREAM_TIMEOUT=66 ✓ (floor)
- TIER_TIMEOUT_BUDGET_S=210 ✓
- FASTBREAK 全部 floor (PEXEC=1, INTEGRATE=1, EMPTY=2) ✓
- TIER_COOLDOWN_S=15 ✓
- KEY_COOLDOWN_S=25 ✓
- NVU_SSLEOF_RETRY_DELAY_S=1.0 ✓
- NVU_TIER_BUDGET_DSV4P_NV=72 ✓
- NVU_TIER_BUDGET_GLM5_2_NV=96 ✓
- 无 zombie 可修复参数 — zombie 为 NVCF content-filter 代码级检测，不可配置修复

### glm5_2_nv zombie: NOP

11 zombie_empty_completion 为 NVCF glm5_2 函数 content-filter stop (finish_reason=stop, content_chars<50, input≥207K)。
代码级 zombie 检测 (NV-ZOMBIE-EMPTY → NV-ZOMBIE-ERROR-CHUNK → RST abort) 正确运行，3-16s 快速失败远优于旧 96s NVStream_TimeoutError。
不可配置修复 — 上游模型行为。

## 验证

- compose 编辑: `sed -i` 修改 line 671, 备份 `.bak.R1275`
- `docker compose up -d nv_gw`: Container nv_gw Recreated + Started ✓
- `docker exec nv_gw env | grep MODELMAP`: 含 `dsv4p_nv:dsv4p_ms` ✓
- `/health`: status=ok ✓
- ms_gw: `['glm5_2_ms', 'dsv4p_ms', 'kimi_ms']` — dsv4p_ms active ✓
- 新 compose md5: `28795fbe68f521457c09577f5da872ba` (前: `0dff5e071f93fc571baa92c55a21becc`)

## 评判

| 维度 | 评估 |
|------|------|
| 更少报错 | dsv4p_nv ATE (3/6h) 获得 ms_gw 兜底路径，预期部分被救援 → 减少 ATE |
| 更快请求 | 零延迟退化: BUDGET=210 不变, TIER_BUDGET=72 不变 |
| 超低延迟 | 不变 (UPSTREAM=66, FASTBREAK=1, zombie 3-16s 不受影响) |
| 稳定优先 | 单参数变更 (MODELMAP 扩展), 零风险: ms_gw dsv4p_ms 验证可用, peer-fb 兜底 |
| **铁律** | **只改 HM1 不改 HM2** — compose 编辑 + 容器重启仅 HM1 |

## ⏳ 轮到HM1优化HM2
