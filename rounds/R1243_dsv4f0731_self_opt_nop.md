# R1243: dsvf0731_nv40666 self-opt NOP — SR 92.5% 持稳, 6错全为 NVCF 过载 ATE, fallback 为过载震荡下游, 无容器杠杆

> 时间: 2026-08-09 19:09 Shanghai (R1242 后 ~12min, 采集窗口 ~10:58 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
> 状态: **NOP (无参数修改)** — 30min SR **92.5%** (74/80), 与 R1242 高位(93.8%)持平;
> 6 错误全部为 `all_tiers_exhausted` (tier 级 5-key 全烧满 180s budget 的 NVCF 过载信号);
> 无净 429, 无 key 劣化, upstream 100% pexec 正常, tier_attempts 空;
> hm4104 fallback 活跃 (20min 8 事件) 但全部为 nv_gw 502@144-180s (budget 烧满) 的下游瞬态,
> 与 R1237 过载震荡同类, 非持续恶化 (6h SR 87.6%, 24h ATE=139 稳于背景带)。

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, ~10:58 UTC)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 80 / 74 / 6 (SR=92.5%) |
| Avg / P50 / P95 | 60669 / 44843 / 182949 ms |
| 净429 | 0 |
| upstream_type | nvcf_pexec 80 req, 74 SR=92.5% (100% pexec, integrate 0) |
| finish_reason | tool_calls 57, stop 12, null 5 |

### 错误分类 (6错: 全部 all_tiers_exhausted)
| error_type | n | avg_ms | 判定 |
|---|---|---|---|
| all_tiers_exhausted | 6 | 152609 | tier 级, 5 key 全烧满 TIER_TIMEOUT_BUDGET=180s → NVCF 过载残余, 无容器杠杆 |

### per-key 200 延迟 (count/avg/p95)
- k0: 20 / 58070 / 135863 | k1: 18 / 53602 / 129116 | k2: 15 / 46244 / 125271 | k3: 15 / 38537 / 64141 | k4: 6 / 89984 / 175274
- k0-k3 avg 38-58s 均衡健康 (典型 NVCF 延迟带); k4 avg 90s/p95 175s 偏高但**仅 6 请求** (小样本, 负载轻),
  且无对应错误, 非持续劣化, 不构成调整 integrate 路由的动机。

### per-key 错误细分
- k0: all_tiers_exhausted 6 — tier 级 5-key 全失败归属 (k0 轮转起始位伪象), 非 k0 代理故障。

### key_cycle_429s (内部循环计数, 非净错误)
- k0=26, k1=53, k3=1
- k1 持续偏高(53)但 net 429=0, key manager 已吸收 → cooldown 工作正常, 无需调 KEY_COOLDOWN。

### 6h/3h/24h 趋势
- 6h: 700 req, 616 SR=88.2% (0 失败非 429)
- 3h 逐小时: 10h=157/142 SR90%, 09h=140/125 SR89%, 08h=123/101 SR82% (峰值残影)
- 24h all_tiers_exhausted = 139 (从 R1242 的 138 微升 1, 已完全停于背景带 116-139, 无持续累积)

### hm4104 fallback (近 20min: 8 事件) — 过载震荡下游
- 18:56 502@180049ms + 切 fallback; 19:04×2, 19:08 502@144154ms, 19:09 切 fallback
- 全部触发为 nv_gw 返回 502@144-180s (PRIMARY_STREAM_TIMEOUT=90 + budget 烧满延时), 即 primary 在上游
  NVCF 过载下烧满 budget 后返回 502, hm4104 才切 ms_gw。这是 **NVCF 过载的传播链下游**, 非本容器参数失误。

## 判定逻辑 (为什么 NOP)
1. **SR 持稳 ≥90% (92.5%)**: 与 R1242 高位持平, 处健康带。
2. **6 错误全为 tier 级 overloading ATE**: 无 429 净错误、无 key 劣化、无流截断/空响应, 容器层无杠杆可动。
3. **R1233/R1234 已论证收缩 NVU_TIER_BUDGET_DSV4F0731_NV 非正解**: 只让 primary 更快放弃并切 fallback,
   不改善 NVCF 过载本身; 当前 180s budget 是合理的重试窗口。
4. **fallback 活跃是 NVCF 过载震荡而非持续恶化**: 6h SR 88.2% 稳定、24h ATE=139 稳于背景带 (116-139)、
   上游层 100% pexec 正常, 传播链下游瞬态, 非本容器问题。
5. **无净 429 + key_cycle 被 key manager 吸收**: KEY_COOLDOWN/NVU_KEYMGR_* 均无需调整。

## 验证
- [x] `docker exec dsvf0731_nv40666 env` 参数未变 (TIER_COOLDOWN=90, NVU_TIER_BUDGET_DSV4F0731_NV=180, KEY_COOLDOWN=30)
- [x] /health = ok (dsvf0731_nv40666 Up 10 hours)
- [x] 容器未重启 (保持 10h uptime)

## 下一步建议
- 继续观察高峰过载: 若再 1-2 轮 30min SR 稳定 ≥90% 且 24h ATE 稳于 ≤140, 确认高峰已越过, 容器保持健康 NOP。
- 若 SR 再跌 <85% 且 24h ATE 持续 >140, 才评估从上游/调度层 (并发/请求节流) 治理 — 但非本容器参数。