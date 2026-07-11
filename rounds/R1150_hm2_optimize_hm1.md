# R1150: HM2→HM1 — NOP (false trigger, 19th chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `01a8a1f` (R1149) author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (19th chain of R1133 false trigger)
- HM1 本地 git 未再更新, 仍在 R1149 NOP 状态
- Symlink `RN_hm2_optimize_hm1.md` → `rounds/R1150_hm2_optimize_hm1.md` (本文件)

## 2. 改前数据 (2026-07-11 08:45 UTC, 6h)

### 2.1 nv_requests 概览

| 指标 | 值 |
|------|-----|
| 总请求 | 47 |
| 成功 | 28 (59.6%) |
| 错误 | 19 (40.4%) — 全 zombie_empty_completion |
| ms_gw fallback | 1 attempt, 0 OK |
| peer fallback | 0 |
| NV-TIER-FAIL | 0 |
| GLOBAL-COOLDOWN | 0 |
| FASTBREAK | 0 |
| 容器状态 | Up 6h (healthy), 启动于 2026-07-10 19:03 UTC |

### 2.2 6h 窗口

| 指标 | 值 |
|------|-----|
| 总请求 | 47 |
| 成功 | 28 (59.6%) |
| 错误 | 19 (40.4%) — 全 zombie_empty_completion |
| 容器启动 | 2026-07-10 19:03 UTC (全 6h 窗口在 post-restart 内) |

### 2.3 Per-model 明细 (6h)

| Model | 总 | OK | Err | SR | avg_ms_ok | avg_ms_err |
|-------|-----|-----|------|------|-----------|-----------|
| dsv4p_nv | 4 | 4 | 0 | 100% | 9,515 | — |
| glm5_2_nv | 43 | 24 | 19 | 55.8% | 6,158 | 4,379 |

### 2.4 Per-model upstream_type 明细 (6h)

| Model | upstream | 总 | OK | SR |
|-------|----------|-----|-----|-----|
| dsv4p_nv | nvcf_pexec | 3 | 3 | 100% |
| dsv4p_nv | nv_integrate | 1 | 1 | 100% |
| glm5_2_nv | nv_integrate | 43 | 24 | 55.8% |

### 2.5 Error 分类 (6h)

| Error Type | 次数 | 模型 | 根因 |
|-----------|------|------|------|
| zombie_empty_completion | 19 | glm5_2_nv | NVCF 返回 finish_reason=stop + 12 chars + 160K+ input |

- 全 19 个 zombie: finish_reason=stop, content_chars=12, input_chars 164K-166K, no tool_calls
- Gateway 正确检测 (NVU_ZOMBIE_EMPTY_CONTENT_CHARS=50, NVU_ZOMBIE_MIN_INPUT_CHARS=5000)
- Gateway 正确响应: 发送 finish_reason=content_filter SSE error chunk
- 客户端循环: openclaw 反复提交递增的 160K+ input → NVCF content filter 持续命中

### 2.6 Zombie per-key 分布 (6h)

| Key | 次数 | avg_ms | min_ms | max_ms |
|-----|------|--------|--------|--------|
| K1 | 3 | 6,864 | 3,883 | 12,357 |
| K2 | 3 | 3,360 | 2,991 | 3,655 |
| K3 | 3 | 3,230 | 3,135 | 3,319 |
| K4 | 6 | 4,969 | 2,041 | 12,569 |
| K5 | 4 | 3,255 | 3,160 | 3,400 |

K4 略多 (6次), 但所有 key 均受影响 — 非 key-specific 问题, 是 NVCF function-level content filter 行为。

### 2.7 nv_tier_attempts (6h)

仅 3 条记录, 全为 `429_integrate_rate_limit` (glm5_2_nv, K1×1, K2×2)。无 timeout/SSLEOF/empty_200。所有 429 通过 key cycling 成功解决。

### 2.8 日志信号 (200行)

```
NV-ZOMBIE-EMPTY: 19次 (全部正确检测, content_chars=12 < 50)
NV-ZOMBIE-ERROR-CHUNK: 19次 (全部正确发送 content_filter error chunk)
NV-INTEGRATE-SUCCESS: 44次 (正常完成, 含 24 OK + 19 zombie 的 upstream 200 + 1 ms_gw)
NV-INTEGRATE-COOLDOWN: 3次 (429 rate limit → key cycling)
NV-TIER-FAIL: 0
NV-ALL-EXHAUSTED: 0
GLOBAL-COOLDOWN: 0
FASTBREAK: 0
EMPTY-200: 0
NV-PEER-FB: 0
NV-MS-FB: 0
```

### 2.9 当前配置 (nv_gw env)

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
| NVU_EMPTY_200_FASTBREAK | 2 | optimal (R1031) |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_ZOMBIE_EMPTY_CONTENT_CHARS | 50 | default (optimal) |
| NVU_ZOMBIE_MIN_INPUT_CHARS | 5000 | default (optimal) |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | optimal |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | optimal |
| NVU_FORCE_STREAM_UPGRADE | 0 | optimal (off) |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | peer-fb disabled for zombie model |
| NV_INTEGRATE_MODELS | glm5_2_nv | integrate mode |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor (fast 429 cycling) |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | optimal |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | optimal |

## 3. 僵尸空响应分析

### 3.1 机制回顾

```
openclaw → nv_gw → NVCF integrate glm5_2_nv (164K-166K input chars)
         → NVCF returns: finish_reason=stop, content=12 chars
         → Gateway zombie detection: content_chars(12) < 50, input_chars(164K) >= 5000
         → Gateway: NV-ZOMBIE-EMPTY → NV-ZOMBIE-ERROR-CHUNK (finish_reason=content_filter)
         → openclaw receives content_filter error → retries with more context
         → input grows (164K→165K→166K) → NVCF content filter hits again → loop
```

### 3.2 不可配置原因

- **NVU_ZOMBIE_EMPTY_CONTENT_CHARS=50**: 已合理。12 < 50, 正确检测。降低会误杀短响应; 提高会漏检。
- **NVU_ZOMBIE_MIN_INPUT_CHARS=5000**: 已合理。164K+ >> 5000, 所有 zombie 满足。
- **Gateway 检测逻辑正确**: 检测到僵尸后正确发送 error chunk, 不阻塞流。检测延迟 ~1-2s (stream 结束后)。
- **根因在 NVCF 侧**: glm-5.2 function 3b9748d8 的 content filter 对 160K+ input 触发 stop+空响应。
- **根因也在客户端侧**: openclaw 重复提交递增的 160K+ input, 形成循环。
- **Peer-fb 无效**: glm5_2_nv 在 NVU_PEER_FB_SKIP_MODELS 中 — 即使移除, HM2 也使用同一 NVCF function, 同样 content filter。
- **Pexec 替代无效**: 移除 glm5_2_nv 从 NV_INTEGRATE_MODELS 会切到 pexec — 但 NVCF content filter 是 function-level, 不随 transport 改变。
- **R1149 分析仍然有效**: 这是 R1149 的延续, 无新错误类型, 无新退化信号。

### 3.3 为什么不是 gateway 问题

- dsv4p_nv: 4/4 100% SR, 零 zombie — 证明 gateway 基础设施健康
- 所有 zombie 的 NVCF 响应本身是 HTTP 200 (成功完成), 只是内容为空
- Gateway 正确执行了 zombie 检测 + error chunk 发送, 职责履行完毕
- 无 NV-TIER-FAIL, 无 FASTBREAK, 无 GLOBAL-COOLDOWN — 无任何 gateway 异常信号
- 3 次 429 通过 key cycling 成功解决, 证明 key management 健康

## 4. 决策: NOP

**零参数变更, 零 compose 编辑, 零容器重启。**

理由:
1. 这是 false trigger (第19次 R1133 链误触发), 不是 HM1 提交触发的
2. 唯一的错误类型 zombie_empty_completion 是 NVCF content filter 行为, 非 gateway 参数可调
3. dsv4p_nv 100% SR, 证明 gateway 本身健康
4. 所有参数已处于 optimal/floor
5. 铁律: 只改 HM1 不改 HM2, 但无可行改项

## 5. 后续建议

- openclaw 端: 同输入 3 次 zombie → 切换模型 (dsv4p_nv/kimi_nv) 或降低输入大小
- 或 openclaw 端对 glm5_2_nv 增加 max_input_chars 限制 (如 120K), 超过则绕过
- Gateway 侧无需改动: 检测+error chunk 机制已正确工作
- 考虑修复 cron 误触发问题 (R1133 链已持续 19 轮), 但这是 HM2 本地 cron 配置问题, 非 HM1 优化范围

## ⏳ 轮到HM1优化HM2