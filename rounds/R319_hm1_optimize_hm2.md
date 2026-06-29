# R319: HM1→HM2 — ⏸️ 无操作: BUDGET=128 经 121.6s 末端救回案例决定性证伪不可降 (15min 93.10%, 30min 97.75%)

**时间**: 2026-06-30 01:25 UTC
**角色**: HM1 (opc_uname) 工程师 / HM2 (opc2_uname) 反对者
**前轮**: R318 (HM2→HM1, ⏸️ 无操作, BUDGET=90 复核不误杀, 流式不受 budget 约束机制发现)
**本轮基线 max_ts**: 2026-06-30 01:17:47 UTC (HM2 DB, host_machine='opc2sname', max(ts)锚点回溯, 采纳 R317 §0 口径)

## 0. R318 待办回应 (本轮核心使命)

R318 §5 留待办: "HM2 侧可复核 R317 的 103/108/112s 成功请求是否都是流式 (若是, BUDGET=128 对它们无约束,
但降 BUDGET 仍压缩 getresponse 阶段换 key 救回空间)". **本轮跨机复核 HM2 此项并升级论证.**

**复核结论 (决定性, 比 R317 更强)**: HM2 BUDGET=128 **不可降** — 本轮发现 **121.6s 末端救回成功案例** (6c12a16f),
比 R317 当时已知的最长 112s 案例多 9.6s, 贴 BUDGET=128 上限更紧. 详见 §2a 模拟.

## 1. 数据收集 (真实窗口, max_ts=2026-06-30 01:17:47 UTC 锚点)

### 1a. 多窗口成功率
| 窗口 | total | success | fail | 成功率 |
|---|---|---|---|---|
| 15min | 29 | 27 | 2 | **93.10%** |
| 30min | 89 | 87 | 2 | **97.75%** |
| 60min | 211 | 208 | 3 | 98.58% |
| 120min | 341 | 329 | 12 | 96.48% |

注意: 15min/30min 成功率 (93.10%/97.75%) 低于 R317 (100%/99.07%) — 因 01:07~01:11 出现 2 次 ATE 集中
(NVCF 平台层 4 分钟内整批 hang 2 次). 60min/120min 反弹到 98.58%/96.48%, 与 R317 同量级, 非劣化趋势,
属 NVCF 平台层间歇集中失败 (低频散布 + 偶发簇状).

### 1b. 30min 错误结构
| error_type | n | avg_dur | p50 | p95 | max_dur |
|---|---|---|---|---|---|
| (success) | 87 | 14381 | 8406 | 58019 | 121567 |
| all_tiers_exhausted | 2 | 123238 | 123238 | 124044 | 124134 |

**2个ATE**: 3ddd8ce7 (124.1s), 2a70206c (122.3s), 均流式 stream=t, nv_key_idx=NULL (5 key 全失败), ttfb=NULL.
**0 SSL计入DB, 0 empty_200, 0 429, 0 rate/limit** (全库 120min 验证, §1g).

### 1c. Per-key 成功延迟 (30min, success only)
| Key (idx) | n | avg_dur | p50 | p95 |
|---|---|---|---|---|
| k0 (k1, mihomo7894) | 16 | 13528 | 8805 | 42082 |
| k1 (k2, DIRECT) | 15 | 12069 | 9339 | 28465 |
| k2 (k3, mihomo) | 15 | 14326 | 7773 | 39109 |
| k3 (k4, DIRECT) | 16 | 14965 | 6596 | 58112 |
| k4 (k5, mihomo7899) | 13 | 20537 | 8719 | 73629 |

5 key 均匀 (13~16), P50=6.6~9.3s, P95=28~74s. 无单 key 劣化.

### 1d. 30min 延迟百分位 (success only)
| 指标 | 值 |
|---|---|
| P50 duration | 8406ms |
| P95 duration | 58019ms |
| avg duration | 14381ms |
| P50 ttfb | 8313ms |
| P95 ttfb | 57744ms |

P50=8.4s (R317 P50=7.4s, +1s 正常波动). HM2 P50 远低于 HM1 (32s) — glm5.1 模型推理快于 deepseek.

### 1e. ATE 完整生命周期 (docker logs, 本轮 2 个 ATE 实测)

**ATE 2a70206c** (01:07:41 → 01:09:46, 124.1s):
```
attempt1 k4 → timeout 52.1s (total 52.1s)       [per_attempt=50s]
attempt2 k5 → timeout 50.5s (total 102.6s)      [per_attempt=50s, budget 剩 25.4s]
attempt3 k1 → timeout 11.0s (total 113.6s)      [末端 MIN_ATTEMPT_TIMEOUT=10 兜底]
attempt4 k2 → timeout 10.6s (total 124.1s)      [末端 MIN=10, budget 128 耗尽 break]
→ TIER-FAIL: timeout=4, other=0 (k3 未试到, budget 用尽)
```

**ATE 3ddd8ce7** (01:10:38 → 01:11:50, 122.3s):
```
attempt1 k5 → timeout 50.3s (total 50.3s)
attempt2 k1 → timeout 50.9s (total 101.2s)
attempt3 k2 → timeout 10.6s (total 111.8s)      [末端 MIN=10]
attempt4 k3 → timeout 10.5s (total 122.3s)      [末端 MIN=10, budget 耗尽 break]
→ TIER-FAIL: timeout=4, other=0 (k4 未试到)
```

**关键模式**: 2 个 ATE 都是 "前 2 个 key 各跑满 ~50s timeout, budget 剩 ~25s, 后 2 个 key 各只跑 ~10s
(MIN_ATTEMPT_TIMEOUT 兜底) 就被 budget 截断". 共试 4 个 key, 第 5 个 key 无机会.
**末端 10s attempt 对 NVCF 50s 级 hang 几乎无成功可能** — 但见 §1f 反例.

### 1f. 本轮决定性新发现: 末端 10s attempt 救回成功案例 (6c12a16f)

**6c12a16f**: status=200, duration=**121567ms (121.6s)**, nv_key_idx=4 (第5 key 成功), stream=t, ttfb=121146ms.
```
attempt1 k1 → timeout 50.5s (total 50.5s)
attempt2 k2 → timeout 50.6s (total 101.1s)
attempt3 k3 → timeout 10.5s (total 111.6s)      [末端 MIN_ATTEMPT_TIMEOUT=10]
attempt4 k4 → SUCCESS, ttfb=121146ms            [k4 attempt 开始 111.6s, 首字节 121.1s, 即 9.4s 内拿到首字节]
```
**关键**: k4 是末端 attempt (per_attempt_timeout=10s, MIN 兜底), 但它在 **9.4s 内成功拿到首字节** (9.4s < 10s),
之后进入 handlers.py 流式循环 (不受 BUDGET 约束, R318 §0 机制) 完成输出.
**这证明末端 10s MIN_ATTEMPT_TIMEOUT 窗口并非总是 doomed — 当 NVCF 在末端窗口恢复时, 10s 足够拿到首字节救回请求.**

**全库最长成功 top5** (HM2 全库 582 成功):
| rid | duration | final_key | stream | ttfb |
|---|---|---|---|---|
| 6c12a16f | 121567 | k4 | t | 121146 |
| 6c89d283 | 120450 | k0 | t | 120444 |
| 1b7a3b90 | 112252 | k2 | t | 112152 |
| aea8172e | 111345 | k0 | t | 111341 |
| d8ef4cda | 108203 | k3 | t | 107128 |

全库 7 个 >90s 成功, **全部是流式** (R318 §5 待办复核确认). 2 个 >120s (6c12a16f/6c89d283) 贴 BUDGET=128 上限.

### 1g. 错误类型全分布 (120min, 排除限流/重复失败)
| error_type | n_120min | n_30min | 性质 |
|---|---|---|---|
| success_200 | 323 | 85 | — |
| all_tiers_exhausted | 11 | 3 | NVCF 平台层整批 hang |
| NVStream_IncompleteRead | 1 | 0 | 流式读取中途断开 (见 §2c) |
| 429 / empty200 / rate-limit | 0 | 0 | **无 NVCF 限流** |

per-key timeout 分布 (120min, tier_attempts): k0=3, k1=8, k2=6, k3=6, k4=3 — 无单 key 集中劣化,
5 key 均有 timeout, avg elapsed=50~56s (UPSTREAM_TIMEOUT=50 边界). **确认 ATE 是 NVCF 平台层整批不可用, gateway 无计可消.**

### 1h. 环境变量 (docker exec hm40006 env, 本轮未改)
| 参数 | HM2值 | HM1值(对比) | 来源 |
|---|---|---|---|
| TIER_TIMEOUT_BUDGET_S | **128** | 90 | HM2历史 (本轮再确认不可降) |
| UPSTREAM_TIMEOUT | 50 | 45 | R315 (58→50) |
| KEY_COOLDOWN_S | 38 | 38 | R296 稳定 |
| TIER_COOLDOWN_S | 22 | 38 | HM2历史 |
| MIN_OUTBOUND_INTERVAL_S | 4.5 | 18.2 | HM2历史 (流量4倍于HM1) |
| HM_CONNECT_RESERVE_S | 21 | 24 | HM2历史 |
| HM_SSLEOF_RETRY_DELAY_S | 3.0 | 3.0 | R315 双机对齐 |
| NVCF_GLM51_FUNCTION_ID | 4e533b45 | (deepseek_id不同) | R313 |
| 5 keys 路由 | k1/k3/k5=mihomo, k2/k4=DIRECT | (HM1同结构) | R310 |

## 2. 候选改动评估 (逐个数据证伪)

### 2a. 候选①: 降 BUDGET 128→120/110 (R317 同类, 本轮用 121.6s 新案例升级证伪) — ❌ 证伪 (决定性)
**直觉**: ATE avg 123s, 降到 120 让 ATE 早 ~3s 返回; 降更多更早.
**反证 (本轮新数据, 决定性)**: 6c12a16f (121.6s 成功) 是末端 10s 窗口救回的真实案例. 模拟 per_attempt_timeout
公式 `max(MIN=10, min(UT=50, remaining - CONNECT_RESERVE=21))` + budget 剩余 <10 则 break:

| BUDGET | attempt1 k1 | attempt2 k2 | attempt3 k3 | attempt4 k4 | 6c12a16f 命运 |
|---|---|---|---|---|---|
| **128 (当前)** | 50s timeout | 50s timeout | 10s timeout (MIN) | **10s SUCCESS (9.4s首字节)** | ✅ 救回 |
| 120 | 50s timeout | 48.5s timeout | 10s timeout | remaining=8.4 <10 → **BREAK** | ❌ 误杀 (k4 永不试) |
| 110 | 50s timeout | 38.5s timeout | remaining=8.9 <10 → **BREAK** | (k3/k4 都不试) | ❌ 误杀 |

**结论**: 降 BUDGET 到 120 就会让 6c12a16f 的 k4 末端 attempt 永不被触发 (remaining=8.4 < MIN=10 → break),
误杀这个 121.6s 成功请求. 降到 110 更糟 (k3/k4 都不试). R317 当时仅基于 112s 案例证伪, 本轮用 121.6s 案例
**升级论证** — BUDGET=128 的末端 10s 窗口是救回边界成功请求的功能必需. **反对者必驳, 放弃.**

### 2b. 候选②: 降 UPSTREAM_TIMEOUT 50→45 (对齐 HM1) — ❌ 证伪 (R317 同结论)
**反证**: per-key timeout avg elapsed=50~56s (k0=56.1s, k1=54.4s, k2=54.4s, k4=54.9s), 多数略超 50s.
5af0103f 等成功请求单 attempt 耗时 42.6s (R317 §2c). 降 UPSTREAM_TIMEOUT=45 会误伤 45~50s 区间慢成功
(NVCF glm5.1 大上下文推理慢, 流式首 token 晚). HM2 流量 4 倍于 HM1, 大上下文占比高, 边界风险 > HM1.
**放弃.**

### 2c. 候选③: NVStream_IncompleteRead 流式重试 (改代码逻辑) — ❌ 证伪
**背景**: fb356457 (06-30 00:06:36) error_type=NVStream_IncompleteRead, duration=8.9s, nv_key_idx=2 (k3),
stream=t. handlers.py:298 捕获 IncompleteRead 后直接置 502, **不换 key 重试** (流式已拿到 200 响应头,
中途 NVCF 断流).
**反证**:
- **频率极低**: 120min 仅 1 次 (0.3%), 30min 0 次 — 改了收益微乎其微
- **风险高**: 流式重试 = 重新发整个 prompt 到新 key, 但客户端可能已收到部分 token — 重试会导致
  内容重复/状态混乱, 且重试成本 = 重新推理 (NVCF 计费 + 延迟翻倍)
- **属改代码逻辑**, 违反 "单参数/单逻辑点少改" 且不可逆风险大
- 按 "稳定优先", 不应为 0.3% 低频失败引入高风险代码改动. **放弃.**

### 2d. 候选④: TIER_COOLDOWN 22→38 / KEY_COOLDOWN 38→更高 — ❌ 证伪 (R317 同结论)
**反证**: 120min 0 重复失败, 0 同 key 短间隔重复失败模式. per-key timeout 散布全 5 key, 非 cooldown 不足.
调高反而延长 tier 恢复降吞吐. **放弃.**

### 2e. 候选⑤: MIN_OUTBOUND 4.5→更高 — ❌ 证伪 (R317 同结论)
**反证**: 120min 0 个 429/empty200/rate-limit (§1g). HM2 流量 4 倍于 HM1, 4.5s 间隔是吞吐必需.
调高直接降吞吐, 违背 "单位时间请求越多越好". **放弃.**

### 2f. 候选⑥: 升 BUDGET 128→更高 (给末端更多救回空间) — ❌ 证伪
**直觉**: 给 6c12a16f 这类末端救回更多余量.
**反证**: 当前 max 成功=121.6s < BUDGET=128, 已有 6.4s 余量. ATE avg=123s (受 budget 截断在 122~128s).
升 BUDGET 会让 ATE 拖更久 (末端 doomed attempt 跑更多次), 增加 ATE 延迟而不增加成功 (NVCF 整批 hang 时
多给时间也不会恢复). **有损 (延迟升, 成功率不变), 放弃.**

## 3. 优化决策: ⏸️ 无操作 — 稳定态再确认 + R318 待办闭环

### 理由
- **30min 97.75% (87/89)**: 2 ATE 为 NVCF 平台层 4 分钟内集中整批 hang
- **60min 98.58%, 120min 96.48%**: 与 R317 同量级, 非劣化趋势
- **R318 待办闭环**: HM2 侧 >90s 成功请求**全部是流式** (7/7), BUDGET=128 对流式输出阶段无约束 (R318 §0 机制),
  但降 BUDGET 仍压缩 getresponse 阶段末端 attempt 救回空间 — 本轮用 6c12a16f (121.6s) 决定性证伪
- **本轮新发现 (重要)**: 6c12a16f 证明末端 10s MIN_ATTEMPT_TIMEOUT 窗口能救回边界成功请求 (k4 在 9.4s 拿首字节),
  这是 BUDGET=128 不可降的**最强证据** (比 R317 的 112s 案例更贴边界)
- **所有候选改动经数据证伪**: 降 BUDGET 误杀 121.6s 救回 (2a), 降 UPSTREAM_TIMEOUT 误伤 45~50s 慢成功 (2b),
  NVStream 重试风险>>收益 (2c), cooldown/outbound 非瓶颈 (2d/2e), 升 BUDGET 增 ATE 延迟 (2f)

### 为何不调任何参数
| 参数 | 当前 | 为何不调 |
|---|---|---|
| BUDGET=128 | 128 | 降值误杀 6c12a16f (121.6s末端救回) (2a决定性证伪); 升值增ATE延迟 (2f) |
| UPSTREAM_TIMEOUT=50 | 50 | 降值误伤 45~50s 慢成功 (2b), R315 已优化 |
| KEY_COOLDOWN=38 | 38 | R296 不变量, 0 重复失败 (2d) |
| TIER_COOLDOWN=22 | 22 | 0 重复失败证据, 调高降吞吐 (2d) |
| MIN_OUTBOUND=4.5 | 4.5 | 0 限流错误, 调高降吞吐 (2e) |
| CONNECT_RESERVE=21 | 21 | 非瓶颈 |
| SSLEOF_RETRY_DELAY=3.0 | 3.0 | R315 双机对齐, 运行良好 |
| (代码) NVStream 重试 | 不重试 | 0.3% 低频, 流式重试风险高 (2c) |

## 4. 铁律验证
| 铁律 | 状态 |
|---|---|
| 只改HM2不改HM1 | ✅ — 0 参数变更, 0 代码变更 (仅 ssh 读对端 DB/logs/源码) |
| 改前必有数据 | ✅ — max(ts)锚点真实窗口 (15/30/60/120min) + 错误结构 + per-key + 2 ATE 完整生命周期 + 6c12a16f 末端救回案例 + 全库最长成功 top5 + per-key timeout 分布 + per_attempt_timeout 公式模拟 + 6候选逐个证伪 |
| 改后必有验证 | ✅ — N/A (无操作轮) |
| 每轮少改 | ✅ — 0 变更 |
| 聚焦 hm-40006--nv | ✅ — 仅 glm5.1_hm_nv 链路 |
| 数据驱动决策 | ✅ — 30min 87/89(97.75%), 6c12a16f(121.6s末端10s窗口救回)决定性证伪降BUDGET, 模拟BUDGET=120→remaining=8.4<10→break→误杀 |
| 评判: 稳定优先 > 越快越好 > 成功率 > 延迟 > 报错少 | ✅ — 零变更 = 最高稳定性, 不为 0.3% 低频失败引入高风险代码改动 |

## 5. 下轮预期与建议 (供 HM2 优化 HM1)

### HM2 侧当前参数 (R319 后, 不变)
- BUDGET=128, UPSTREAM_TIMEOUT=50, KEY_COOLDOWN=38, TIER_COOLDOWN=22
- MIN_OUTBOUND=4.5, CONNECT_RESERVE=21, SSLEOF_RETRY_DELAY=3.0
- 5 keys 混合路由 (k1/k3/k5=mihomo, k2/k4=DIRECT), function_id=4e533b45
- **BUDGET=128 经本轮 121.6s 末端救回案例升级证伪不可降** (比 R317 的 112s 更贴边界)

### 本轮新发现 (重要机制, 供下轮参考)
1. **末端 MIN_ATTEMPT_TIMEOUT=10 窗口能救回边界成功请求**: 6c12a16f 在 k1/k2/k3 各 timeout 后,
   k4 于末端 10s 窗口内 9.4s 拿到首字节成功 (之后流式不受 BUDGET 约束). **这是 BUDGET=128 不可降的最强证据** —
   降 BUDGET 会让 remaining<10 提前 break, k4 永不被试. HM1 侧 BUDGET=90 同理: 若 HM1 也有末端 10s 救回案例,
   降 BUDGET=90 同样会误杀 (R318 已用流式不受 budget 约束论证, 本轮 HM2 侧用末端 attempt 视角补充).
2. **NVStream_IncompleteRead 失败模式**: 流式请求拿到 200 后中途断流, handlers.py:298 直接 502 不重试.
   频率极低 (0.3%), 暂不优化. 若未来频率上升, 可考虑 "首字节前断流才重试" 的安全策略 (首字节后断流重试风险高).
3. **ATE 簇状集中**: 01:07~01:11 的 4 分钟内 2 次 ATE, 提示 NVCF 平台层有间歇性整批不可用窗口,
   非 gateway 可消. HM1 侧若也观察到簇状 ATE, 同属平台层.

### 给 HM2→HM1 的建议
1. 数据口径: 继续用 max(ts) 锚点回溯
2. HM1 侧可复核: 是否有末端 10s MIN_ATTEMPT_TIMEOUT 窗口救回的成功请求 (类似 6c12a16f) —
   若有, 进一步强化 BUDGET=90 不可降; 若无, BUDGET=90 仍有���值空间需重新评估 (R318 已从流式角度证伪,
   但末端 attempt 视角未查)
3. 守稳模式继续, NVCF 平台层间歇失败 gateway 层无法消除

## 6. 结论
HM2 hm40006 gateway 经 R313/R315/R316/R317/R319 多轮验证已达稳定态:
- 30min 97.75%, 60min 98.58%, 失败为 NVCF 平台层间歇整批不可用 (簇状集中)
- **R318 待办闭环**: HM2 侧 >90s 成功请求全部是流式 (7/7), BUDGET=128 对流式输出无约束
- **本轮决定性新发现**: 6c12a16f (121.6s 成功) 证明末端 10s MIN_ATTEMPT_TIMEOUT 窗口能救回边界成功请求
  (k4 在 9.4s 拿首字节) — BUDGET=128 不可降的**最强证据** (降 BUDGET=120 → remaining=8.4<10 → break → k4 永不试 → 误杀)
- UPSTREAM_TIMEOUT=50、TIER_COOLDOWN=22、MIN_OUTBOUND=4.5 均经数据证伪不可调
- NVStream_IncompleteRead (0.3% 低频) 暂不优化 (流式重试风险>>收益)
- 零变更 = 最高稳定性, 守稳模式继续

---

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记(交替优化序列)
