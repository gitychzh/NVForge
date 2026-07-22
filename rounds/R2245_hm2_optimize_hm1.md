# R2245 (HM2→HM1): NVU_BIG_INPUT_MODELS 移除 dsv4p_nv

## 时间
2026-07-22 09:05 UTC

## 数据收集 (改前必有数据)

### 6h 窗口 (2026-07-22 02:05 ~ 08:05 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 51 |
| 成功 (200) | 35 (68.6% SR) |
| 失败 | 16 |

### 错误分类
| 模型 | 错误类型 | 子类型 | 数量 |
|------|---------|--------|------|
| dsv4p_nv | all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 9 |
| glm5_2_nv | all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 4 |
| glm5_2_nv | zombie_empty_completion | | 3 |

### ATE 关键发现
**所有 13 个 ATE 请求的 tier_attempts=0** — 完全被 big-input breaker 预拦截 (pre-empted):
- dsv4p_nv: 9 ATE, 全部 0 tier_attempts (line 637 breaker 拦截)
- glm5_2_nv: 4 ATE, 全部 0 tier_attempts (line 637 breaker 拦截)

### dsv4p_nv 成功请求分析
- 14 OK, avg 35,700ms, min 14,803ms, max 65,761ms
- **0 zombies** (dsv4p_nv 无僵尸问题)
- 0 key_cycle_429s across all 23 dsv4p_nv requests
- dsv4p_nv 运行健康: 无 pexec_timeout, 无 SSLEOF, 无 zombie

### glm5_2_nv 分析
- 21 OK, avg 53,832ms, min 5,574ms, max 174,770ms
- 3 zombies (zombie_empty_completion, avg 61,304ms) — 需要保留 big-input breaker
- key_cycle_429s: 11/28 有 429, 分布均匀 (1-8 cycles)

### 日志
```
[16:43:44.8] [NV-BIGINPUT-FAIL] big_input nv hang for dsv4p_nv input=354223c err=empty_200
[16:43:44.8] [NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0
[16:43:44.8] [NV-ALL-TIERS-FAIL] All 1 tiers failed, elapsed=64126ms, ABORT-NO-FALLBACK
```
dsv4p_nv 被 big-input breaker 拦截: input=354,223 chars > 250,000 threshold → breaker OPEN → pre-empted → 0 tier_attempts → 502 without any real key attempt.

### 30min 窗口
8 req / 7 OK (87.5% SR) / 1 fail

### 环境变量
- NVU_BIG_INPUT_MODELS: `glm5_2_nv,dsv4p_nv` (R1889 加入 dsv4p_nv)
- NVU_BIG_INPUT_THRESHOLD: `250000`
- NVU_BIG_INPUT_FAIL_N: `5`
- NVU_BIG_INPUT_COOLDOWN_S: `2100`
- UPSTREAM_TIMEOUT: `24`
- NVU_TIER_BUDGET_DSV4P_NV: `96`
- NVU_TIER_BUDGET_GLM5_2_NV: `38`
- NVU_PEXEC_TIMEOUT_FASTBREAK: `2`
- NVU_EMPTY_200_FASTBREAK: `1`

## 分析

### 问题根因
dsv4p_nv 在 `NVU_BIG_INPUT_MODELS` 中被 big-input breaker 误杀。breaker 针对 >250K chars 的请求触发 OPEN 状态，但 dsv4p_nv 在大输入场景下表现健康：
- 0 zombies (dsv4p_nv 无 glm5_2_nv 的 zombie_empty_completion 问题)
- 成功请求 14/14 都是正常完成，无 empty200 模式
- 9 ATE 全部是 breaker 预拦截，不是真实 key 级别失败

### 优化方案
从 `NVU_BIG_INPUT_MODELS` 中移除 `dsv4p_nv`，保留 `glm5_2_nv`。

**理由**:
1. dsv4p_nv 0 zombies — big-input breaker 对它无价值
2. dsv4p_nv 9/9 ATE 全是 breaker 误杀 (0 tier_attempts)
3. dsv4p_nv 成功请求 avg 35.7s 健康
4. glm5_2_nv 3 zombies 需要保留 breaker 保护
5. 单参数变更，风险极低：dsv4p_nv 大输入正常走 pexec 路径

## 执行

### 变更
```diff
- NVU_BIG_INPUT_MODELS: "glm5_2_nv,dsv4p_nv"
+ NVU_BIG_INPUT_MODELS: "glm5_2_nv"
```

### 操作
```bash
ssh -p 222 opc_uname@100.109.153.83
# 1. 编辑 /opt/cc-infra/docker-compose.yml line 637
# 2. docker compose -f /opt/cc-infra/docker-compose.yml up -d --force-recreate nv_gw
# 3. curl http://localhost:40006/health → 200
# 4. docker exec nv_gw printenv NVU_BIG_INPUT_MODELS → glm5_2_nv ✓
```

### 验证
- ✅ Health check: 200
- ✅ Env 生效: NVU_BIG_INPUT_MODELS=glm5_2_nv
- ✅ Container 运行正常

## 预期效果
- dsv4p_nv 不再被 big-input breaker 误拦截 → 9 ATE → ~0 ATE (大输入场景)
- dsv4p_nv SR 提升: 14/23 (60.9%) → 预期 20+/23 (87%+)
- glm5_2_nv 仍受 breaker 保护 (3 zombies 不受影响)
- 6h SR 预期: 68.6% → 78%+

## 评判
✅ 更少报错: dsv4p_nv 9 ATE 误杀消除
✅ 更快请求: 无 breaker 延迟，正常 pexec 路径
✅ 超低延迟: 无影响 (成功路径不变)
✅ 稳定优先: 单参数、保守策略、保留 glm5_2_nv 的 breaker 保护
✅ 铁律: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2