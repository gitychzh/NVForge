# R2306: cc2→cc4101→ms_gw(40007) fallback 触发情形全编目

**日期**: 2026-07-24
**主机**: HM2 (opc2_uname@100.109.57.26)
**铁律遵守**: 只查不改, 零参数变更, 未碰 ms_gw 源码/compose, 未碰 agent 模型选择

## 背景

用户要求"汇总 fallback 到 ms 的几种情形"。前置工作 R2305 (KEY_COOLDOWN 60→15 证伪已回滚) + 与 chatgpt 讨论 Pareto 曲线 + 读 cc4101/nv_gw 源码后, 系统编目所有 fallback 到 ms_gw 的触发路径。

## 关键事实修正(推翻旧记忆)

1. **HM1 cc4101 ≠ HM2 cc4101**:
   - HM1 cc4101: R854 "no fallback", `fallback_triggered` 硬编码 False
   - **HM2 cc4101: R1643 加回 fallback**! `execute_request` 注释: "R854 曾删 fallback; R1643 加回(末位兜底, nv 不限额优先, ms 限额仅兜底)"
   - DB 33 次 fallback_triggered=True 全在 HM2, 是 R1643 逻辑触发
   - 教训: 读源码必须读 HM2 容器内版本(`docker exec cc4101`), HM1 源码已不同步

2. **当前 6h 真实数据(HM2 cc_requests)**:
   - 332 请求, HTTP 200 率 93.1%, fallback 触发率 9.9% (33 次)
   - fallback 兜回 200 = 30 次 (91% 救回), 真实失败 3/332 = 0.9%
   - 33 次 fallback **全因 timeout** (primary_error_type=timeout, avg primary_elapsed 114s)
   - primary 路径 avg ttfb 56s, fallback 路径 avg ttfb 130s (ms 也慢但兜回)

3. **33 次 timeout 的 primary_elapsed 分布**:
   - 60-100s: 18 次 (cc4101 header_timeout 砍, 可能误杀 NVCF 慢首字节)
   - 150-180s: 1 次 (边界)
   - >=180s: 14 次 (撞 SDK 180s byte-idle 墙, NVCF 真 hang)

4. **breaker OPEN 只 6 次/6h** → 大部分 fallback 不是断路器短路, 是单请求级 timeout (路径 2)

## cc4101 层 fallback 路径 (4 种, primary=glm5_2_nv → fallback=glm5_2_ms)

源码: HM2 `cc4101 /app/gateway/upstream.py` execute_request()

### 路径 1: PRIMARY-BREAKER-OPEN (断路器 OPEN 直走 ms)

- **触发**: `is_primary_open()` 返 True
- **条件**: primary 连续失败 >=5 次/300s 窗口(breaker 阈值), 且失败是"该计的"
  - 该计: server_5xx, 或 timeout 且耗时 > _CHAIN_BUDGET_S(120s), 或 conn/unexpected
  - 不该计: header 超时且耗时 < 120s (大概率 cc4101 抢断 nv_gw, 不计, 避免误开)
- **行为**: 跳过 primary, 直接 `_try_fallback("fallback(circuit-open)")`, 省每条等 nv 超时 60-120s
- **当前占比**: ~6 次/33 = 18% (按 breaker OPEN 6 次估)
- **源码行**: upstream.py `if is_primary_open():` 段

### 路径 2: PRIMARY-FAIL → 立即试 fallback (primary retryable 失败) ★主路径

- **触发**: `_try_primary()` 返 False (非 client_4xx)
- **条件**: primary 抛 `_UpstreamError` 且 kind ∈ {server_5xx, timeout, conn, unexpected}
- **行为**: 立即 `_try_fallback("fallback")` 一次. 成败都不计 breaker
- **client_4xx (400/413 等) 不 fallback** (请求级错误, ms 也会 4xx)
- **当前占比**: ~27 次/33 = 82% (33 次全 timeout, 扣掉 breaker OPEN 6 次)
- **源码行**: upstream.py `r = _try_primary("primary")` 后的 Stage 2 段

### 路径 3: FORCE_FALLBACK (客户端指定强制走 ms)

- **触发**: `FORCE_FALLBACK_MODEL` env 设了, 且 `oai_body["model"]` 匹配
- **行为**: 跳过 primary + 跳过断路器, 直走 `_try_fallback("fallback(forced)")`
- **用途**: loop 自优化子会话绕开 nv_gw 间歇劣化窗口
- **当前状态**: env 未设(compose 没配), **当前不触发**
- **源码行**: upstream.py Stage -1 段

### 路径 4: PRIMARY_HEADER_TIMEOUT 砍 (路径 2 timeout 的细分根因)

- 这不是独立路径, 是路径 2 的 timeout 细分
- **触发**: cc4101 `_call_upstream` 的 `getresponse()` 在 `header_timeout` 内没拿到首字节 → `socket.timeout` → `_UpstreamError(kind="timeout")`
- **六档 (input chars, R2154 + R2202/R2197 修正)**:
  | input chars | header_timeout | 依据 |
  |---|---|---|
  | >350K | 120s | |
  | >200K | 180s | R2197: 120→180 (NVCF ttfb 120-142s 踩 120s 线致 499) |
  | >150K | 180s | R2202: 120→180 (同上根因) |
  | >90K  | 160s | R2154: nv_gw first-byte 60s 先 break, 160s 兜底真慢 |
  | >50K  | 150s | R2154: 实测 p99 141s, 旧 75s 误杀 |
  | >30K  | 40s  | R2154: 新拆档, nv_gw first-byte 20s + 20s 余量 |
  | else  | 25s  | 默认, 死连快断 (R828) |
- **数据印证**: 33 次 timeout 中 18 次 60-100s (落 50-90K/90-150K 档) + 14 次 >=180s (撞 SDK 墙, 非 cc4101 砍)

## nv_gw 层 fallback 路径 (2 种, 在返回 cc4101 之前)

源码: HM2 `nv_gw /app/gateway/handlers.py` + `upstream.py`
注: nv_gw 自己 R854 移除了 ms_fallback (注释提到 `_ms_fallback_request` 但代码无定义), 自己不切 ms, 返回 502/429 让 agent(cc4101) 落 ms

### 路径 5: all_tiers_exhausted → 返回 502/429 让 agent 落 ms

- **触发**: nv_gw 内部 5key×2mode tier chain 全失败
- **行为**: 返回 502 (或 429 if all_429) 给 cc4101, cc4101 收到 → 路径 2 触发 fallback
- **子情形(nv_gw 提前 short-circuit, 不全跑 5key)**:
  - **NV-TIER-DEGRADED-SKIP**: NVCF function 近期返 400 DEGRADED → skip 整个 key loop
  - **NV-TIER-BUDGET**: tier budget 耗尽 (glm5_2_nv env 默认 70s 短 budget) → 1-2 key 就 fail
  - **PEEXEC_TIMEOUT_FASTBREAK** (env NVU_PEXEC_TIMEOUT_FASTBREAK=3): 连续 3 次 pexec timeout → break early (省 30-50s)
  - **EMPTY_200_FASTBREAK** (env NVU_EMPTY_200_FASTBREAK=1): 连续 1 次 empty_200 → break
  - **peer-fb skip** (env NVU_PEER_FB_SKIP_MODELS 默认含 glm5_2_nv): glm5_2_nv 不跨机 peer fallback, 直接本地 502
- **源码行**: handlers.py `if not result.success:` + `if result.all_keys_exhausted:` 段; upstream.py:523 tier_budget 段

### 路径 6: peer fallback 失败 → 502 让 agent 落 ms

- **触发**: 本机 all_tiers_exhausted 且 model 不在 peer-skip list 且非 429 → 跨机转发 HM1 nv_gw
- **行为**: peer 也 all_tiers_exhausted → 返本地 502 → cc4101 路径 2 触发
- **当前状态**: glm5_2_nv 在 skip list, **对 glm5_2_nv 当前不走** (其他模型 dsv4p/kimi 可能走)
- **源码行**: handlers.py `_peer_fallback()` + `hop_n < 1 and not is_429` 段

## 当前 6h 33 次 fallback 的实际分布

| 路径 | 估计次数 | 依据 |
|---|---|---|
| 路径 2 (primary timeout → fb) | ~27 次 | 33 次全 timeout, breaker 只 OPEN 6 次 |
| 路径 1 (breaker OPEN 直走) | ~6 次 | breaker OPEN 6 次 |
| 路径 4 细分 (路径 2 子集) | 18 次 60-100s + 14 次 >=180s | primary_elapsed 分布 |
| 路径 3 (FORCE_FALLBACK) | 0 | env 未设 |
| 路径 5 (all_tiers_exhausted→502→fb) | 含在路径 2 | nv_gw 502 → cc4101 timeout |
| 路径 6 (peer fb 失败→502→fb) | 0 | glm5_2_nv 在 skip list |

## 与 chatgpt 讨论的 Pareto 曲线 (决策依据)

chatgpt 贡献两个关键判断(均采纳):
1. **两表口径不一致**: nv_tier_attempts 是单次 pexec attempt (max success=57s), nv_requests 是整个请求含 chain 重试累计 (60-120s 桶 SR 96%). PRIMARY_HEADER_TIMEOUT 作用层决定用哪张表
2. **先挖 DB 现有数据做 Pareto, 别拍脑袋**: 已落地

### 挖出的 Pareto (HM2, 6h, nvcf_pexec, nv_requests ttfb 分桶 × SR)

| ttfb | n | SR |
|---|---|---|
| <10s | 12 | 91.7% |
| 10-20s | 29 | 100% |
| 20-30s | 43 | 90.7% |
| 30-60s | 94 | 95.7% |
| 60-90s | 32 | 96.9% |
| 90-120s | 22 | 95.5% |
| 120-150s | 6 | 66.7% ← 拐点 |
| >=180s | 1 | 100% |

nv_tier_attempts 的 pexec_success: avg=24.7s, **max=57s** (成功单次 attempt 全在 60s 内)

### chatgpt 建议被源码推翻

- chatgpt 建议 25/40/90/90/90/90 (砍到 90s)
- 源码铁证: cc4101 header_timeout 包整个 nv_gw chain 首字节 (不是单次 attempt), chain 合法预算 120s
- R1638 历史: 200-350K 档曾 90s, 与 chain budget 120s 倒挂 → BrokenPipe 死循环, 改 120s 才修
- 砍到 90s 会重触发 R1638 倒挂 → **不采纳**

## 关键约束 (为什么不能简单"砍 fallback")

1. **路径 2 的 14 次 >=180s**: NVCF 真 hang, 不 fallback 就撞 SDK 180s byte-idle 墙变 499. **fallback 是救命, 不能砍**
2. **路径 2 的 18 次 60-100s**: 可能 NVCF 慢首字节被 header_timeout 砍早, 但 Pareto 显示砍到 60s 会误救 35% (60-120s 桶 SR 96%), 且 90s 重触发 R1638 倒挂. **不动**
3. **路径 1 breaker**: 过度 OPEN 跳过整条 nv chain, 但砍阈值致 38% 超 180s. **不动**

## 最终结论: 方案 D (接受现状, 零参数变更)

- 真实失败率 0.9% (3/332), fallback 率 9.9% 中 91% 被 ms 兜回
- 4 种 cc4101 路径 + 2 种 nv_gw 路径都各有正当理由
- 动任何一处都会重触发历史已修的 bug (R1638 倒挂 / R854 死循环 / breaker 误开)
- 当前 PRIMARY_HEADER_TIMEOUT 六档已对齐 chain budget 120s + Pareto 拐点 120s, **已接近最优**

## 验证清单

- [x] HM2 cc4101 源码读完 (execute_request 182-460, _try_primary, _try_fallback, 调度)
- [x] HM2 nv_gw handlers.py fallback 调度段读完 (290-410)
- [x] DB 33 次 fallback_triggered=True 样本确认 (upstream_used=fallback, primary_error_type=timeout)
- [x] Pareto 曲线挖掘 (nv_requests ttfb 分桶 + nv_tier_attempts pexec_success)
- [x] chatgpt 讨论两轮 (口径判断 + 90s 建议被源码推翻)
- [x] 零参数变更 (未改 compose/env/.py), 铁律遵守

## 关联

- [[r1648-terminal-architecture]] cc4101 瘦成纯透传 (R1643 加回 fallback 的架构背景)
- [[r2154-cc4101-dynamic-header-timeout-refined]] PRIMARY_HEADER_TIMEOUT 六档
- [[r2202-cc4101-150k-tier-120-180-499-rootfix]] 150-200K 档 120→180s
- [[r2264-499-two-forms-real-rootcause]] 499 两形态 + SDK byte-idle 180s 墙定义
- [[r2258-watchdog-600s-hotfix]] webui watchdog 120→600s (只罩 webui, cc2 吃 SDK 默认 180s)
- [[r1638-cc4101-header-inversion-breaker-polarity]] 90s 倒挂 120s 致 BrokenPipe (砍 90s 会重触发)
