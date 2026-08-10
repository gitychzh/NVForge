# R1251: NOP — dsv4f0731_nv40666 健康窗口延续 (SR 96.5%, 无 fallback, ATE 持平)

## 修改
- **无参数修改** (NOP)。env 与 R1250 完全一致:
  - UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180
  - KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90
  - NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120, CONN_*=30/60/3/120
  - NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3

## 依据 (30min 窗口 / 采集脚本)
- **SR = 96.5% (55/57)**, 高于 NOP 阈值 95%，健康窗口延续。
- **5 key 完美负载均衡** (k0=13/k1=10/k2=10/k3=14/k4=8)，avg 21.1-42.4s 均匀，**无任何 key 劣化**。
- **net 429 = 0**; key_cycle_429s (k0=42/k1=10/k2=1/k3=3/k4=1) 仅 key manager 内部保护, 已完全吸收。
- **错误仅 2 孤立瞬态**: all_tiers_exhausted (1, avg 180.1s = 恰为 tier budget, 单次 NVCF 过载时隙) + stream_absolute_cap (1, avg 168.4s = 长流绝对上限截断)。均各自 1 次, 无系统性征兆。
- **upstream 全 pexec** (57/55, SR=96.5%), 无 integrate 路由激活 (NV_INTEGRATE_MODELS 空 — 与 R1245-R1250 架构一致)。
- **finish_reason: tool_calls=50 / stop=5 (91% tool_calls)** → avg ~34s / p95 高属长 agentic 流, 非代理/超时问题, 跨 key 一致。

## 趋势确认
- 6h: 589/615 req SR=95.8% (含昨日 NVCF 过载历史); 3h 逐小时健康: 23h **100%**/00h 92.1%/01h 92.5%/02h **98.1%** — 活跃窗口稳定。
- **24h all_tiers_exhausted = 291, 与 R1250(291)/R1249(291) 完全持平** — 无新生累积, 昨日过载为一次性历史事件, 已稳定。
- **fallback = 0**: hm4104 最近 5min 无 fallback 日志 — 40666 primary 链路健康, 无可降空间。

## 判定 (为什么 NOP)
1. SR 96.5% > 95% 阈值, 健康窗口延续。
2. 仅 2 孤立瞬态错误 (各自 1 次, avg≈tier budget/长流上限, 窗口滚动后归 0), 无流截断/空响应/净 429 集中征兆。
3. 5 key 负载均衡无劣化, key manager 冷却保护正常 (net 429=0)。
4. **fallback = 0** (hm4104 无 fallback 日志) — 本容器链路完全健康。
5. 24h ATE 持平 (291), RemoteDisconnect 事件未在本窗出现 (R1250 报告的 NVCF 上游抖动未见复现), 无新数据支撑参数改动。
6. 强行调 budget/冷却会引入连锁效应风险 (见 R12/R13 TIER_COOLDOWN 教训), 无数据理由不调。

## 验证
- [x] `docker exec dsvf0731_nv40666 env` 参数未变 (UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN=30, TIER_COOLDOWN=90, NVU_KEYMGR_* 稳定)
- [x] /health = ok (dsvf0731_nv40666, 5 keys, port 40666, nv_default glm5_2_nv)
- [x] 容器状态正常 (nv_gw Up 2h, dsvf0731_nv40666 Up 2h, hm4104 Up 5d)

## 下一步建议
- **本容器继续 NOP**: SR>95%, fallback=0, ATE 持平, 健康稳态确立。
- 持续观察 24h ATE: 若继续持平在 ~290 且无新生累积, 正式确认昨日 NVCF 过载彻底消退。
- 关注 hm4104 fallback 触发率: 本窗 0 次, 若下一窗 >5% 且触因指向 40666 失稳 (而非 ms_gw), 再上 40666 杠杆。
- 若 30min SR 持续 <85% 或 24h ATE 显著跳增 (>200/日新生累积), 上报基础设施层治理 NVCF 过载, 本容器不擅自改 budget 伪装修复。