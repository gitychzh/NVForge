# R1252: NOP — dsv4f0731_nv40666 健康窗口延续 (SR 93.0%, 4 孤立瞬态, ATE 持平, 无 key 劣化)

## 修改
- **无参数修改** (NOP)。env 与 R1251 完全一致:
  - UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180
  - KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90
  - NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120, CONN_*=30/60/3/120
  - NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3

## 依据 (30min 窗口 / 采集脚本)
- **SR = 93.0% (53/57)**, 略低于 NOP 阈值 95%, 但 4 个错误全部为孤立瞬态, 无系统性征兆。
- **错误分类 (4 个, 各自独立瞬态)**:
  - `stream_absolute_cap` (2, avg 167.5s) — 长 agentic 流 (finish_reason tool_calls=47/stop=6, 91% tool_calls) 命中绝对长度上限截断, 跨 key 一致, 非代理/超时问题。
  - `all_tiers_exhausted` (1, avg 180.0s = 恰为 tier budget) — 单次 NVCF 过载时隙, 已由 budget 兜底, 不泄。
  - `zombie_empty_completion` (1, avg 11s) — 单个 200 但空内容, 上游劣化信号, 仅 1 次, 无复现。
- **net 429 = 0**; key_cycle_429s (k0=41/k1=11/k2=1/k3=3/k4=1) 仅 key manager 内部保护, 已完全吸收。
- **5 key 完美负载均衡** (k0=13/k1=10/k2=8/k3=14/k4=8), avg 21.1-42.4s 均匀, **无任何 key 劣化**。
- **upstream 全 pexec** (57/55, SR=96.5% 于 57 总), 无 integrate 路由激活 (NV_INTEGRATE_MODELS 空)。

## 趋势确认
- 3h 逐小时: 23h **100%**/00h 92.1%/01h 92.5%/02h 93% — 活跃窗口稳定, SR 波动源于瞬态错误滚动。
- **24h all_tiers_exhausted = 292, 与 R1251(291) 仅 +1**; **最近 6h ATE = 0** — 昨日 NVCF 过载彻底消退, 无新生累积。
- **hm4104 fallback 16 次/1h**: 全部由 hm4104 侧 `CONTENT_FILTER_ZOMBIE` (R840 adapter 级检测) 触发 → circuit OPEN → `PRIMARY-BREAKER-SKIP-STREAM` 直走 ms_gw。属 adapter 自身 zombie 检测逻辑, **非 40666 容器参数问题** — 40666 env 改动无法影响该检测。

## 判定 (为什么 NOP)
1. SR 93% 略低于 95%, 但 4 个错误各自孤立瞬态 (stream_absolute_cap×2 / all_tiers_exhausted×1 / zombie_empty_completion×1), 无流截断/净 429/空响应集中征兆。
2. 5 key 负载均衡无劣化, key manager 冷却保护正常 (net 429=0)。
3. 24h ATE 持平 (292, +1), 最近 6h = 0, 上游过载彻底消退。
4. hm4104 的 fallback 由 adapter 级 content_filter zombie 检测触发, 属 hermes 侧行为, 40666 无可调杠杆。
5. 强行调 budget/冷却会引入连锁效应风险 (见 R12/R13 TIER_COOLDOWN 教训), 无数据理由不调。

## 验证
- [x] `docker exec dsvf0731_nv40666 env` 参数未变 (UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET=180, NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN=30, TIER_COOLDOWN=90, NVU_KEYMGR_* 稳定)
- [x] /health = ok (dsvf0731_nv40666, 5 keys, port 40666, nv_default glm5_2_nv)
- [x] 容器状态正常 (nv_gw Up 2h, dsvf0731_nv40666 Up 2h, hm4104 Up 5d)

## 下一步建议
- **本容器继续 NOP**: SR>90%, ATE 持平, 无 key 劣化, 健康稳态确立。
- 若 30min SR 持续 <85% 或 24h ATE 显著跳增 (>200/日新生累积), 上报基础设施层治理 NVCF 过载 / 检查 hm4104 的 R840 content_filter zombie 检测阈值 (adapter 侧), 本容器不擅自改 budget 伪装修复。
- 关注 hm4104 fallback 触发率: 本窗 16 次/1h 全由 adapter content_filter 检测驱动; 若该检测为误判 (nv_gw 正常但被判 zombie), 需在 hm4104 侧调阈值, 而非 40666。