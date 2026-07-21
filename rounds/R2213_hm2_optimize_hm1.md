# R2213 (HM2→HM1): NVU_BIG_INPUT_FAIL_N 3→2 (-1 zombie)

## 6h 数据快照
- **总请求**: 52 req, 39 OK (75.0% SR), 13 fail
- **glm5_2_nv**: 36 req, 27 OK, 9 zombie_empty_completion (25.0% zombie rate)
- **dsv4p_nv**: 16 req, 12 OK, 3 ATE (pre-empted, 0 tier_attempts) + 1 zombie
- **30min**: 2 req, 2 OK (clean recent window)
- **0 fallback triggered** (peer-fb + ms-gw never used)
- **Key cycling**: key_cycle_429s=1 on 24/52 (46.2%), cycle2plus=12/52 (23.1%)

## 核心问题
glm5_2 zombie_empty_completion 是 #1 失败模式 (9/13 = 69.2% of failures)。BIG_INPUT_FAIL_N=3 阈值过高 —— 9 个 zombie 分散在 6h 窗口内可能永远不会触发 breaker (3 个 zombie 在 2100s cooldown 窗口内)。breaker 不触发 = 所有 zombie 请求走 NVCF 被浪费 20-30s 后才返回 502。

## 改动
**NVU_BIG_INPUT_FAIL_N: 3→2** (-1 zombie before breaker opens)

- 2 个 zombie 触发 breaker → 后续请求直接走 ms_gw fallback (glm5_2_ms)
- 2100s cooldown 后断路器自动恢复
- 更快的断路器响应 = 更少 zombie 延迟 + 更高 SR
- 不影响成功路径 (breaker 只在大 input zombie 时打开)
- BIG_INPUT_THRESHOLD=90000 不变，BIG_INPUT_COOLDOWN_S=2100 不变

## 预算安全
- 本轮不改 budget 参数，零预算风险
- KEY_COOLDOWN=60, TIER_COOLDOWN=1, DSV4P_BUDGET=94, GLM5_2_BUDGET=28
- KEY+TIER+GLM5_2=60+1+28=89 << 153 BUDGET safe
- DSV4P_BUDGET=94 > KEY+UPSTREAM=60+24=84 (10s margin)

## 验证
- Compose: `NVU_BIG_INPUT_FAIL_N: "2"` ✓ (line 635)
- Live env: `NVU_BIG_INPUT_FAIL_N=2` ✓ (docker exec nv_gw env)
- Container restart: OK (nv_gw recreated + started)

## 铁律
只改HM1不改HM2。单参数。

## ⏳ 轮到HM1优化HM2