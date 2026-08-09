# R1224: dsv4f0731_nv40666 NOP — 30min SR=90%(36/40) 小样本, 4错全为NVCF侧(2×tier级ATE烧满budget + k2流截断×2), 无容器杠杆

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~12:20)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 40 / 36 / 4 (SR=90%) |
| Avg/P50/P95 | 52018 / 35063 / 147666 ms |
| 净429 | 0 |
| Fallback | 0 |
| upstream_type | nvcf_pexec 39 req, 36 SR=92.3%; 1 null(上报null key的ATE) |

### 错误分类
- `all_tiers_exhausted` ×2 (avg 185717ms) — **tier级**, 5 key 全部烧满 TIER_TIMEOUT_BUDGET=180s 后放弃 → NVCF 侧过载
- `NVStream_IncompleteRead` ×1 (k2, 115601ms) — k2 流被上游截断
- `stream_absolute_cap` ×1 (k2, 170579ms) — k2 流到绝对上限

### per-key 200 延迟
- k0: 8req/33072 | k1: 8req/57328 | k2: 8req/41636 | k3: 7req/28892 | k4: 5req/32913
- k1 延迟最高但 8 次全成功; 无 key 错误集中(错误分散在 k0/k2/null)

### key_cycle_429s (内部循环计数, 非净错误)
- k1=27 偏高, 但 key manager 已吸收(净429=0) → 参数已生效, 无需调 KEY_COOLDOWN

### 趋势
- 6h: 594/631 = 94.1% SR
- 3h逐小时: 01h=94.9% / 02h=97.4% / 03h=85.1%(11错,一小时前已恢复) / 04h=93.3%
- 24h all_tiers_exhausted=116 (持续背景水平, 与近几轮 108-116 持平)

## 为何不改
1. 4 个错误全部是 **NVCF 侧/tier 级信号**: 2× all_tiers_exhausted 是 tier 预算烧满(过载), stream 截断×2 是上游流问题。均非容器 key/超时/冷却参数可治愈。
2. 净 429=0 → KEY_COOLDOWN/429 cooldown 已正确吸收。
3. 无 fallback 触发, k1 高 cycle 但成功率高, 无 key 劣化。
4. 30min 仅 40 请求小样本, SR=90% 的偏离来自 NVCF 过载瞬间, 非长期趋势(6h=94.1% 正常)。
5. 上一轮 R1221/R1223 曾 TRY 降低 UPSTREAM_TIMEOUT 至 45 → 当前已生效, 无新信号需迭代。

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT→45)
- 30min 无超时相关错误(NVCFPexecTimeout=0), 延迟稳定, 保持。

## 下一步建议
- 持续观察 all_tiers_exhausted 24h 背景(当前~116)。若持续上升(>150)或 3h SR 在高峰时段跌破 85%, 再考虑 NVCF 侧/上游层面, 而非本容器参数。
- k2 若再出现 stream 截断需关注(本窗口 2 次), 但目前不足以触发 NVU_PEXEC_TIMEOUT_FASTBREAK=3 阈值。