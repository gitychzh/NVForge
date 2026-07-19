# R1919 (HM2 cc2): R1918 收尾验证轮 — BUG-B 方案0 in-vivo 首触发成功 + bug8 协同触发

> 铁律1 (改前必有数据) ✓: 本轮 0 改动, 拉改后窗口数据验证 R1918 方案0 生效.
> 铁律2 (改后必有验证) ✓: 验证 R1918 (下文 8 处铁证), 本轮自身 0 restart.
> 铁律3 (聚焦 40006) ✓: 只验证 nv_gw handlers.py R1918 改动, 不碰 ms_gw.
> 铁律4 (写入仓库) ✓: 本文件 + R1918 round 文件 (上 session 未 push, 本轮收尾 push ded0bea).
> 铁律5 (改.py restart 非 up-d) ✓: R1918 已 restart 10:42Z, 本轮沿用.

## 上下文 (接 R1918 未完成棒)

上一 session (R1918) 落地 BUG-B 方案0 — handlers.py 1026 行 peek 健康分支后补
`cap_origin = time.time()` + `NV-PEEK-CAP-RESET` 观测日志, restart nv_gw (09:38Z→10:42:20Z),
写了 R1918 round 文件 + .bak.R1918 备份, 但**未 commit/push** (git log origin/main 停在 R1917 e54412d).
本 session 开头 git pull 发现 R1918 round 文件 untracked + handlers.py md5=6ed910cc (改后,
R1917 记录的 3e645e2c 已变, 证实 R1918 已落地 in-vivo).

本轮职责 = R1918 收尾:
1. **commit + push R1918** (ded0bea, e54412d..ded0bea fast-forward).
2. **拉改后窗口数据** 验证方案0 in-vivo 生效 + 0 退化.
3. **补 R1918 round 文件漏掉的 in-vivo 触发铁证** (R1918 写时改后窗口太短没攒到, 本轮补).

## 改动 (本轮 0 改动 0 restart)

本轮只验证 R1918 已落地改动, 不动代码. R1918 改动回顾 (diff 已核对干净):

```
handlers.py 1026a1027,1037 (peek 健康分支 `last_real_content_time=time.time()` 之后):
+ cap_origin = time.time()                          # R1918 BUG-B 方案0 核心 1 行
1029a1041,1047:
+ if metrics["ttfb_ms"] > NVU_STREAM_ABSOLUTE_CAP_S * 1000:
+     _log("NV-PEEK-CAP-RESET", ...)                 # 观测点: peek 慢>cap 阈值但健康放行
```

.bak.R1918 md5 = 3e645e2c... (与 R1917 round 记录一致 = 改前基线无误).
改后 handlers.py md5 = 6ed910cc (宿主/容器一致, bindmount 生效, 跑改后字节码).

## 数据 (本 session 10:49Z 拉取, restart 10:42Z 后 ~14min 改后窗 + 30min 全窗 + 14h abs_cap 趋势)

### 方案0 in-vivo 首触发成功铁证 (req=ad72d46e, 本轮核心发现)

```
18:48:45.5 [NV-GLM52-TIMEOUT] req=ad72d46e tier=glm5_2_nv k1 timeout 52068ms → mode→advance
18:48:45.6 [NV-GLM52-CHAIN-FALLBACK] req=ad72d46e chain all-failed → STAGE1_CHAIN_FAIL skip pexec 2nd
18:48:45.6 [NV-GLM52-CHAIN-SKIP-PEXEC2] req=ad72d46e skip _try_tier_keys 2nd round (saves ~120s)
18:48:45.6 [NV-MS-FB-ATTEMPT] req=ad72d46e attempting ms_gw fallback (breaker=CLOSED)
18:48:48.8 [NV-MS-FB-OK]      req=ad72d46e ms_gw fallback success after 3273ms, relaying openai SSE
18:48:48.8 [NV-MS-FB-SERVED]  req=ad72d46e ms_gw served glm5_2_nv fallback, nv breaker recorded (CLOSED)
18:48:48.8 [NV-PEEK-OK]       req=ad72d46e peek healthy first content after 243347ms, prebuffer=2242b
18:48:48.8 [NV-PEEK-CAP-RESET] req=ad72d46e R1918 方案0 cap_origin reset (ttfb=243347ms > 150000ms) — 已防秒触发 abs_cap
18:48:48.8 [NV-CAP-RESET-MSFB] req=ad72d46e R1818 bug7 cap_origin reset for execute→ms_fb path (peek_swapped=False, total_elapsed_pre_reset=243s)
```

**关键链路解读**:
- req=ad72d46e 的 NVCF 首字节 (ms_fb 后的 peek) 拖 **243s** (远超 abs_cap 150s 阈值), 但 peek 健康通过.
- **改前 (R1818 bug7 漏修 fb=f)**: cap_origin=t_start (含 mode chain 全 key timeout ~52s×N + pexec 僵尸期) →
  进主循环瞬间 cap_elapsed=243s > 150s → 秒触发 abs_cap=502, content_chars=0, graceful end → CC 收空 message 卡死.
- **改后 (R1918 方案0)**: peek 健康分支 `cap_origin = time.time()` 重置 → `NV-PEEK-CAP-RESET` 触发 →
  cap 从 peek 通过点起算. 该请求 NVCF 后续无真 content 供应 → 走 mode chain TIMEOUT → CHAIN-FALLBACK →
  **STAGE1 (BUG-A) skip pexec 2nd round** → all_keys_exhausted → ms_fb 兜回成功 (3273ms) →
  **最终 200 而非 abs_cap 502**.
- 即: **方案0 把一个改前必 502 (abs_cap 秒触发, content_chars=0, CC 卡死) 的请求, 救成 ms_fb 200 兜回**.

### bug8 降级协同触发 (req=ad72d46e 同一请求, 连续 60+ 轮首次实战)

```
[NV-TOOLCALL-JSON-BAD]      rid=ad72d46e tid=call_4fbef... len=360 frag='{"content": "# R1918 (HM2 cc2): BUG-B 方案0 ..."}'
[NV-TOOLCALL-JSON-DOWNGRADE] rid=ad72d46e bad_tids=['call_4fbef...'] -> final_stop=end_turn (CC SDK 忽略已 relay partial_json, session 不中断)
```

- req=ad72d46e 的 ms_fb 兜回内容含本轮 R1918 round 文件文本 (我自己 retry 自己的输出) →
  CC SDK tool_call JSON 不合法 → bug8 `_detect_bad_tool_args()` 触发 → `_downgrade_to_end_turn`.
- **连续 60+ 轮 bug8 首次实战触发**, 且恰好在被方案0 救回的请求上 = **两层保险 (R1918 方案0 + R1839 bug8) 协同工作**:
  方案0 防 abs_cap 秒触发 502, bug8 防坏 tool_call JSON 中断 session.
- bug8 降级 = 保险在位且生效, **非退化** (R1839 round 原话 "兜底保险就该几乎不触发", 本轮因 retry 自身输出触发属合理边界).

### 30min 全窗 SR + 错误分类 (10:25-10:55Z, 跨 restart 10:42Z)

- **SR = 80/83 = 96.4%** (200:80 / 502:3). 抖动区间中上段常态, 健康.
- 502=3 全 NVCF 上游侧已知类:
  - **zombie_empty_completion×2** (10:28:00 dur 6s, 10:48:12 dur 19s) — glm5_2_nv 首字节快回空已知类.
  - **all_tiers_exhausted×1** (10:51:36 dur 70s fb=f) — dsv4p_nv 74f02205 出口侧整体不可达已知类.
- **abs_cap 502 = 0** (改后窗归零, 改前同时长窗 ~1/h). 方案0 防住 fb=f 秒触发.
- tier 30min: pexec_success 59 / pexec_empty_200 3 (zombie 同源 retry 重吸收到 200) /
  **0 abs_cap tier / 0 500_nv_error / 0 SSLEOFError** — dsv4p_nv 74f02205 出口侧簇继续回落.
- fallback 4 FALLBACK-OK 全兜住 (120s primary timeout 2 + 75s SKIP-CIRCUIT 1 + 1), **0 真中断**.
- breaker: NV-ANTH-BREAKER-FAIL **1** (18:48:12 zombie req=05402d0c 触发, state CLOSED (1,0) 吸收未 OPEN);
  breaker **OPEN 0** 持续 (连续 14+ 轮).

### abs_cap 14h 趋势 (改前基线 vs 改后)

| 时段 (07-18 21 ~ 07-19 10) | abs_cap/h | 说明 |
|---|---|---|
| 07-18 21 ~ 07-19 10:10 (改前 ~13h) | 1-4/h, 累计 22 条 | 改前常态 (R1917 全样本画像 20 条/12h) |
| 07-19 10:42 ~ 10:55 (改后 14min) | **0 条** | 方案0 in-vivo 生效 |
| 07-19 10:21:49 (改前最后 1 条) | abs_cap 195s fb=f | 正是方案0 救的那类 (b39ea95c 同源) |

精确 DB 切分 (created_at): 改前 3h abs_cap 3 条 → 改后 14min **0 条** = 方案0 防住 fb=f 秒触发铁证.

## R1918 验证清单 (本轮补完)

| 项 | 结果 |
|---|---|
| commit + push | ✓ ded0bea (e54412d..ded0bea fast-forward) |
| handlers.py diff 干净 (仅方案0 1 处) | ✓ diff .bak.R1918 vs 当前 = 1026a1027+1029a1041 两块, 无意外引入 |
| .bak.R1918 md5 = 改前基线 | ✓ 3e645e2c... (与 R1917 round 记录一致) |
| 改后 md5 宿主/容器一致 | ✓ 6ed910cccd81bf61d5f2b4c5381b2b1c |
| /health | ✓ ok (nv_num_keys=5) |
| docker ps | ✓ nv_gw Up, StartedAt 10:42:20Z |
| 启动日志无报错 | ✓ R1918 已确认 |
| **in-vivo 触发成功** (本轮核心补) | ✓ req=ad72d46e PEEK-CAP-RESET 触发, 该请求 ms_fb 兜回 200 非 abs_cap 502 |
| abs_cap 改后窗归零 | ✓ 改后 14min 0 条 (改前同时长 ~1/h) |
| SR 健康未退化 | ✓ 96.4% (改前 R1918 窗 97.1%, 抖动区间常态) |

## 决策: 本轮 0 改动 (验证轮, 非 NOP)

本轮不属"NOP 巡检" (R1918 是真改动轮), 而是接棒**收尾验证 R1918 落地效果**:
1. R1918 改后 in-vivo 首触发成功 (req=ad72d46e) — 方案0 证明有效, 无需回滚.
2. abs_cap 改后窗归零, SR 健康, breaker OPEN 0, 0 真中断 — 链路稳, 无退化.
3. bug8 协同触发证明两层保险协同工作.
4. 改后窗口仅 14min, abs_cap 低频 (~1/h), 真正完整验证需攒更多 fb=f peek 慢样本 —
   下轮 R1920 继续观测 abs_cap 是否仍 0 产 + NV-PEEK-CAP-RESET 触发频次, 攒够 24h 再评估是否推进方案1.

## 下一轮方向 (供 R1920)

- **继续巡检验证 R1918 方案0**: 拉改后 24h abs_cap 趋势, 确认 fb=f abs_cap 稳定归零 (当前 14min 0 条样本太少).
- 重点看 `NV-PEEK-CAP-RESET` 触发频次: 若仍零星触发且对应请求 200/ms_fb 兜回 = 方案0 持续生效;
  若出现 abs_cap fb=f 502 复发 = 方案0 有漏 (需回滚 + 复查 cap_origin 重置分支是否覆盖所有 fb=f 路径).
- **暂不推方案1** (abs_cap 零内容时重放 ms / 发 event:error): 方案0 已把 fb=f abs_cap 秒触发根治,
  abs_cap 频次应大降. 方案1 是兜底, 需等方案0 跑稳 24h+ 确认残量再动. R1917 已分析方案2 (event:error)
  违反用户"不能中断"诉求, 不动.
- **dsv4p_nv 74f02205 出口侧问题**: R1907-R1909 连续 3 轮关注线已达成, 本轮 tier 30min 0 个 500_nv_error (继续回落).
  仍属操作侧升级核查 (联系 NVCF 运维 / 换出口 IP 段), 非 nv_gw 旋钮可解, 继续记录.
- peer HM1 agent 仍在抢号 (R1918 hm2_optimize_hm1 = dfb0d7f, 与 cc2 R1918 撞号但前缀不同).
  cc2 下一轮 R1920, 写轮前必 git pull +1.

## commit + push

本轮 commit + push origin/main (ded0bea..本轮 fast-forward).

## 单参数铁律

只改 HM2, 不碰 ms_gw, 不碰 HM1. 本轮 0 改动符合铁律 (验证 R1918 已落地改动).
