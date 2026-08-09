# R1249: NOP — dsv4f0731_nv40666 健康稳态延续 (5 连窗 SR >95%)

## 修改
- **无参数修改** (NOP)。env 与 R1248 完全一致:
  - UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180
  - KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, KEY_AUTHFAIL_COOLDOWN 未变
  - NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120, CONN_*=30/60/3/120
  - NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3

## 依据 (30min 窗口)
- **SR = 96.4% (54/56)**, 高于 NOP 阈值 95%, 连续 5 窗 SR>95% (R1246 98.8%/R1247 97.5%/R1248 98.7%/本窗 96.4%).
- **5 key 完美负载均衡** (k0=10/k1=12/k2=11/k3=10/k4=10), avg 19.7-30.7s 均匀, **无任何 key 劣化**。
- **net 429 = 0**; key_cycle_429s (k0=44,k1=7,k2=3,k3=1) 计数仅 key manager 内部保护, 已完全吸收。
- **错误仅 2 个孤立瞬态**: all_tiers_exhausted (1, avg 180s = 恰为 tier budget, 单次 NVCF 过载时隙) + NVStream_IncompleteRead (1, 112s 长流截断)。无 `zombie_empty_completion`, 无系统性问题可调。
- **upstream 全 pexec** (55/53), 无 integrate 路由激活 (NV_INTEGRATE_MODELS 空, 当前架构全走 pexec — 与 R1245 链路设计一致)。
- finish_reason: tool_calls=46 / stop=7 (**87% tool_calls** → avg 31.7s / p95 105s 属长 agentic 流, 非代理/超时问题, 跨 key 一致).

## 复核 (采集后推进)
- docker exec logs_db 复核最近 30min: `NVStream_IncompleteRead=0, all_tiers_exhausted=0` — 窗口内 2 错误已滚出, 当前无活跃错误。

## 趋势确认
- 6h: 378 req SR=92.1% (含昨日 NVCF 过载历史); 3h 逐小时回落: 22h **97.1%**/21h 95.3%/20h 90.2%/19h 3req — 活跃窗口健康, 19-20h 90% 属昨日过载长尾。
- **24h all_tiers_exhausted = 291, 较 R1248(293) 回落** — 历史遗留计数仍随窗口滚动下降, 无新生累积, 确认昨日过载为一次性事件。

## 判定 (为什么 NOP)
1. SR 96.4% > 95% 阈值, 连续 5 窗稳态。
2. 只有 2 孤立瞬态错误 (各自仅 1 次, 窗口滚动后已归 0), 无流截断/空响应/净 429 集中征兆。
3. 5 key 负载均衡无劣化, key manager 冷却保护正常 (net 429=0)。
4. **fallback 低**: hm4104 仅 1 次 FALLBACK-FAIL-STREAM (ms_gw 流式 503 after 177s), 系 ms_gw 侧 503 而非本容器 40666 失稳 — 40666 primary 链路健康, 无明显 fallback 可降。
5. 24h ATE 滚动回落, 过载为非活跃历史。
6. 无数据支撑的参数改动理由 — 强行调 budget/冷却反而引入连锁效应风险 (见 R12/R13 TIER_COOLDOWN 教训)。

## 验证
- [x] `docker exec dsvf0731_nv40666 env` 参数未变 (UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN=30, TIER_COOLDOWN=90, NVU_KEYMGR_* 稳定)
- [x] /health = ok (dsvf0731_nv40666, 5 keys, port 40666)

## 下一步建议
- **本容器继续 NOP**: 连续 5 窗 SR>95%, NVCF 过载长尾渐退, 健康稳态确立。
- 持续观察 24h ATE 回落到 <100 后, 3h/6h SR 若稳定 >95%, 正式确认昨日过载为一次性事件。
- 关注 hm4104 fallback 触发率: 本窗 1 次 (ms_gw 503, 0.2%级), 若下一窗 >5% 且触因指向 40666 失稳 (而非 ms_gw), 再上 40666 杠杆。
- 若 30min SR 持续 <85% 或 24h ATE 重新 >150, 上报基础设施层治理 NVCF 过载, 本容器不擅自改 budget 伪装修复。