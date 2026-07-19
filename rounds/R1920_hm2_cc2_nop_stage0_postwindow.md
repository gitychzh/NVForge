# R1920 (HM2 cc2): NOP 巡检 R62 — BUG-B 方案0 落地后窗口纯净, abs_cap 502 归零

> 铁律1 (改前必有数据) ✓: 本轮 0 改动, 拉 R1918 方案0 restart 10:42Z 后 ~23min 窗口 + 4h abs_cap 趋势.
> 铁律2 (改后必有验证) ✓: 本轮自身 0 restart, 验证 R1918 方案0 持续生效 (无退化).
> 铁律3 (聚焦 40006) ✓: 只观测 nv_gw, 不碰 ms_gw.
> 铁律4 (写入仓库) ✓: 本文件.
> 铁律5 (改.py restart 非 up-d) ✓: 本轮 0 改动 0 restart, 沿用 R1918 restart (StartedAt 10:42:20Z).

## 上下文 (接 R1919)

R1919 (上一轮, commit 2174ef9) 是 R1918 收尾验证轮: 首次确认 BUG-B 方案0
(peek 健康分支补 `cap_origin = time.time()`, 补 R1818 bug7 漏修 fb=f 路径) in-vivo
首触发成功铁证 — req=ad72d46e ttfb=243s, `NV-PEEK-CAP-RESET` 触发, 防秒触发 abs_cap,
最终走 ms_fb 兜回 200 (而非改前的 abs_cap 502 + content_chars=0 + CC 卡死).

本轮职责 = R1919 之后续观测: 方案0 落地后窗口是否纯净, abs_cap 502 是否真降, 是否该推进
监督者 19:25/19:50 提的 BUG-B 阶段2 (方案1: abs_cap 后重放 ms) 或 方案2 (peek 判定收紧).

## 改动 (本轮 0 改动 0 restart)

NOP 巡检 R62. 不动代码不动 env. R1918 方案0 改动 (handlers.py peek 健康分支补 cap_origin 重置)
仍在位, StartedAt 10:42:20Z (R1918 restart) 未变, 跑改后字节码.

## 数据 (本 session 11:05Z 拉取, restart 10:42Z 后 ~23min + 4h abs_cap 趋势)

### 30min nv_gw 窗口 (10:35-11:05Z)
- **SR = 72/76 = 94.7%** (200:72 / 502:4). 抖动区间上沿常态, 健康 (R1909=91.9%→R1919 验证→R1920=94.7%).
- 502=4 全 NVCF 上游侧, 0 条 abs_cap:
  1. `05402d0c` zombie_empty_completion — glm5_2_nv egress 134.195.101.180 function 3b9748d8, dur 19.6s (NVCF 首字节快回空, 已知类).
  2. `f72cb005` all_tiers_exhausted — dsv4p_nv function 74f02205, dur 70s, egress 空 (出口侧整体不可达, 已知类, R1907-R1909 连续抬头同 function).
  3. `4894f12d` zombie_empty_completion — glm5_2_nv egress 134.195.101.193 function 3b9748d8, dur 9.9s.
  4. `6f4cd414` zombie_empty_completion — glm5_2_nv egress 134.195.101.193 function 3b9748d8, dur 4.2s.
- tier 30min: pexec_success 46 / pexec_empty_200 2 (zombie 同源, 被 retry 重吸收到 200) / pexec_SSLEOFError 1.

### BUG-B 方案0 in-vivo 持续生效 (核心, R1920 续观测)

30min 窗内 `NV-PEEK-CAP-RESET` 触发 **3 次** + `NV-CAP-RESET-MSFB` 7 次:
- req=ad72d46e ttfb=243347ms → `NV-PEEK-CAP-RESET` (方案0) → `NV-CAP-RESET-MSFB` (bug7) → 最终 ms_fb 兜回 200.
- req=6713bfb6 ttfb=242706ms → 同链路 → 200.
- req=383c3ecb ttfb=254241ms → 同链路 → 200.

**关键**: 这 3 条请求 NVCF 首字节拖 243-254s (远超 abs_cap 150s 阈值).
- 改前 (R1818 bug7 漏修 fb=f 路径): cap_origin=t_start → 进主循环瞬间 cap_elapsed>150s → 秒触发 abs_cap=502, content_chars=0, CC 收空 message 卡死.
- 改后 (R1918 方案0): peek 健康分支 cap_origin 重置 → cap 从 peek 通过点起算 → 不再秒触发 abs_cap → 走 mode chain TIMEOUT → CHAIN-FALLBACK → STAGE1 (BUG-A) skip pexec 2nd → all_keys_exhausted → ms_fb 兜回 200.

**3 个本该 abs_cap 502 的请求被救成 200** = 方案0 in-vivo 持续生效, 且本轮比 R1919 首触发多了 2 个新样本 (6713bfb6/383c3ecb), 持续非偶发.

### 4h abs_cap 趋势 (restart 10:42Z 前后对比)

restart 前 (05:00-10:21Z, ~5h): abs_cap 502 共 **4 条** (057cbe88 07:50 / a56a3a69 08:02 / 93e454cd 09:55 / b39ea95c 10:21), 全 nvcf_pexec fb=f, egress 134.195.101.193 或空, function 3b9748d8, ttfb 152-196s (cap_elapsed==total_elapsed 秒触发铁证).
restart 后 (10:42-11:05Z, ~23min): abs_cap 502 **0 条**.

→ 方案0 落地后 abs_cap 502 归零 (短窗 23min, 样本偏少待续攒, 但与 R1919 验证一致: 方案0 修对了 fb=f 路径 cap_origin 重置, 秒触发根因消除).

### fallback + breaker

- fallback 4 FALLBACK-OK 全被 ms_gw 兜住, **0 真中断**. 其中 3 条 120s PRIMARY-FAIL (18:46/18:58/19:01 时间戳系 R1919 窗口日志, 本轮 30min 窗内 nv_gw 侧 fallback 走 ms_fb 路径, 全 200 兜回).
- breaker NV-ANTH-BREAKER-FAIL 1 次 (req=05402d0c zombie 触发, state CLOSED (1,0) 吸收未 OPEN); breaker **OPEN 0 连续 14+ 轮**.
- bug8 DOWNGRADE 触发 2 次 (ad72d46e/383c3ecb, NVCF 流里夹带 R1918/R1919 round 文本 chunk 的 tool_call, bug8 降级兜底正确捕获, session 不中断 — 这是 cc2 自身写文档内容被 NVCF 反射回来的偶发现象, 非链路问题).
- NV-CAP-RESET-MSFB 7 次 (bug7 已修路径, 与方案0 协同正常).

## 决策 (为何 NOP 不改)

依据铁律1 (无据不改) + 监督者 19:50 优先级建议:

1. **方案0 (已落地) in-vivo 持续生效, abs_cap 502 短窗归零** — 监督者 19:50 提的"最该先动"已做且验证, 不动.
2. **方案1 (abs_cap 后重放 ms, 中风险)** — 监督者原话"方案0 后观测, 若 abs_cap 仍产则加". 本轮 restart 后 abs_cap 502=0 (23min), **未量产, 无据动方案1**. 且方案1 涉及 message_start 重复风险 (需 cc4101 端容错), 高风险, 当前低频不值得动.
3. **方案2 (peek 判定收紧, 中风险)** — 监督者原话"观测 NVCF tool_calls 时序后定". 本轮无新 tool_calls 时序数据, 不动.
4. 30min 502=4 全 NVCF 上游侧 (zombie 首字节快回空 / ATE 出口侧不可达), 非新可配置类, 非链路层可解 (NVCF 上游侧 + 出口 IP 段 134.195.101.0/24 + dsv4p_nv function 74f02205 出口路由).
5. breaker OPEN 0 连续 14+ 轮, 本轮 BREAKER-FAIL 1 被 CLOSED 吸收未 OPEN, 链路稳.
6. SR 94.7% 在抖动区间上沿, 非退化, 未达"连续 3+ 轮跌破 80%"介入线.

**结论**: 介入条件全不满足 → NOP 巡检, 无据不改. 继续攒方案0 落地后长窗口数据 (尤其 abs_cap 量产是否真的归零), 等监督者/NVCF 侧对 dsv4p_nv function 74f02205 出口路由的核查.

## 下一步

- **继续 NOP 巡检 R63**. 下一轮拉 30min 看 SR/fallback/breaker/abs_cap 抖动是否仍在已知区间.
- **重点续攒**: 方案0 落地后 abs_cap 502 是否持续归零 (本轮 23min 0 条, 样本偏少). 若连续 3+ 轮 (R1920-R1922) abs_cap 502 均为 0, 可正式判定方案0 根除 fb=f 秒触发路径, 届时方案1 (abs_cap 后重放 ms) 失去数据支撑, 不再需要动.
- **dsv4p_nv function 74f02205 出口侧问题**: 本轮续抬头 (1 ATE 70s egress 空). R1907 首抬头→R1908 第 2→R1909 第 3→R1917-R1919 续→R1920 第 N 轮 (已超 3 轮关注线, 持续记录). 这是 NVCF 上游侧出口路由问题, 非链路层可解, 等监督者/NVCF 运维介入.
- 若 abs_cap 真量产 (连续 2+ 轮 30min 窗内 abs_cap 502 ≥ 3), 再启动方案1 (abs_cap 后重放 ms) 阶段2, 但需先攒 message_start_sent 分布数据定安全阈值.
- 沿用 R1919 给监督者方向: zombie/empty200/ATE/500_nv_error/abs_cap 同源首字节慢/空/出口侧不可达是 NVCF 上游侧 + 出口 IP 段 (134.195.101.0/24 zombie 单点续 + dsv4p_nv 74f02205 出口 egress 空), 需换出口 IP 段 / 联系 NVCF 运维 / 核查 dsv4p_nv function 74f02205 出口路由, 非 nv_gw 单参数可解.
- peer HM1 agent 持续在 HM1 侧收紧 (R1918 NVU_TIER_BUDGET_DSV4P_NV 39→30, R1917 TIER_TIMEOUT_BUDGET_S 155→153), 写轮前必 git pull 看最新号 +1 防 peer 抢号.

## 当前 nv_gw 参数快照 (R1920 拉取, 无漂移)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=180
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90
TIER_COOLDOWN_S=25
```
nv_gw StartedAt = 2026-07-19T10:42:20Z (R1918 restart 落地方案0, R1919-R1920 未再 restart).
/health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
handlers.py md5 = 6ed910cc (R1918 改后, 宿主/容器一致, bindmount 生效).
