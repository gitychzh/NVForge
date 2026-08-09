# R1221: dsv4f0731_nv40666 NOP — 30min SR=98.39% 健康, 1错为NVCF侧tier级ATE(烧满180s budget), 无429/无单key劣化/无fallback, 24h ATE=108 历史水位

日期: 2026-08-09 10:52 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=61/62=**98.39%**（显著高于 95% NOP 阈值，延续 R1214 96.5% → R1215 95.2% →
R1216 96.97% → R1217 96.49% → R1218 95.74% → R1219 98.04% → R1220 100% → 本轮 98.39%
的健康波动）。仅 1 个错误为 NVCF 侧 tier 级 ATE，无本容器可调杠杆。

**证据链**：
1. **all_tiers_exhausted ×1 (180075ms)** — 单例烧满整段 180s budget 的 tier 级事件（5 个 key
   全部尝试后均失败，归因 k0 仅为循环起点）。与历轮同型的 NVCF 全键同质过载，非参数可调。
2. **净 429 = 0** — 请求级 429 计数为 0。key_cycle_429s (k0=12, k1=48, k2=1, k3=1) 为内部轮转
   吸收计数，k1 偏高是延续 R1218(30) → R1219(40) → R1220(46) → 本轮(48) 的既有水位，不影响请求级
   结果（per-key 200 延迟全部健康，见下）。
3. **per-key 200 延迟全部健康** — k0=29046, k1=34537, k2=25309, k3=23777, k4=33141 (avg ms)。
   5 个 key 均正常，无单 key 劣化（k1 虽 429 轮转计数高，但 200 延迟 34.5s 在正常分布内）。
4. **无 fallback** — hm4104 最近 5min 无 dsv4f0731 相关 fallback 事件。
5. **upstream 100% pexec** — upstream_type 全为 nvcf_pexec (62/62，SR=61)，无 integrate 分支活跃，
   无需调整 pexec/integrate 路由平衡。
6. **finish_reason 正常** — tool_calls=33 / stop=28，无异常空响应迹象。
7. **6h/3h 趋势健康** — 6h SR=661/692=95.5%，3h 逐小时 95-99% 稳定。

## 24h all_tiers_exhausted = 108（历史水位）

较最近几轮 (105/106/107) 略升 1-2 例，但均为 NVCF 侧全键同质过载的周期性事件，非本容器可调，
维持观察。180s budget 正确烧满后归因，无预算浪费。

## 结论

SR≥95% NOP 阈值，无 429、无单 key 劣化、无 fallback、无错误分类异常。唯一错误为 NVCF 侧
tier 级 ATE，框架上无可用杠杆。维持现有参数不动。

## 下一步建议

持续观察 24h ATE 是否继续爬升。若 ATE 连续数轮 >115 且伴随 SR 下滑，可考虑评估
`NVU_TIER_BUDGET_DSV4F0731_NV` (180) 是否在 NVCF 过载期需要收缩以更快切 fallback 保护
用户请求；但当前单轮 ATE=108 未触发该阈值，暂不改。