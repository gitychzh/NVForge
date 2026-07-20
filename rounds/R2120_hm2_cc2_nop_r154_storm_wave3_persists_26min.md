# R2120 (hm2_cc2) — NOP R154 连续第90轮冻结: 第3波429风暴延续26min+未自愈(异常)

## 数据 (本 session 拉取, CST 05:05 = UTC 21:05, 30min 窗口起点 20:35 UTC)

**状态分布 (nv_requests 30min)**:
- 200: 86 / 502: 42 / 429: 3 → SR = 86/131 = **65.6%** (vs R2119 拉时 86.7% -21.1pp; vs R2118 91.9% -26.3pp)
- **30min SR 跌幅显著加大**: 本轮窗口完全包含 R2119 记录的 20:40-20:50 第3波风暴 + 其延续段 20:50-21:08

**小窗 SR (风暴延续回落中)**:
- last3 = 12/15 = 80.0% (风暴回落期, vs R2119 last3 45.0% +35pp 回升)
- last10 = 16/33 = 48.5%
- last15 = 27/57 = 47.4%
- last30 = 86/131 = 65.6%

**5min 桶完整轨迹 (UTC)**:
- 20:31-20:39 稳态期 (每桶 200:3-7 / 502:0-1, R2118 自愈期延续)
- 20:40 502×1 首现 → 20:41 502×1 → 20:46 502×1 (零星)
- **20:49 502×5 + 429×1 爆发上浮** (R2119 记录的 20:45 段延续)
- **20:50 502×3 → 20:51 502×2 → 20:52 502×1 → 20:53 502×1**
- **20:54 502×5 + 429×1 二次峰值** (SR≈3/9=33%)
- 20:55 502×2 → 20:56 200:4/502:2 → 20:57 502×2 → 20:58 200:1/429:1/502×4 (三次小峰)
- 20:59 502×2 → 21:00 200:1/502×3 → 21:01 200:1/502×1 → 21:02 502×1 → 21:04 200:5/502×1 → 21:05 200:2/502×2 → 21:06 200:1
- **风暴从 20:49 持续到 21:06 = 26+ 分钟仍未完全平息**, 远超之前 R2111(~15min)/R2116(~15min)/R2119(~10min上升期) 各波的自愈周期

**502 分类 (30min)**:
- all_tiers_exhausted×36 + zombie_empty_completion×5 → 全 **NVCF 上游已知类, 0 新可配置类** ✅
- 429×3 全 all_tiers_exhausted

**tier 30min 错误分类**:
- **429_nv_rate_limit×23** (vs R2119 拉时 30min 429=10, **10→23 翻倍加剧**, 风暴延续期 tier retry 持续吸收但上游 429 不停)
- pexec_success×34 (正常 tier 吸收)
- NVCFPexecRemoteDisconnected×6
- pexec_SSLEOFError×1 (本轮出现 1 个 SSL, vs R2119 0; 非 SSL 主导, 仍纯 429 风暴)
- pexec_empty_200×1 + empty_200×1 + pexec_conn_RemoteDisconnected×1

## fallback (cc4101 30min)
- **8 FALLBACK-OK, 0 真中断, 0 fallback 失败** ✅
- 全 8 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb timeout 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类)
- **0 条 120s 跑满类** (持平 R2119)
- req 样本: 59e3ae9a / 1b9a4b30 / 7421de45 / 77de8f3f ... 全被 ms_gw 兜住
- cc4101 `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认

## ⚠️ 新现象: 6 条 cap_origin reset (execute→ms_fb path, chain_budget 耗尽)
- `grep -cE "abs_cap|cap_origin"` 30min = 6 (STATE 多轮记 "abs_cap 30min=0", 本轮需澄清)
- **6 条全 `NV-CAP-RESET-MSFB` (R1818 bug7 cap_origin reset for execute→ms_fb path)**:
  - 04:41:29 req=192aaedd total_elapsed_pre_reset=122s
  - 04:43:34 req=edef5b62 121s
  - 04:47:03 req=20a5e6cf 128s
  - 04:56:27 req=42b8056f 125s
  - 04:59:14 req=5ddf122b 130s
  - 05:03:06 req=fac055ef 125s
- **含义**: 这 6 条请求在 nv_gw 内 tier retry 累积到 chain_budget (120s) 耗尽才走 ms_fb 兜底并 reset cap_origin. 总耗时 121-130s (略超 120s budget 因 reset 时点). **首次出现 chain_budget 耗尽类** (vs R2111/R2116/R2119 均 "0 条 120s 跑满类").
- **但全被 ms_fb 兜住, 0 真中断** — 这是风暴持续时间长导致部分请求累积 retry 撑满 budget 的体现, 兜底机制正常生效.

## breaker / BUG-A / health / StartedAt / env
- breaker cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw `grep -cE "NV-ANTH-BREAKER-FAIL|breaker.*OPEN|state.*OPEN"` = **0**
- nv_gw 30min `grep BREAKER` 日志: 12 条 `NV-BIGINPUT-SUCCESS ... breaker→CLOSED` (big_input 成功后 CLOSED, 非真 OPEN)
- **state CLOSED 未达 OPEN 阈值 = 连续第 23 轮验证未恶化** ✅
- BUG-A 修复 (R1913) 生效: `NV-GLM52-CHAIN-SKIP-PEXEC2` 30min 触发 **6 次** (vs R2119 5 次 +1, 持续复活) ✅
- nv_gw /health = ok (proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=dsv4p_nv, port=40006)
- **docker inspect StartedAt**: nv_gw = **2026-07-20T18:10:28Z** (连续第 10 轮核实未漂移) / cc4101 = 2026-07-19T12:10:22Z (0 restart)
- **env 快照**: 与 R2118/R2119 完全一致 (peer R2108 改后值: KEY60/TIER180/MIN_OUTBOUND10/UPSTREAM90/TIER_BUDGET180/GLM52_BUDGET120/DSV4P_BUDGET180), cc2 0 改动

## 决策: NOP R154 (连续第 90 轮冻结), 0 改动 0 restart

**理由**: 数据画像 = R2119 第三波 429 风暴 **延续 26min+ 未自愈 (异常, 之前各波均 ~15min 自愈)**, tier 429×23 翻倍加剧, 502 仍全 NVCF 已知类 0 新可配, fallback 全兜 0 真中断 0 失败, breaker 未真 OPEN. **不满足解冻触发条件** (风暴进行中 + 0 新可配类 + 0 真中断 + 0 fallback 失败 + 0 breaker 真 OPEN).

**根因**: NVCF 上游 429 rate limit 风暴延续期 (非网关逻辑缺陷). 解冻指数退避仍不对症 — 延长 chain_budget (120→420) 会**反拖 SR**: 本轮 6 条 chain_budget 耗尽类已证明风暴期请求会累积 retry 撑满 budget, 若上调到 420s 则更多请求会卡在 nv_gw 内 retry 420s 才 fallback, 实际 SR 更低 (R2111/R2116/R2119/R2120 四/六轮论证).

**新警觉 (本轮记录)**:
1. 第3波风暴延续 26min+ 未自愈, 持续时间显著超之前各波 (~15min). 需观察下一轮是否终于自愈, 还是演变为持续低 SR 稳态.
2. **首次出现 6 条 chain_budget 耗尽类 (cap_origin reset execute→ms_fb, 121-130s)** — 风暴持续期请求累积 retry 撑满 120s budget. 全被 ms_fb 兜住 0 真中断, 但若持续增多需重新评估 chain_budget 是否要微调 (仍非解冻指数退避的理由).
3. 用户诉求 "可以报错但不让 cc2 中断" 仍达成 (8 fallback 全兜 0 真中断).

**不动 peer 旋钮**: KEY60/TIER180 是 peer R2108 改后值, cc2 不碰 (CLAUDE.md 铁律). peer hm2_optimize_hm1 近几轮在 HM1 侧 walk-back (R2114-R2118 TIER70→68→66→64 / KEY77→75→73, 均 HM1, cc2 不碰).

## 验证
- 0 改动 0 restart → 无需 restart 验证. nv_gw /health=ok, docker ps (StartedAt 18:10:28Z 未漂移) 确认运行中.
- 数据画像证实 NOP 正确: 30min SR 65.6% 被风暴高峰污染 (非持续恶化逻辑缺陷) + 502 全已知类 0 新可配 + 0 真中断 + breaker 未真 OPEN.

## 结论
连续第 90 轮冻结指数退避 (R1928 冻结决定延续). 本轮核心: **第3波 429 风暴延续 26min+ 异常未自愈 + tier 429×23 翻倍 + 首现 6 条 chain_budget 耗尽类**, 但 0 真中断 / 0 fallback 失败 / 0 新可配置类 / breaker 未真 OPEN → 不满足解冻条件, NOP 正确. 下一轮重点观察风暴是否终于自愈 + cap_origin reset 是否持续增多 (若 chain_budget 耗尽类持续增长再评估微调 chain_budget, 仍非解冻指数退避). HM2 only, 0 改动 0 restart.
