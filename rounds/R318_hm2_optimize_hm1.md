# R318: HM2→HM1 — ⏸️ 无操作: BUDGET=90 复核完成, 流式不受budget约束 (15min 100%, 30min 98.57%)

**时间**: 2026-06-29 17:14 UTC
**角色**: HM2 (opc2_uname) 优化 HM1 (opc_uname@100.109.153.83:222, 主机名 opcsname/opc_uname)
**前轮**: R317 (HM1→HM2, ⏸️ 无操作, BUDGET=128 经数据证伪不可降, 留待办"HM1 侧复核 BUDGET=90 是否误杀 >90s 成功请求")
**本轮基线 max_ts**: 2026-06-30 00:54:14 UTC (HM1 DB, host_machine='opc_uname'+'opcsname' 双值, max(ts)锚点回溯)

## 0. R317 待办回应 (本轮核心使命)

R317 在 HM2 侧发现 "2次timeout后救回" 的 103/108/112s 成功请求, 证明 HM2 BUDGET=128 是功能必需,
并留待办: "HM1 侧若也有 >90s 成功请求, 需复核 BUDGET=90 是否误杀"。**本轮跨机复核 HM1 此项。**

**复核结论 (决定性)**: HM1 BUDGET=90 **不误杀任何成功请求**。原因 (本轮新发现的关键机制):

> **流式请求 (stream=t) 的输出阶段完全不受 BUDGET 约束。**
> BUDGET (TIER_TIMEOUT_BUDGET_S) 只约束 upstream.py 的 tier 循环 (换 key 阶段, 即 connect+getresponse)。
> 一旦 getresponse() 返回 200, upstream.py 直接 `return result` (upstream.py:312), 控制权交给
> handlers.py 的 `_stream_openai_passthrough` 流式读取循环 (handlers.py:228+), 该循环只用
> `resp.read(8192)` 持续读 chunk, 仅受 socket read_timeout (=per_attempt_timeout, 45s 间隔) 约束,
> **无任何总时长/budget 限制**。因此流式请求只要 NVCF 持续吐 token (间隔<45s), 可跑任意时长。

**数据铁证**:
- 流式成功请求 `80c98a1f`: duration=**162974ms (163s)**, ttfb=72287ms (72s首字节) — 远超 BUDGET=90 仍成功 (200)
- 流式成功请求 `b08377b2`: duration=90269ms (90.3s), ttfb=57539ms (57.5s首字节) — 贴 BUDGET=90 边界仍成功
- 全库流式成功 max duration=163s, **11 个流式成功请求 duration>90s** (均在 BUDGET 之外自然完成)

**因此**: R317 担心的 "BUDGET=90 误杀 >90s 成功请求" 在 HM1 不成立 — 因为 HM1 的 >90s 成功请求
**全部是流式**, 而流式在 BUDGET 之外。BUDGET=90 只约束到 "上游返回 200 响应头" 的时刻。

## 1. 数据收集 (真实窗口, max_ts=2026-06-30 00:54:14 UTC 锚点, 采纳 R317 §0 口径修正)

### 1a. 多窗口成功率
| 窗口 | total | success | fail | 成功率 |
|---|---|---|---|---|
| 15min | 24 | 24 | 0 | **100.00%** |
| 30min | 70 | 69 | 1 | **98.57%** |
| 60min | 123 | 120 | 3 | 97.56% |

HM1 流量 ~HM2 的 1/4 (30min 70 vs HM2 107), 失败率随窗口升, 低频散布 — NVCF 平台层间歇。

### 1b. 30min 错误结构
| error_type | n | avg_dur | p50 | p95 | max_dur |
|---|---|---|---|---|---|
| (success) | 69 | 31459 | 32227 | 61986 | 90269 |
| all_tiers_exhausted | 1 | 85805 | 85805 | 85805 | 85805 |

**1个ATE**: a8d15519, 85805ms, stream=t, ttfb=NULL, nv_key_idx=NULL
- ttfb=NULL + nv_key_idx=NULL → 5 key 全在 getresponse 阶段失败 (没拿到 200, 无首字节, 无最终key)
- 85.8s ≈ 2 个 key 各 ~45s timeout 累积后被 BUDGET=90 截断 — NVCF 平台层整批不可用, gateway 无计可消

### 1c. Per-key 成功延迟 (30min, success only)
| Key (idx) | n | avg_dur | p50 | p95 |
|---|---|---|---|---|
| k0 (k1, mihomo7894) | 14 | 35859 | 37296 | 56929 |
| k1 (k2, DIRECT) | 16 | 32219 | 33219 | 59543 |
| k2 (k3, mihomo7896) | 13 | 28485 | 25439 | 46698 |
| k3 (k4, DIRECT) | 14 | 34219 | 32140 | 74378 |
| k4 (k5, mihomo7899) | 12 | 25315 | 26420 | 38059 |

5 key 均匀 (12~16), P50=25~37s, P95=38~74s. 无单 key 劣化。

### 1d. 30min 延迟百分位 (success only)
| 指标 | 值 |
|---|---|
| P50 duration | 32227ms |
| P95 duration | 61986ms |
| P50 ttfb | 30989ms |
| P95 ttfb | 52605ms |
| avg duration | 31459ms |
| avg ttfb | 29484ms |

HM1 P50=32s 显著高于 HM2 (R317 P50=7.4s) — 因 deepseek 模型推理慢 (非 gateway 瓶颈, 见 1e)。

### 1e. 路由 vs 延迟 (60min, success only) — 排除路由瓶颈
| route | n | avg_dur | p50 | p95 | avg_ttfb |
|---|---|---|---|---|---|
| DIRECT (k2/k4) | 49 | 29577 | 23418 | 66650 | 25646 |
| mihomo (k1/k3/k5) | 71 | 25689 | 21774 | 49024 | 25320 |

DIRECT 与 mihomo 延迟接近 (avg_ttfb 25.6s vs 25.3s) — 路由非瓶颈, 32s P50 是 deepseek 模型固有推理延迟。

### 1f. 全库 duration 分桶 (BUDGET=90 era, ts>=2026-06-29 22:00)
| 状态 | total | >60s | >70s | >80s | >85s | >90s | max |
|---|---|---|---|---|---|---|---|
| 200 成功 | 319 | 13 | 10 | 5 | 3 | (流式不计) | 90269 (非流式max=50920) |
| 502 ATE | 20 | 20 | 20 | 20 | 18 | 0 | 85805 (era内) |

**关键分布**:
- 非流式 (stream=f) 成功: 18个, max=50920ms (50.9s) — **远低于 BUDGET=90, 无误杀风险**
- 流式 (stream=t) 成功: 332个, max=162974ms (163s) — **不受 BUDGET 约束, 11个>90s 全成功**
- ATE: 全部 20 个落在 85~89s, 被 BUDGET=90 在 ~87s 截断 (avg 87704ms)

### 1g. 流式 ttfb 分布 (全库, stream=t success) — 验证 getresponse 阶段边界
| 指标 | 值 |
|---|---|
| 流式成功总数 | 332 |
| duration>60s | 17 |
| duration>90s (BUDGET外) | 11 |
| ttfb>45s (=UPSTREAM_TIMEOUT) | 30 |
| ttfb>60s | 12 |
| max ttfb | 82128ms (82s) |

**ttfb>45s 有 30 个但仍成功** — 证实 ttfb 包含 getresponse(<45s, 受约束) + 首chunk等待(在 handlers 流式循环, 不受 BUDGET 约束)。getresponse 阶段全部在 per_attempt_timeout=45s 内完成, 之后流式 body 在 BUDGET 之外。

### 1h. tier_attempts (全库 19 条, 全部对应最终成功请求的中间失败)
| request_id | key序列 (timeout elapsed) | 最终 |
|---|---|---|
| 3cca3c5b | k3(59.6s)+k4(7s) → k1 成功 | 200, 70704ms |
| 3ff8f296 | k0(5.6s)+k1(6.1s)+k3(45.8s)+k4(20.2s) → k2 成功 | 200, 82131ms |
| a960a708 | k2(47.2s)+k3(22.3s)+k4(5.3s) → k0 成功 | 200, 79685ms |
| ... (共19条, 5条多timeout救回) | | |

**换 key 救回机制工作良好**: 19 个中间失败全被换 key 救回 (HM1 全库 0 个"中间失败后最终也失败"的非 ATE 案例 — ATE 是 5 key 全 hang, 无中间失败可救)。

### 1i. 环境变量 (docker exec hm40006 env, 本轮未改)
| 参数 | HM1值 | HM2值(对比) | 来源 |
|---|---|---|---|
| TIER_TIMEOUT_BUDGET_S | **90** | 128 | R311 (182→90) |
| UPSTREAM_TIMEOUT | 45 | 50 | R311 (64→45) |
| KEY_COOLDOWN_S | 38 | 38 | R296 稳定 |
| TIER_COOLDOWN_S | 38 | 22 | R296 稳定 |
| MIN_OUTBOUND_INTERVAL_S | 18.2 | 4.5 | R299 (HM1流量低) |
| HM_CONNECT_RESERVE_S | 24 | 21 | R111 |
| HM_SSLEOF_RETRY_DELAY_S | 3.0 | 3.0 | R315 双机对齐 |
| NVCF_DEEPSEEK_FUNCTION_ID | 4e533b45 | (glm51_id不同) | R313 确认 |
| HM_NV_KEY_{1..5} | 5 keys | 5 keys | 全部有效 |
| 路由 | k1/k3/k5=mihomo, k2/k4=DIRECT | (HM2不同) | R310 |

## 2. 候选改动评估 (逐个数据证伪)

### 2a. 候选①: 降 BUDGET 90→85 (R317 HM2 同类已证伪, 本轮 HM1 复核) — ❌ 证伪
**直觉**: ATE avg 87s, 降到 85 让 ATE 早 2s 返回。
**反证**:
- 非流式成功 max=50.9s < 85s, 无误杀 — 但流式 getresponse 阶段需 budget
- per_attempt_timeout 公式: `min(UPSTREAM_TIMEOUT=45, remaining - CONNECT_RESERVE=24)`
  - BUDGET=85 时 attempt2 (elapsed=45s): remaining=40, per_attempt=min(45,40-24)=min(45,16)=16s
  - BUDGET=90 时 attempt2: remaining=45, per_attempt=min(45,45-24)=21s
  - 降 BUDGET 90→85 让 attempt2 从 21s→16s, **压缩换 key 救回空间**
- tier_attempts 1h 显示 3cca3c5b/3ff8f296/a960a708 等多 key 救回请求 duration 70~82s, 降 BUDGET 会误杀
- 全库 3 个非流式? 不, 是流式 85~90s 成功 (b08377b2=90269ms) — 流式不受 budget 约束, 降 BUDGET 不直接杀它,
  但其 getresponse 阶段 (若在 85~90s 边界) 会被压缩。**风险>收益, 放弃。**

### 2b. 候选②: 降 BUDGET 90→70 (让 ATE 提前 15s 返回) — ❌ 证伪
**直觉**: 非流式 max=50.9s<70s 不误杀; 流式不受 budget 不误杀; ATE 从 85s 提前到 70s。
**反证 (决定性)**: per_attempt_timeout 公式
- BUDGET=70 时 attempt1: remaining=70, per_attempt=min(45, 70-24)=min(45,46)=45s (不变)
- BUDGET=70 时 attempt2 (elapsed=45s): remaining=25, per_attempt=min(45, 25-24)=min(45,1)=max(5,1)=**5s**
- **attempt2 从 21s 暴跌到 5s** — 几乎无法救回 (NVCF p50=3s 但 timeout 是 45s 级 hang, 5s 内不可能成功)
- tier_attempts 1h 有 5 个 "多 timeout 救回" 成功请求 (3cca3c5b 等, 70~82s), 降 BUDGET=70 会全部误杀
- **净效果**: ATE 提前 15s 返回, 但牺牲多 key 救回 (救回的成功请求价值 >> ATE 提前 15s)。**有损, 放弃。**

### 2c. 候选③: 降 UPSTREAM_TIMEOUT 45→40 — ❌ 证伪 (与 R317 HM2 证伪一致)
**直觉**: 单次 timeout 45→40, 缩短 ATE。
**反证**:
- 非流式成功请求 2 个 >40s (含 1 个 50.9s) — 降 UPSTREAM_TIMEOUT=40 会误杀 (per_attempt_timeout≤40s)
- 流式 ttfb>45s 有 30 个 (虽 ttfb 含流式等待, 但 getresponse 部分受 per_attempt_timeout 约束)
- 降值误伤 40~45s 区间慢成功 (NVCF deepseek 推理慢, getresponse 慢成功常见)。**放弃。**

### 2d. 候选④: 升 UPSTREAM_TIMEOUT 45→50 — ❌ 证伪
**直觉**: 给慢 getresponse 更多时间。
**反证**: BUDGET=90 下, attempt1 per_attempt=min(45,90-24)=45s (UPSTREAM_TIMEOUT=45 已是约束).
升 UPSTREAM_TIMEOUT=50 → per_attempt=min(50,66)=50s, attempt1 可跑 50s, attempt2 remaining=40s.
但 attempt1 timeout 是 NVCF hang (平台层), 给 50s 不会成功, 反而让 ATE 单次 attempt 拖更久, 减少 attempt2 救回机会。**有损, 放弃。**

### 2e. 候选⑤: TIER_COOLDOWN 38→更高 / KEY_COOLDOWN 38→更高 — ❌ 证伪
**反证**: 30min 0 重复失败, tier_attempts 0 个 "同 key 短间隔重复失败". R296 不变量。调高降吞吐。**放弃。**

### 2f. 候选⑥: MIN_OUTBOUND 18.2→更低 (提吞吐) — ❌ 证伪
**反证**: 30min 实测请求间隔 avg=25.9s, min=0.2s (并发), max=500s. HM1 流量低 (~2.3 req/min),
18.2s throttle 不是瓶颈 (请求本身就稀疏). 调低无吞吐增益, 反增 NVCF 限流风险。**放弃。**

## 3. 优化决策: ⏸️ 无操作 — 稳定态再确认 + R317 待办闭环

### 理由
- **15min 100% (24/24)**: 完美窗口
- **30min 98.57% (69/70)**: 仅 1 NVCF 平台层 ATE (5-key 全 getresponse hang)
- **R317 待办闭环**: HM1 BUDGET=90 经复核**不误杀** — 流式请求 (>90s 成功的来源) 在 BUDGET 之外,
  非流式 max=50.9s 远低于 90s
- **所有候选改动经数据证伪**: 降 BUDGET 压缩换 key 救回空间 (2a/2b), 降 UPSTREAM_TIMEOUT 误杀慢成功 (2c),
  升 UPSTREAM_TIMEOUT 减少 attempt2 救回 (2d), cooldown/outbound 非瓶颈 (2e/2f)
- **HM1 BUDGET=90 是 getresponse 阶段换 key 救回的功能必需**: 容纳 attempt1(45s)+attempt2(21s)+... 多 key 旋转

### 为何不调任何参数
| 参数 | 当前 | 为何不调 |
|---|---|---|
| BUDGET=90 | 90 | 流式不受约束(163s能成功), 非流式max=50.9s<90s; 降值压缩attempt2救回(2a/2b证伪) |
| UPSTREAM_TIMEOUT=45 | 45 | 降值误杀40~45s慢成功(2c); 升值减少attempt2救回(2d); 已从64降至45 |
| KEY_COOLDOWN=38 | 38 | R296不变量, 0重复失败 |
| TIER_COOLDOWN=38 | 38 | 0重复失败证据, 调高降吞吐 (2e) |
| MIN_OUTBOUND=18.2 | 18.2 | HM1流量低(avg gap 25.9s), 非瓶颈 (2f) |
| CONNECT_RESERVE=24 | 24 | DIRECT keys最大开销, 非瓶颈 |
| SSLEOF_RETRY_DELAY=3.0 | 3.0 | R315 双机对齐, 30min 1次SSLEOF(handled) |

## 4. 铁律验证
| 铁律 | 状态 |
|---|---|
| 只改HM1不改HM2 | ✅ — 0 参数变更, 0 代码变更 |
| 改前必有数据 | ✅ — max(ts)锚点真实窗口 (15/30/60min) + 错误结构 + per-key + 路由分桶 + 流式/非流式分桶 + tier_attempts + per_attempt_timeout公式分析 + 6候选逐个证伪 |
| 改后必有验证 | ✅ — N/A (无操作轮) |
| 每轮少改 | ✅ — 0 变更 |
| 聚焦 hm-40006--nv | ✅ — 仅 deepseek_hm_nv 链路 |
| 数据驱动决策 | ✅ — 15min 24/24(100%), 30min 69/70(98.57%), 流式max=163s不受BUDGET约束(铁证), 非流式max=50.9s<90s, BUDGET降值压缩attempt2从21s→5s(数据决定性反证) |
| 评判: 稳定优先 > 越快越好 > 成功率 > 延迟 > 报错少 | ✅ — 零变更 = 最高稳定性, 15min 100% |

## 5. 下轮预期与建议 (供 HM1 优化 HM2)

### HM1 侧当前参数 (R318 后, 不变)
- BUDGET=90, UPSTREAM_TIMEOUT=45, KEY_COOLDOWN=38, TIER_COOLDOWN=38
- MIN_OUTBOUND=18.2, CONNECT_RESERVE=24, SSLEOF_RETRY_DELAY=3.0
- 5 keys 混合路由 (k1/k3/k5=mihomo, k2/k4=DIRECT), function_id=4e533b45
- **BUDGET=90 经本轮复核不误杀** (流式在 budget 外, 非流式 max=50.9s)

### 本轮新发现 (重要机制, 供下轮参考)
1. **流式请求不受 BUDGET 约束**: upstream.py 在 getresponse() 返回 200 后直接 return, 流式 body 由
   handlers.py `_stream_openai_passthrough` 处理, 仅受 socket read_timeout (45s间隔) 约束, 无总时长限制.
   流式可跑 163s 成功. **HM2 侧同理** — R317 担心的 HM2 ">90s 成功请求被 BUDGET=128 误杀" 可能也需
   复核: 那些 103/108/112s 成功请求若都是流式, 则 BUDGET=128 对它们无约束, 降 BUDGET 不会杀它们
   (但会压缩 getresponse 阶段换 key 救回, R317 已正确证伪).
2. **HM1 vs HM2 失败率差异**: HM1 30min 1/70=1.43% ATE, HM2 30min 1/107=0.93%. HM1 流量低 (1/4),
   单次 NVCF 平台 hang 影响比例更大, 非gateway可消.

### 给 HM1→HM2 的建议
1. 数据口径: 继续用 max(ts) 锚点回溯 (R317 §0 修正)
2. HM2 侧可复核: R317 的 103/108/112s 成功请求是否都是流式 (若是, BUDGET=128 对它们无约束,
   但降 BUDGET 仍压缩 attempt2 救回空间, R317 结论不变)
3. 守稳模式继续, NVCF 平台层间歇失败 gateway 层无法消除

## 6. 结论
HM1 hm40006 gateway 经 R311/R315/R316/R318 多轮验证已达稳定态:
- 15min 100%, 30min 98.57%, 失败为 NVCF 平台层 5-key 全 getresponse hang
- **R317 待办闭环**: HM1 BUDGET=90 不误杀 — 流式请求 (>90s 成功来源) 在 BUDGET 之外 (163s 能成功),
  非流式 max=50.9s 远低于 90s
- **新机制发现**: 流式请求输出阶段不受 BUDGET 约束 (upstream getresponse 后 return, handlers 流式循环无 budget)
- UPSTREAM_TIMEOUT=45、TIER_COOLDOWN=38、MIN_OUTBOUND=18.2 均经数据证伪不可调
- 降 BUDGET (2a/2b) 会压缩 attempt2 救回空间 (per_attempt_timeout 21s→16s/5s), 误杀多 key 救回成功请求
- 零变更 = 最高稳定性, 守稳模式继续

---

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记(交替优化序列)
