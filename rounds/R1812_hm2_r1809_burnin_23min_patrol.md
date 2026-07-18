# R1812 — HM2 cc2: R1809 burn-in 23min 巡检轮, 不改代码

> 铁律：只改 HM2，不改 HM1，不碰 proxy/ms-gw。改前必有数据，改后必有验证。
> 本轮性质：**巡检轮**（非新改）。R1809 全 pexec 生效 ~23min，攒够 48req burn-in 数据，
> 确认 bug2(stream_no_content_gap)/bug1(SSE malformed) 归零趋势是否成立。

## 数据（拉于 2026-07-19 00:25 CST = 16:25 UTC, R1809 生效 16:00:08 UTC, 已 ~23min）

### 切换前后拼接 1h 趋势（PRE 混 integrate+pexec / POST 全 pexec）
| 窗口 | 200 | 502 | SR | avg(ms) | max(ms) |
|---|---|---|---|---|---|
| PRE_R1809 (~15:22-16:00 UTC) | 65 | 7 | 90.3% | 25553 | 63631 |
| POST_R1809 (16:00-16:25 UTC) | 49 | 5 | **90.7%** | 23727 | 274944 |

整体 SR 切换前后持平 ~90%（未到 95% 全胜线）。POST 窗 max 274s 是 pexec 僵尸流(见下)。

### 切换后纯 pexec 窗（16:00-16:25 UTC, 23min, 54req）
- SR = **49/54 = 90.7%**
- 错误分类: stream_absolute_cap **2** / stream_first_byte_timeout **2** / all_tiers_exhausted **1**(16:02 过渡期残余)
- 成功延迟: count=43, avg=20885ms, p50=19452, p90=34274, max=69562（**无 hang 长尾**，integrate 期 max 135886 已消失 ✓）
- **stream_no_content_gap = 0 条**（30min 窗）✓ **bug2 治本成立**
- **SSE malformed "could not parse" = 0 条**（30min/全天 nv_gw 日志 grep 全空）✓ **bug1 也未复发**

### 5 条失败逐条真因（从 nv_error_detail.2026-07-19.jsonl）
1. **16:02:45 all_tiers_exhausted** (fa202f2c, 66s) — 重启瞬态过渡残余, dsv4p_nv tier
2. **16:12:30 stream_absolute_cap** (3a2ef7f3, 247s, content_chars=0) — **pexec 僵尸流**
   - tier glm5_2_nv 4 key 全试: k2 pexec_empty_200 / k3 pexec_timeout(58s) / k2 504_nv_gateway_timeout / k3 NVCFPexecTimeout(57s)
   - 同一 function_id `3b9748d8...` → 上游 NVCF glm-5.2 function 整体间歇挂
3. **16:12:37 stream_first_byte_timeout** (3a0f6ac8, 95s) — pexec 首字节超时, 合法 fallback
4. **16:17:04 stream_absolute_cap** (ad179e0f, 274s, content_chars=0) — 同 #2, 同一 function_id, k0 empty_200/k1 timeout/k0 empty_200/k1 NVCFPexecTimeout
5. **(15:58-16:02 残余 first_byte/all_tiers 已归入 PRE 窗)**

### fallback 率（cc4101 30min 日志）
- 30min **12 次** PRIMARY-FAIL, 全 75s ttfb timeout → SKIP-CIRCUIT（< chain budget 120s, 不计 circuit）
- 3 批: 23:58/00:09/00:13 CST = 15:58/16:09/16:13 UTC
- **bug3 未修**: cc4101 75s 抢断 < nv_gw chain budget 120s, 抢断甩 ms。但本轮 12 次 fallback 里 **2 条对应 cap 事件(16:12/16:17)实际是 nv_gw 自己 cap 杀僵尸流(240s+)**, 不全是 bug3 抢断。

## 结论
1. **R1809 源头治本成立**: bug2(stream_no_content_gap) 切换后 23min/54req **0 条**（对照切换前 1h 2 条全 integrate）。bug1(SSE malformed) 同期也 **0 条**。pexec 延迟更优（max 69562 vs integrate 135886 hang 长尾消失）。
2. **但 SR 未达 95% 全胜线**（90.7%）, 主因不是 bug1/bug2, 是 **pexec 僵尸流**(2 条 cap, content_chars=0, 上游 NVCF glm-5.2 function 间歇挂 4 key 全空/超时) + first_byte_timeout(2 条合法 fallback) + 1 过渡残余。
3. **新失败模式定位**: pexec 僵尸流 = 上游 NVCF 服务问题（function_id `3b9748d8` 间歇挂）, **非 nv_gw 配置可治**。cap=150s 留作兜底正确, 但 cap break 后 tier 内仍跑到 240s(absolute cap break 与 tier abort chain 衔接有 lag, 下轮可查源码是否 cap break 后硬中止)。

## 为何不改（巡检轮依据）
1. R1809 核心假设（pexec 消除 integrate 9% 失败）**已由 bug2/malformed 双归零 + 延迟更优证实**, 无需再改。
2. 当前 90.7% SR 的失败主因是**上游 NVCF 服务间歇挂**, 改 nv_gw 配置治不了（调高 cap 只会拖长死循环, 违反"宁可走 ms 也不死循环"; 调低 cap 会误杀正常慢流）。
3. cap break→tier abort 衔接 lag 是潜在改进点, 但**改源码风险高**, 需先攒更多失败样本确认模式稳定（当前仅 2 条）。
4. 遵守小步快走: 本轮攒够 23min/54req burn-in, 确认 R1809 治本成立 + 定位新失败模式 = 本轮成果, 不叠加新改动污染观测。

## 下一轮该做什么 (R1813)
1. **继续攒 pexec burn-in 数据**（目标 ≥1h/≥100req 干净 pexec 窗）, 确认:
   - bug2/malformed 持续归零（已 23min 0 条, 拉到 1h 0 条则 R1809 正式宣告全胜）
   - pexec 僵尸流(capped content_chars=0)频率是否稳定（当前 2/54≈3.7%）还是间歇上游抖动
2. **决策分支**:
   - 若 zombie cap 频率 >5% 持续 → 查源码 `handlers.py` cap break 后是否硬中止 tier abort chain（NV-ANTH-ABS-CAP 触发后, tier 内仍在跑 240s, 应硬中止）— 潜在 bug4治本点, 需 dump wire 一次确认 cap break 路径
   - 若 fallback 率仍高(bug3) → 等 bug1/僵尸流看完, 慢流治了 ttfb 降, 抢断自然减少
3. **若数据证明全胜(SR>95% + zombie<2% + fallback<5)**: 转纯巡检或下一个优化点（dsv4p_nv tier 间歇 empty_200? 见 16:02 fa202f2c）。
4. 不再调 cap/SSLEOF_RETRY/TIER_BUDGET 边际参数（监督者已证非主犯）。
5. 小步改（若数据支撑）: cp .bak.R1813, 改一处, restart/up -d nv_gw, 验证 /health+docker ps+下窗口日志。

## 铁律
只改 HM2，不改 HM1，不碰 proxy/ms-gw。改前必有数据，改后必有验证。改 .py 必须 restart（非 up -d）, 改 compose env 必须 up -d（非 restart）。
