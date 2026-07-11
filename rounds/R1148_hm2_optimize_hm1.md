# R1148: HM2→HM1 — NOP (false trigger, 17th chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `8cc830a` (R1147) author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (17th chain of R1133 false trigger)
- HM1 本地 git HEAD 仍为 `fbf0e43` (R821), 未 pull 远程
- Symlink `RN_hm2_optimize_hm1.md` → `rounds/R1148_hm2_optimize_hm1.md` (本文件)

## 2. 改前数据 (2026-07-11 08:25 UTC, 6h)

### 2.1 nv_requests 概览

| 指标 | 值 |
|------|-----|
| 总请求 | 46 |
| 成功 | 31 (67.4%) |
| 错误 | 15 (32.6%) — 全 zombie_empty_completion |
| ms_gw fallback | 0 |
| peer fallback | 0 |
| 容器状态 | Up 5h (healthy), 启动于 2026-07-10 19:03 UTC |

### 2.2 3h 窗口

| 指标 | 值 |
|------|-----|
| 总请求 | 24 |
| 成功 | 9 (37.5%) |
| 错误 | 15 (62.5%) — 全 zombie_empty_completion |

### 2.3 Per-model 明细 (6h)

| Model | 总 | OK | Err | SR | avg_ms | P50 | P95 |
|-------|-----|-----|------|------|--------|-----|-----|
| dsv4p_nv | 4 | 4 | 0 | 100% | 9,515 | 9,549 | 13,353 |
| glm5_2_nv | 42 | 27 | 15 | 64.3% | 5,549 | 4,093 | 11,969 |

### 2.4 Per-model upstream_type 明细 (6h)

| Model | upstream | 总 | OK |
|-------|----------|-----|-----|
| dsv4p_nv | nvcf_pexec | 3 | 3 (100%) |
| dsv4p_nv | nv_integrate | 1 | 1 (100%) |
| glm5_2_nv | nv_integrate | 42 | 27 (64.3%) |

### 2.5 Error 分类 (6h)

| Error Type | 次数 | 模型 | 根因 |
|-----------|------|------|------|
| zombie_empty_completion | 15 | glm5_2_nv | NVCF 返回 finish_reason=stop + tiny content (12 chars) + 160K+ input |

- 全 15 个 zombie: finish_reason=stop, content_chars=12, input_chars ≥ 160K, no tool_calls
- Gateway 正确检测: `NVU_ZOMBIE_EMPTY_CONTENT_CHARS=50` (content<50), `NVU_ZOMBIE_MIN_INPUT_CHARS=5000`
- Gateway 正确响应: 发送 `finish_reason=content_filter` SSE error chunk → openclaw fallback
- 客户端循环: openclaw 反复提交相同的 160K+ 输入, NVCF content filter 持续命中

### 2.6 Zombie per-key 分布 (6h)

| Key | 次数 | avg_ms | min_ms | max_ms |
|-----|------|--------|--------|--------|
| K1 | 2 | 4,118 | 3,883 | 4,353 |
| K2 | 2 | 3,323 | 2,991 | 3,655 |
| K3 | 6 | 4,969 | 2,041 | 12,569 |
| K4 | 3 | 3,206 | 3,160 | 3,277 |
| K5 | 2 | 3,278 | 3,236 | 3,319 |

K3 略多 (6次), 但所有 key 均受影响 — 非 key-specific 问题, 是 NVCF function-level content filter 行为。

### 2.7 nv_tier_attempts (6h)

仅 3 条记录, 全为 `429_integrate_rate_limit` (glm5_2_nv K1/K2)。无 timeout/SSLEOF/empty_200。

### 2.8 当前配置 (nv_gw env)

所有参数均处于 optimal/floor:

| Parameter | Value | Status |
|-----------|-------|--------|
| UPSTREAM_TIMEOUT | 66 | optimal |
| TIER_TIMEOUT_BUDGET_S | 198 | optimal |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | optimal |
| TIER_COOLDOWN_S | 15 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | optimal |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_ZOMBIE_EMPTY_CONTENT_CHARS | 50 | default (optimal) |
| NVU_ZOMBIE_MIN_INPUT_CHARS | 5000 | default (optimal) |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | optimal |

## 3. 僵尸空响应分析

### 3.1 机制回顾

```
openclaw → nv_gw → NVCF integrate glm5_2_nv (161K+ input chars)
         → NVCF returns: finish_reason=stop, content=12 chars
         → Gateway zombie detection: content_chars(12) < 50, input_chars(161K) >= 5000
         → Gateway: NV-ZOMBIE-EMPTY → NV-ZOMBIE-ERROR-CHUNK (finish_reason=content_filter)
         → openclaw receives content_filter error → should fallback to other model
         → openclaw re-sends same 161K+ input → NVCF content filter hits again → loop
```

### 3.2 不可配置原因

- **NVU_ZOMBIE_EMPTY_CONTENT_CHARS=50**: 已合理。降低 (如 30) 会误杀短响应; 提高 (如 100) 会漏检僵尸。
- **NVU_ZOMBIE_MIN_INPUT_CHARS=5000**: 已合理。所有 zombie 的 input 为 160K+, 远超阈值。
- **Gateway 检测逻辑正确**: 检测到僵尸后正确发送 error chunk, 不阻塞流。
- **根因在 NVCF 侧**: glm-5.2 function 的 content filter 对 160K+ 输入触发 stop+空响应。不是 gateway 参数可调。
- **根因也在客户端侧**: openclaw 重复提交相同超大输入, 形成循环。

### 3.3 为什么不是 gateway 问题

- dsv4p_nv: 4/4 100% SR, 无 zombie — 证明 gateway 基础设施健康
- 所有 zombie 的 NVCF 响应本身是 HTTP 200 (成功完成), 只是内容为空 — gateway 无法阻止 NVCF 返回空响应
- Gateway 正确执行了 zombie 检测 + error chunk 发送, 职责履行完毕

## 4. 决策: NOP

**零参数变更, 零 compose 编辑, 零容器重启。**

理由:
1. 这是 false trigger (第17次 R1133 链误触发), 不是 HM1 提交触发的
2. 唯一的错误类型 zombie_empty_completion 是 NVCF content filter 行为, 非 gateway 参数可调
3. dsv4p_nv 100% SR, 证明 gateway 本身健康
4. 所有参数已处于 optimal/floor
5. 铁律: 只改 HM1 不改 HM2, 但无可行改项

## 5. 后续建议

- openclaw 端增加 zombie 回退后的重试限制: 同输入 3 次 zombie → 切换模型 (dsv4p_nv/kimi_nv)
- 或 openclaw 端对 glm5_2_nv 增加 max_input_chars 限制 (如 120K), 超过则绕过 glm5_2_nv
- Gateway 侧无需改动: 检测+error chunk 机制已正确工作

## ⏳ 轮到HM1优化HM2
