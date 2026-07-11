# R1153: HM2→HM1 — NOP (false trigger, 22nd chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `e3f58ce` (R1152) author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (22nd chain of R1133 false trigger)
- HM1 本地 git 仍停在 R821 (`fbf0e43`), 未 pull 新提交

## 2. 改前数据 (2026-07-11 09:20 UTC, 6h)

### 2.1 nv_requests 概览

| 指标 | 值 |
|------|-----|
| 总请求 | 45 |
| 成功 | 25 (55.6%) |
| 错误 | 20 (44.4%) — 全 zombie_empty_completion |
| dsv4p_nv | 0 req (6h 窗口零流量) |
| peer fallback | 0 |
| NV-TIER-FAIL | 0 |
| FASTBREAK | 0 |
| GLOBAL-COOLDOWN | 0 |
| 容器状态 | Up 6h (healthy), 启动于 2026-07-10 19:03 UTC |

### 2.2 6h 模型分布

| Model | Req | OK | Fail | SR% | Avg Dur |
|-------|-----|----|------|------|---------|
| glm5_2_nv | 45 | 25 | 20 | 55.6% | 5383ms |
| dsv4p_nv | 0 | 0 | 0 | N/A | N/A |

### 2.3 6h upstream 分布

| Upstream | Req | OK | Fail | Avg TTFB | Avg Dur | Max Dur |
|----------|-----|-----|------|----------|---------|---------|
| nv_integrate | 45 | 25 | 20 | 4924ms | 5383ms | 12569ms |

### 2.4 6h 每小时 SR 趋势

| Hour (UTC) | Total | OK | Fail | SR% |
|-----------|-------|-----|------|------|
| 19:00 | 2 | 2 | 0 | 100.0% |
| 20:00 | 7 | 7 | 0 | 100.0% |
| 21:00 | 9 | 9 | 0 | 100.0% |
| 22:00 | 9 | 1 | 8 | 11.1% |
| 23:00 | 9 | 4 | 5 | 44.4% |
| 00:00 | 7 | 1 | 6 | 14.3% |
| 01:00 | 2 | 1 | 1 | 50.0% |

注: 01:00 UTC 后至今 (~8h) 零请求 — openclaw zombie 循环已停止或暂停

### 2.5 错误类型详情 (6h)

| Error Type | Count |
|-----------|-------|
| zombie_empty_completion | 20 |

### 2.6 24h 全景

| 指标 | 值 |
|------|-----|
| 24h 总请求 | 270 |
| 24h 成功 | 228 (84.4%) |
| 24h 失败 | 42 (15.6%) |

| Model | Req | OK | Fail | SR% |
|-------|-----|----|------|------|
| glm5_2_nv | 221 | 186 | 35 | 84.2% |
| dsv4p_nv | 33 | 26 | 7 | 78.8% |
| minimax_m3_nv | 9 | 9 | 0 | 100% |
| kimi_nv | 7 | 7 | 0 | 100% |

| Upstream | Req | OK | Fail | Avg TTFB | Avg Dur |
|----------|-----|-----|------|----------|---------|
| nvcf_pexec (dsv4p) | 20 | 20 | 0 | 13692ms | 13692ms |
| nv_integrate (dsv4p) | 6 | 6 | 0 | 16041ms | 17060ms |
| ATE (dsv4p, NULL) | 7 | 0 | 7 | 770ms | 76767ms |

| Error Type | Count |
|-----------|-------|
| zombie_empty_completion | 29 |
| all_tiers_exhausted | 7 |
| NVStream_TimeoutError | 6 |

### 2.7 dsv4p_nv ATE 详情 (24h, 全部 pre-restart)

| Time (UTC) | Dur | tiers_tried | Note |
|-----------|-----|-------------|------|
| 18:02 | 61142ms | 1 | pre-restart |
| 16:00 | 61374ms | 1 | pre-restart |
| 15:50 | 61376ms | 1 | pre-restart |
| 09:06 | 132017ms | 1 | pre-restart |
| 08:20 | 1328ms | 1 | quick fail |
| 06:07 | 110073ms | 1 | pre-restart |
| 05:59 | 110058ms | 1 | pre-restart |

- 全部 upstream_type=NULL, fallback_occurred=f, tiers_tried=1
- 全部 pre-restart (19:03 UTC 前), 当前 regime 6h 零 ATE
- dsv4p_nv pexec 20/20 100% SR, integrate 6/6 100% SR — 功能健康

### 2.8 NVStream_TimeoutError 详情 (24h)

| Time (UTC) | Model | Dur | Upstream |
|-----------|-------|-----|----------|
| 16:52 | glm5_2_nv | 95076ms | nv_integrate |
| 15:56 | glm5_2_nv | 96999ms | nv_integrate |
| 08:15 | glm5_2_nv | 96068ms | nv_integrate |
| 06:10 | glm5_2_nv | 99181ms | nv_integrate |
| 06:02 | glm5_2_nv | 102323ms | nv_integrate |
| 05:54 | glm5_2_nv | 105819ms | nv_integrate |

- 全部 glm5_2_nv integrate, 95-106s, ttfb=NULL
- NVCF content-filter timeout: 大输入 (160K+) → NVCF 内部排队 ~95s → stop+12chars
- INTEGRATE_THINKING_TIMEOUT_S=90 — timeout 后 stream read 再超时

### 2.9 nv_tier_attempts (6h)

| Tier | Error Type | Count | Avg ms | Max ms |
|------|-----------|-------|--------|--------|
| glm5_2_nv | 429_integrate_rate_limit | 3 | - | - |

- 仅 3 次 429, key cycling 成功解决
- 无 NVCFPexecTimeout, 无 SSLEOF, 无 empty_200

### 2.10 docker logs 模式

```
[NV-ZOMBIE-EMPTY] (glm5_2_nv) finish_reason=stop content_chars=12 < 50
  input_chars=163K-166K >= 5000 → aborting stream
[NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter
  error SSE chunk to openclaw
[NV-INTEGRATE-SUCCESS] tier=glm5_2_nv kX succeeded (interleaved)
[NV-INTEGRATE-CYCLE] tier=glm5_2_nv kX → 429 → cycling (rare)
```

模式: 正常请求成功 (~2-6s integrate) → zombie 检测 → error chunk → 循环
- 无 NV-TIER-FAIL, 无 FASTBREAK, 无 GLOBAL-COOLDOWN
- 3 次 429 通过 key cycling 成功解决

### 2.11 当前参数 (容器 env)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | ceiling |
| TIER_TIMEOUT_BUDGET_S | 198 | 充足 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| KEY_COOLDOWN_S | 25 | stable |
| TIER_COOLDOWN_S | 15 | stable |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | stable |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | aligned |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | skip zombie |
| NV_INTEGRATE_MODELS | glm5_2_nv | integrate |
| NV_INTEGRATE_THINKING_TIMEOUT_S | 90 | ceiling |

## 3. 分析

### 3.1 根因不变

- **NVCF content-filter**: glm-5.2 function `3b9748d8` 对 160K+ input 返回 `stop+12chars` 空响应
- **Gateway 检测逻辑正确**: zombie 检测 + error chunk 发送, 不阻塞流
- **dsv4p_nv**: pexec 20/20 100% SR, integrate 6/6 100% SR — 功能健康。7 个 ATE 全部 pre-restart, 当前 regime 零 dsv4p_nv 流量
- **NVStream_TimeoutError**: 6 次都是 glm5_2_nv integrate content-filter timeout (95-106s), NVCF 内部排队, 非 gateway 参数可调
- **openclaw**: 01:00 UTC 后零请求 — zombie 循环已停止或暂停 (8h 无流量)

### 3.2 为什么不是 gateway 问题

- 无 NV-TIER-FAIL, 无 FASTBREAK, 无 GLOBAL-COOLDOWN
- 所有 zombie 的 NVCF 响应是 HTTP 200 (成功完成), 只是内容为空
- Gateway 执行了 zombie 检测 + error chunk 发送, 职责履行完毕
- 3 次 429 通过 key cycling 成功解决, key management 健康
- 所有参数 optimal/floor, 无调优空间

### 3.3 不可配置

- 所有参数 optimal/floor
- 根因在 NVCF 侧 (content-filter, 不可从 gateway 调)
- 第22次 R1133 链误触发
- R1133→R1153 连续 22 轮 NOP, 同模式, 无新信号

## 4. 决策: NOP

**零参数变更, 零 compose 编辑, 零容器重启。**

理由:
1. 这是 false trigger (第22次 R1133 链误触发), 不是 HM1 提交触发的
2. 唯一的 6h 错误类型 zombie_empty_completion 是 NVCF content filter 行为, 非 gateway 参数可调
3. 所有参数已处于 optimal/floor
4. dsv4p_nv 100% SR (pexec+integrate), 功能健康
5. 铁律: 只改 HM1 不改 HM2, 但无可行改项

## 5. 后续建议

- openclaw 端: 同 input 3 次 zombie → 切换模型 (dsv4p_nv/kimi_nv) 或降低输入大小
- 或 openclaw 端对 glm5_2_nv 增加 max_input_chars 限制, 超过则绕过
- Gateway 侧无需改动: zombie 检测+error chunk 机制已正确工作
- cron 误触发问题 (R1133 链已持续 22 轮) — HM2 本地 cron 配置问题, 非 HM1 优化范围

## ⏳ 轮到HM1优化HM2