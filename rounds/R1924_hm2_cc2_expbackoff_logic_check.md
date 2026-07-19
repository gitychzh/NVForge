# R1924 (HM2 cc2): 指数退避+ms 双层方案 — 逻辑核对轮(监督者 21:15 指令 step1 核对, 未编码)

> 铁律1 (改前必有数据) ✓: 本轮 0 改动, 拉 30min nv_gw 窗口数据 (本 session 19:55Z 拉取) + 逐条核对监督者 21:15 设计要点在当前源码是否成立.
> 铁律2 (改后必有验证) ✓: 本轮 0 改动 0 restart, 验证 R1918 BUG-B 方案0 + R1913 BUG-A STAGE1 持续生效.
> 铁律3 (聚焦 40006) ✓: 只观测+核对 nv_gw(40006)+cc4101(4101), 不碰 ms_gw(40007).
> 铁律4 (写入仓库) ✓: 本文件.
> 铁律5 (改.py restart 非 up-d) ✓: 本轮 0 改动 0 restart, 沿用 R1918 restart (StartedAt 10:42:20Z).

## 上下文 (接 R1922 + 监督者 21:00/21:15 指令)

监督者 2026-07-19 21:00 定稿 + 21:15 指令交 cc2 编码实施"指数退避 + ms 双层兜底"方案:
- 层1 nv_gw per-key 指数退避 (60/120/240, chain_budget 420s) + post-200 软挂换 key
- 层2 cc4101 PRIMARY_HEADER_TIMEOUT 对齐 450s + ms 兜底不变
- 数学保证: nv 420s + ms 5s = 425s < CC API_TIMEOUT_MS 600s, 留 175s 余量, cc2 不中断

监督者明确指令 step1 = "**先核对逻辑**"(逐条核对设计在当前源码是否成立, 发现偏差修正设计再编码).
本轮职责 = 完成 step1 核对, 写入本文件 + STATE 供下一轮编码 (step2).

## 改动 (本轮 0 改动 0 restart)

**核对轮, 非 NOP 巡检也非编码轮**. 0 代码改动, 0 env 改动, 0 restart.
沿用 R1918 restart (StartedAt 10:42:20Z, 跑改后字节码).

## 数据 (30min 窗口, 本 session 19:55Z 拉取) — 确认链路稳供核对基底

### nv_gw 成功率 + 错误分类
```
status | count
-------+-------
200    |    35
502    |     3
```
**SR = 35/38 = 92.1%** (抖动区间常态, 稳定; R1922 90.5%→R1924 92.1%, 非退化).

502=3 全 NVCF 上游侧 (nv_requests.error_type 字段空, 但 tier 表 pexec_empty_200×5 + IntegrateTimeout×1 → 同源 zombie/IntegrateTimeout 被 retry 吸收到 200, 非 nv_gw 旋钮可解).

### tier 错误分类 30min
```
error_type      | count
----------------+-------
pexec_success   |    28
pexec_empty_200 |     5
IntegrateTimeout|     1
```
全已知类型. pexec_empty_200 5 (zombie 同源, 被 retry 重吸收到 200). 无 500_nv_error / SSLEOFError / timeout.

### 关键机制日志计数 (30min)
| 日志 | 计数 | 说明 |
|---|---|---|
| NV-GLM52-CHAIN-SKIP-PEXEC2 | 5 | BUG-A STAGE1 持续实战触发 (R1913 落地, R1921 首触发→R1922 6→R1924 5, 稳定). 跳过 `_try_tier_keys` 第二轮 pexec, 每 次 省 ~120s, 全转 all_keys_exhausted → ms_fb 兜回. |
| NV-TOOLCALL-JSON-DOWNGRADE | 2 | bug8 真降级在位零星触发 (args 真不合法导致真降级, final_stop=end_turn, CC SDK 忽略已 relay partial_json, 不中断). |
| stream_absolute_cap / NV-CAP-ABS | 0 | **abs_cap 502 持续归零 (连续第 5 轮 R1919-R1924 窗口纯净)**. R1918 BUG-B 方案0 (peek 健康分支补 cap_origin 重置) 持续生效. |
| breaker OPEN | 0 | 连续多轮 OPEN=0 (本轮 BREAKER-FAIL 全被 CLOSED 吸收). |

### fallback (cc4101 30min)
- **FALLBACK-OK = 8** 全成功 ms_gw 兜回, **0 真中断**.
- 全部 8 条 75s SKIP-CIRCUIT (primary timeout ~75s < chain budget, cc4101 bug3 preempt, NOT counted toward circuit).
- CC4101-UPSTREAM-ERROR-SEEN (非跳过类真中断) = **0**. 用户诉求 "可以报错但不能让 cc2 中断" (2026-07-19 01:40) 仍达成.

## cc2 逻辑核对 (监督者 21:15 核对清单 7 条逐条核对结果)

### 当前 env + StartedAt 实况 (纠正 STATE.md 旧心智模型)
- nv_gw StartedAt = **2026-07-19T10:42:20Z** (R1918 restart, R1919-R1924 未再 restart). STATE.md 旧值 21:26:29Z 是 R1836, 已过时.
- `UPSTREAM_TIMEOUT=66`, `NVU_TIER_BUDGET_GLM5_2_NV=120` (非 STATE 旧心智"70s"), `NVU_STREAM_ABSOLUTE_CAP_S=150`.
- cc4101 `PRIMARY_HEADER_TIMEOUT=60`, `CC4101_PRIMARY_FAIL_THRESHOLD=3`, `CC4101_PRIMARY_SKIP_S=30`.
- cc4101 `CC4101_STREAM_TOTAL_DEADLINE_S` env 未显式设 → 走 config.py:26 默认 **360s** (ttfb 后绝对总时长兜底, stream.py:84/121 raise socket.timeout 中断流).
- cc4101 `CC4101_STREAM_IDLE_GAP_S` env 未显式设 → 走默认 **100s** (真静默兜底).
- **无** `NVU_GLM52_EXP_BACKOFF` env → 指数退避尚未实施 (本轮核对基底确认).

### 核对清单逐条

**[1] per_attempt_timeout 当前计算逻辑** ✓ 成立
- upstream.py:208 (integrate) + :583 (pexec) + :1067 (`_glm52_single_attempt` 内): `per_attempt_timeout = max(MIN_ATTEMPT_TIMEOUT, min(UPSTREAM_TIMEOUT or override, remaining_budget - CONNECT_RESERVE_S))`.
- 设计"按 attempt_idx 指数递增"插入点清晰: 改 `min(UPSTREAM_TIMEOUT, ...)` 为 `min(exp_timeout(attempt_idx), ...)` where exp_timeout = 60/120/240. 开关 `NVU_GLM52_EXP_BACKOFF=true` gate.
- 注意: `_glm52_single_attempt` 是 mode_chain 的 per-attempt 函数 (每 attempt 1 key+1 mode), 与 `_try_tier_keys` (line 194 _n_iter loop) 不同. mode_chain 7 轮在 `_try_glm52_mode_chain` (line 1253, `for attempt in range(NVU_NUM_KEYS + 2)`).

**[2] 循环上界 7 轮 vs 指数退避 3 轮** ✓ 需 cc2 定
- mode_chain `for attempt in range(NVU_NUM_KEYS + 2)` = 5+2=7 轮 (每轮 1 key 走绑定 mode). 指数退避只需前 3 轮达 60/120/240=420s.
- 建议: **保留 7 轮循环上界**, per-key timeout 指数递增 (前 3 轮 60/120/240, 第 4+ 轮封顶 240). 理由: 7 轮容 NVU_NUM_KEYS=5 key 全挂+2 容错, 指数退避只改 timeout 档不改循环数, 最小改动. 后 4 轮封顶 240s 不再指数 (已到单 key 上限), 总 chain_budget=420s 仍由 budget break 兜底.
- 待编码轮定: 是否改循环上界为 3 (更激进) 或保留 7 (更稳). 倾向保留 7.

**[3] chain_budget 70→420 与大请求 300s 档** ⚠️ **设计偏差**
- 当前 `_glm52_single_attempt` chain_budget (upstream.py:1003): `float(os.environ.get(f"NVU_TIER_BUDGET_{tier_model.upper()}", "70"))` → env=120 (非设计预想的 70s).
- 且 R1418 加了按 input 缩放: `_chain_ic > 350000 → max(budget, 300)`, `>200000 → max(budget, 240)`. 大请求已 300s.
- 设计"chain_budget 70→420"心智模型过时. 实际: 小请求 120→420 (大跳 +300s), 大请求 300→420 (一致). 需编码轮明确: 是改 env `NVU_TIER_BUDGET_GLM5_2_NV=120→420` 还是改 `_glm52_single_attempt` 内部 chain_budget 计算? 倾向改 env (单点, 可回滚).

**[4] handlers.py 软挂点 5 处 (zombie/abs_cap/no_content_gap 分支)** — 本轮未深挖, 留编码轮
- 设计说 "handlers.py 5 处 zombie + abs_cap + no_content_gap 分支加换 key 调用". 需编码轮 grep 定位 (R1675/R1774 记录).
- R1918 BUG-B 方案0 已治 abs_cap peek 误判 (连续 5 轮归零), abs_cap 现已低频, 软挂换 key 的 abs_cap 分支收益降低. zombie + no_content_gap 是主战场.

**[5] post-200 软挂换 key 时 message_start_sent 重放容错** 🔴 **最大风险点, 编码轮必先验证**
- peek 通过后 send_response(200) 已发 → converter._emit_message_start 可能已 True → 换 key 重放新流会让 cc4101 看到重复 message_start.
- cc4101 透传层 (R1705/R1711) 是否容错重复 message_start? **本轮未验证, 编码轮必先验证**.
- 若不容错: 需在 nv_gw 换 key 前先 close conn (发 EOF) 让 cc4101 当 stall 处理, 还是直接重放? 这是 step2 编码前必须确定的协议.
- 缓解: 复用 R1774 graceful end (zombie+有内容发 graceful end, 零内容 event:error). 但换 key 是新流, 需 cc4101 端容错重复 message_start. **建议编码轮 step2.0 先在 cc4101 端加重复 message_start 容错 (或确认已容错), 再动 nv_gw 软挂换 key**.

**[6] cc4101 STREAM_TOTAL_DEADLINE 抢断** 🔴 **坑确认存在且更复杂**
- config.py:26 `CC4101_STREAM_TOTAL_DEADLINE_S=360` (默认, env 未设), stream.py:84/121 raise socket.timeout 中断流.
- 指数退避让单 key 跑到 240s, + ttfb 慢 (NVCF 常 60-148s 才首字节) → 总时长撞 360s 被 cc4101 stall-watcher 先杀.
- **必须同步改**: `CC4101_STREAM_TOTAL_DEADLINE_S` env 360→480+ (容 nv 420s + ttfb + 余量). 或 config.py 默认改.
- 这是第 3 个要改的组件 (不只 nv_gw + cc4101 env, 还有 cc4101 stream.py 的 stall-watcher). 编码轮需纳入计划.

**[7] abs_cap/cap 与指数退避冲突** 🔴 **坑确认存在**
- `NVU_STREAM_ABSOLUTE_CAP_S=150`. 指数退避延长单 key 到 240s → abs_cap (150s) 会在单 key 跑到 150s 时提前触发截断.
- R1918 BUG-B 方案0 治了 peek 慢误判 (cap_origin 重置), abs_cap 连续 5 轮归零. 但指数退避延长单 key 后, 单 key 内的 abs_cap 仍可能触发 (NVCF 首块后中途软挂).
- **需编码轮同步**: (a) `NVU_STREAM_ABSOLUTE_CAP_S` 150→250 容指数退避; 或 (b) abs_cap 触发时换 key 而非直接 502 (与软挂换 key 同机制, 见[5]). 倾向 (b) — abs_cap 触发换 key 是软挂换 key 的一部分, 一并解决.

## 本轮结论

**核对完成, 发现 3 处设计偏差 + 2 个最高风险点, 本轮不编码**. 理由:
1. 监督者 21:15 指令 step1 = "先核对逻辑", 已完成 7 条逐条核对.
2. 发现偏差需先修正设计: [3] chain_budget 70→420 心智过时 (实际 120+input 缩放); [6] cc4101 STREAM_TOTAL_DEADLINE=360 抢断坑确认 (需同步改 480+); [7] abs_cap 150 与指数退避冲突 (需同步改或换 key).
3. [5] message_start 重放容错是最大风险点, 编码轮 step2.0 必先验证 cc4101 透传层行为, 否则软挂换 key 会引入重复 message_start 报错.
4. **当前链路稳**: SR 92.1% / 0 真中断 / abs_cap 连续 5 轮归零 / BUG-A 持续触发省 ~120s/fallback. 用户诉求"可以报错但不能让 cc2 中断"已达成. 跨 3 组件大改造若编码中途会话结束留半成品 bind-mount 代码在运行容器, 会破坏当前稳定状态, 反而引入中断风险 — 与用户诉求直接冲突.
5. 铁律1 (无据不改) + 监督者原话 "不要硬改, 攒数据后动". 本轮核对结论 = 给编码轮的数据/设计基底.

**下一轮 (R1925) 该做**: 编码轮 step2. 先做 step2.0 (cc4101 端容错重复 message_start 验证 + STREAM_TOTAL_DEADLINE 360→480), 再做 step2.1 (nv_gw per-key 指数退避 + abs_cap/cap 同步). 一轮一个点, 不一次全改.

## 介入决策 (为何本轮不编码)

- SR 92.1% 抖动区间常态非退化, 未达"连续 3+ 轮跌破 80%"介入线.
- 502=3 全 NVCF 上游侧 (zombie/IntegrateTimeout 被 retry 吸收到 200), 非新可配置类.
- breaker OPEN 0 连续多轮.
- 指数退避方案虽获用户授权, 但 step1 核对发现设计偏差需修正设计, step2 编码需先验证 cc4101 透传层 (最大风险点), 本轮完成 step1 = 价值交付, 不强行编码留半成品.
