# R1222: dsv4f0731_nv40666 NOP — 30min SR=95.83% 健康临界上沿, 2错为NVCF侧tier级ATE(烧满180s budget), 无429/无单key劣化/无请求级超时, 3h趋势回升, 24h ATE=109 历史水位

日期: 2026-08-09 11:04 UTC 采集窗口 (~30min)
容器: `dsvf0731_nv40666` (端口 40666, num_keys=5, DeepSeek V4 Pro via NVCF pexec)
主机: HM2 (opc2sname)

## 决策：NOP（不改任何参数）

30min SR=46/48=**95.83%**（临界上沿但高于 95% NOP 阈值，延续 R1214→R1221 的健康波动）。
2 个错误均为 NVCF 侧 tier 级 ATE（各烧满整段 budget），无本容器可调杠杆。3h 趋势显著回升。

**证据链**：
1. **all_tiers_exhausted ×2 (avg 174734ms)** — 2 个均烧满整段 ~175s/180s budget 的 tier 级事件
   （5 个 key 全部尝试后均失败，归因 k0 仅为循环起点）。与历轮同型的 NVCF 全键同质过载，
   非参数可调。区别于 R1221 的 1 例，本窗 2 例但仍属 NVCF 侧偶发。
2. **净 429 = 0** — 请求级 429 计数为 0。key_cycle_429s (k0=11, k1=36, k2=1) 为内部轮转吸收
   计数，k1 偏高延续既有水位（R1221=48 → 本轮 36，略降），不影响请求级结果。
3. **per-key 200 延迟全部健康** — k0=27567, k1=42595, k2=33062, k3=27767, k4=27556 (avg ms)。
   5 个 key 均正常，无单 key 劣化（k1 虽 429 轮转计数高，但 200 延迟 42.6s 在正常分布内）。
4. **upstream_type 全 pexec，integrate=0，tier_attempts 空** — 无 pexec/integrate 失衡，
   无 key 间切换异常。finish_reason: stop 23 / tool_calls 23 均衡。
5. **hm4104 fallback 日志（最近 5min）×3** — FALLBACK-STREAM ×2 + PRIMARY-BREAKER-SKIP ×1。
   此为 hm4104 适配器相对其 primary nv_gw(40006) 链路（默认 glm5_2_nv）的 fallback，非本
   dsv4f0731_nv(40666) 容器直接归因；本容器 30min 窗自身 95.8% SR 健康。该事件数量少且为
   适配器级，不构成对本容器参数调整的依据。
6. **3h 逐小时趋势回升** — 00:00=92.3% → 01:00=96.2% → 02:00=97.4% → 03:00=100%。
   早高峰过载段已过去，当前段恢复健康。
7. **延迟分布健康** — Avg=38561ms, P50=25871ms, P95=96941ms。P50 显著低于 Avg（长尾拖高均值），
   P95≈97s 处仍有成功请求，符合 pexec 长流预期。

## 30min 窗口数据（脚本注入）

| 指标 | 值 |
|---|---|
| SR | **95.83%** (46/48, 2 err, 0 timeout) |
| Avg / P50 / P95 | 38561 / 25871 / 96941 ms |
| 429 | 0 |
| upstream_type | nvcf_pexec 48/48 (100%), integrate 0 |
| finish_reason | stop 23, tool_calls 23 |

**错误分类**：`all_tiers_exhausted: 2 (avg 174734ms)` — 2 例均烧满整段 budget 的 NVCF 侧 ATE。

**Per-key 200 延迟**（均衡, 无单 key 劣化）:
```
key0|6req|avg27567
key1|11req|avg42595
key2|12req|avg33062
key3|11req|avg27767
key4|6req|avg27556
```

**趋势**:
- 6h: 682 req, SR=95.6% (652 ok / 30 err)
- 3h 逐小时: 03:00=3/3(100%), 02:00=117/114(97.4%), 01:00=104/100(96.2%), 00:00=104/96(92.3%)
- 24h all_tiers_exhausted = 109 (历史累积, 本窗 2 例新增属 NVCF 偶发)

## 决策依据汇总

本窗为**健康临界上沿**：95.8% SR 高于 NOP 阈值，2 个错误均为 NVCF 侧 tier 级 ATE（烧满
budget，非容器可调），净 429=0、无单 key 劣化、无请求级超时、无 pexec/integrate 失衡。
3h 趋势自早高峰 92.3% 回升至 100%。hm4104 的 fallback 事件归因于适配器级 nv_gw primary
链路（glm5_2_nv），非本容器。按"必须有数据支撑 + 一次只改一个参数"原则，无任何可归因
杠杆，维持当前参数（UPSTREAM_TIMEOUT=45, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, TIER_COOLDOWN_S=90, KEY_COOLDOWN_S=30,
NVU_KEYMGR_429_BASE/MAX=120）即可。

## 下一步建议

- 若 hm4104 的 fallback/PRIMARY-BREAKER-SKIP 事件在后续窗口持续增多（非适配器级偶发），
  需回溯确认是 nv_gw(40006) 的 glm5_2_nv 还是本 dsv4f0731_nv 链路触发，再决定是否调整
  TIER_COOLDOWN_S(90) 或 fast-break 阈值。
- 持续观察 24h ATE 累积：若本窗 2 例 ATE 在后续窗口高频复现（非偶发），评估是否需收紧
  TIER_TIMEOUT_BUDGET_S 以缩短单次烧 budget 时间。
- 当前链路健康，建议保持 NOP 直至出现新的可归因退化信号。