# R2134 (hm2_oc2) — NOP 巡检轮 82 + 499 持续基线复核

## 基线
- 上一轮 hm2_oc2: R2133 (commit a8b102f, NOP 巡检轮 81, glm5_2_nv 6h 96.79%, 连续 77 NOP)
- 本轮: **R2134 — hm2_oc2 NOP 巡检轮 82, 0 改动 0 restart**
- HM1 peer 轨 (R2275-R2278) 多轮连调非本域, HM2 不参与 (铁律只改 HM2).
- STATE.md 接棒时停在 R2196 (旧/并行编号体系, 与主仓 hm2_oc2 轨 R2133 对不上),
  以 `git log` 主仓 hm2_oc2 轨为准重建基线续 R2134.

## 数据 (HM2, 30min window, ~05:42 时点)
- 总 83 请求 / 77 OK(200) / 6 错(502) → SR = **92.8%**
  (较 R2133 30min glm5_2_nv 71/71 全 200 略有回落, 主因 dsv4p_nv ATE 占)
- by model: **glm5_2_nv 69/70 = 98.6% SR** (主链路稳态延续, 1 错 stream_no_content_gap); dsv4p_nv 8/13 = 61.5% (5 错全 all_tiers_exhausted)
- 6 错 error_type: dsv4p_nv 5× all_tiers_exhausted (NVCF 上游 dsv4p function ATE 已知良性, 与历史同族无新增) + glm5_2_nv 1× stream_no_content_gap (中游流背景波, 首字节已收未触发 fallback)
- **0 zombie / 0 content_filter / 0 timeout / 0 conn / 0 429 / 0 ATE on glm5_2_nv**
- host_machine 全 HM2 本域

## cc4101 30min fallback (负向核心指标)
- **1 个请求, 全 FALLBACK-OK 救回, 0 双失败**
  - req=ad4661ac [05:40:43] PRIMARY-FAIL (cc4101 自身 60s header/ttfb timeout after 60069ms,
    `PRIMARY-FAIL-SKIP-CIRCUIT` 明示 "primary timeout 60069ms < chain budget 120s, likely
    cc4101 pre-empted nv_gw retry, NOT counted toward circuit") → [05:41:03] FALLBACK-OK (ms_gw glm5_2_ms 救回 20277ms)
- grep -cE 计数 4 是同一事件多行匹配 (PRIMARY-FAIL×2 + SKIP-CIRCUIT + FALLBACK-OK), 实际就 **1 个 fallback 请求**
- 真新发 (req=ad4661ac 新 id 新时点 05:40:43) 但全救回 0 真中断
- fallback 请求数 1 < 5 阈值 ✅

## ⚠ 499 (client_gone_mid_stream) 持续基线复核 — BUG-A 未解确认
- **cc_requests 6h: 50 个 client_gone_mid_stream** (CLAUDE.md R2191 段盲点指标, 预期 R2191 后归零或 <5/6h, 实测远超)
- 小时分布: 16:00(4)/17(3)/18(3)/19(3)/20(4)/21(4)/22(4)/23(5)/00(5)/01(3)/02(4)/03(3)/04(2) —
  **每小时持续 2-5 个, 不是单点突发, 是持续基线**
- duration: avg **131660ms ≈ 131s**, max 238945ms
- **铁证吻合 BUG-A**: cc2 SDK 客户端 ~131s 首字节墙 — NVCF TTFB>131s 时 cc2 客户端自断 (broken pipe),
  cc4101 记 client_gone. avg 恰好卡 131s = 客户端硬超时, **不是 nv_gw 旋钮能治** (nv_gw UPSTREAM_TIMEOUT=90,
  cc4101 primary header 60s 都远低于 131s, 但 client_gone 是客户端侧独立计时, fallback 来不及救)
- R2228 注入清单 BUG-A 已明确: "如 SDK 客户端首字节墙不可调, 接受 499 是 SDK 限制".
- **本轮结论**: 499 持续基线确认是 SDK 结构性限制, 非 nv_gw 参数问题, 本轮不动 nv_gw (动也治不了客户端墙).
  下轮评估是否查 claude CLI `API_FORCE_IDLE_TIMEOUT` 或类似客户端超时旋钮 (CLAUDE.md BUG-A 待查项).

## R2192 三任务进度 (CLAUDE.md 持久任务, 撤 40007 前置)
- 任务1 (cc4101 透传 cache_control): **已落地** (R2228 cache_read 0%→38.8%, 走 nv_gw 读 NVCF
  prompt_tokens_details.cached_tokens 路径). ✅ 本轮无需再动, 持续验证命中率不退.
- 任务2 (nv_gw 侧抓 zombie body dump probe): **未做**. 本轮窗口 0 zombie, 无素材可加 probe.
  handlers.py L779 有 oai_body 但无 dump 到文件. 待 zombie 窗口出现时加 probe 落盘对比字段.
- 任务3 (路径B zombie 内部重试): **部分**. _ms_fallback_request 存在但 "200+message_start 已发→
  不能切 ms 重放" 约束未解 (双 message_start 错乱). 需设计 converter feed_chunk 内部重试.
  本轮 0 zombie 无触发条件, 暂不动.

## nv_gw 内部 NV-MS-FB / breaker
- fallback_occurred=true (nv_gw 内部 tier 兜底) 与 NV-ANTH-BREAKER-FAIL 本轮未单独抓 (30min 窗口
  glm5_2_nv 仅 1 错 stream_no_content_gap 非 breaker 触发条件, 主链路稳态延续 R2133).
- breaker 不真 OPEN (主链路连续多轮稳态, 无 mid-stream 软挂累积).

## 容器状态 (漂移信号核)
- nv_gw /health ok (nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], passthrough role, default=glm5_2_nv)
- docker ps: nv_gw Up 7 hours / cc4101 Up 7 hours / ms_gw Up 33 hours (全栈 Up)
- env 关键参数与 R2133 逐项一致 (UPSTREAM_TIMEOUT=90/TIER_TIMEOUT_BUDGET_S=180/
  KEY_COOLDOWN_S=60/TIER_COOLDOWN_S=180/NVU_TIER_BUDGET_GLM5_2_NV=120/NVU_TIER_BUDGET_DSV4P_NV=180/
  MIN_OUTBOUND_INTERVAL_S=10), **无参数漂移**

## 决策: NOP 巡检, 不改代码
STATE 三触发改动阈值全不满足:
- SR 92.8% (glm5_2_nv 主链路 98.6%) > 85% ✅
- cc4101 fallback 请求数 1 < 5 ✅ (全救回 0 真中断)
- 无新增错误类型 ✅ (6 错全上游类: 5 dsv4p ATE + 1 glm5_2_nv stream_no_content_gap 中游流背景波, 与历史同族)
四重佐证 nv_gw 稳: 主链路 98.6% 持续稳态 / 0 zombie 0 ATE on glm5_2_nv / breaker 不真 OPEN / 参数无漂移容器未重建.
499=50/6h 是 SDK 客户端墙结构性限制 (avg 131s 铁证), 非 nv_gw 旋钮能治, 动 nv_gw 治不了它 —
属 CLAUDE.md BUG-A 待查项 (查 claude CLI 客户端超时旋钮), 不是本轮 nv_gw 改动范围.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + env 无漂移 (与 R2133 逐项一致).
连续 78 NOP.

## 下一轮该做什么
1. 继续巡检. 盯 glm5_2_nv 主链路 SR 持续 ≥95% (本轮 98.6%).
2. **cc4101 fallback 趋势**: 本轮 1 全救回 (cc4101 自身 60s header timeout pre-empt, 不归因 nv_gw).
   连续多轮全救回 0 双失败. STATE 建议 ~R2200+ 做下次 6h 复核 (R2182/R2178 做过 6h 复核 98.2% 无慢退化).
3. **499 BUG-A 待查项 (优先级升)**: 499=50/6h 持续基线 (avg 131s) 确认是 SDK 客户端墙.
   下轮评估查 claude CLI 客户端首字节超时是否可调 (API_FORCE_IDLE_TIMEOUT? 或 SDK 硬编码).
   如可调→调它降 499; 如不可调→接受是 SDK 限制, 转 nv_gw 端容忍 (但 client_gone 不在 zombie 路径, 需另设计).
   **注意**: 不要改 settings.json (项目级已 R2191 改 900000/1000000, 全局禁碰). 查的是 CLI 客户端超时旋钮.
4. **R2192 任务2/3 推进**: 待 zombie 窗口出现时 (本轮 0 zombie 无素材). 任务2 加 zombie body dump probe 是
   任务3 前置. 下轮若 6h 出现 zombie (R2133 6h 14z) 可加 probe 落盘对比字段.
5. 触发改动的三阈值 (全满足才动, 否则冻结): 30min SR 跌破 85% **或** cc4101 fallback 请求数 >5 条/30min
   **且** 出现新错误类型 (zombie 比例上升 / NV-ANTH-BREAKER-FAIL 真 OPEN).
6. HM1 peer 轨 (R2275-R2278) 多轮连调非本域, HM2 不参与 (铁律只改 HM2 不改 HM1).
7. 下一 session 接棒: STATE 体系 (R21XX 系列) 与主仓 hm2_oc2 轨 (R2133) 编号不同, 以 git log
   `git log --oneline | grep hm2_oc2 | head` 为准重建基线. 绝不 Read /tmp.
8. 数据库列名: nv_requests 列是 `request_model` (不是 model), `status` 是 integer (200/502).
   cc_requests 列是 `ts` (不是 created_at), `error_type` 取 client_gone_mid_stream 等.

## nv_gw 参数快照 (HM2, 本轮确认无漂移)
```
MIN_OUTBOUND_INTERVAL_S=10
KEY_COOLDOWN_S=60
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
TIER_COOLDOWN_S=180
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_THRESHOLD=250000
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_MODELS=glm5_2_nv
KEY_AUTHFAIL_COOLDOWN_S=60
NV_INTEGRATE_KEY_COOLDOWN_S=90
```
容器: nv_gw Up 7 hours (RC=0 env 无漂移) / cc4101 Up 7 hours / ms_gw Up 33 hours. HM2 only.
