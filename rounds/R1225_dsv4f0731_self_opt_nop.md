# R1225: dsv4f0731_nv40666 NOP — 30min SR=98.6%(70/71), 单1错为k2 zombie_empty_completion(4096ms)上游瞬态, 无容器杠杆

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~12:50)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 71 / 70 / 1 (SR=98.6%) |
| Avg/P50/P95 | 34907 / 24467 / 105624 ms |
| 净429 | 0 |
| Fallback | 0 |
| upstream_type | nvcf_pexec 71 req, 70 SR=98.6% |
| finish_reason | tool_calls 51, stop 19 |

### 错误分类
- `zombie_empty_completion` ×1 (k2, 4096ms) — 报告200但无实际内容, 上游劣化瞬态信号。仅1次, 4秒极短, 未触发 NVU_EMPTY_200_FASTBREAK=3 阈值。

### per-key 200 延迟
- k0: 14req/36805 | k1: 15req/28191 | k2: 14req/39234 | k3: 9req/42600 | k4: 18req/33527
- 各 key 延迟均衡(28-42s), 无 key 劣化。错误仅 k2 1次。

### key_cycle_429s (内部循环计数, 非净错误)
- k1=56 偏高, 但 key manager 已吸收(净429=0) → KEY_COOLDOWN/429 cooldown 工作正常, 无需调整。

### 趋势
- 6h: 600/633 = 94.8% SR
- 3h逐小时: 02h=97.4% / 03h=85.1%(11错, 已恢复) / 04h(当前)=96.2%
- 24h all_tiers_exhausted=117, 逐小时 3-14 背景水平, 与近几轮持平(108-116)

## 为何不改
1. SR=98.6% 远超 95% 阈值, 延迟稳定, 净429=0, fallback=0。
2. 唯一错误 zombie_empty_completion 为 k2 上游瞬态(4096ms极短), 单次不构成持续劣化, 未达 FASTBREAK 阈值。
3. k1 高 cycle_429s 已被 key manager 吸收, 参数已生效。
4. all_tiers_exhausted 背景稳定(~117), 无上升趋势。
5. 上一轮 R1221 曾 TRY UPSTREAM_TIMEOUT→45 已生效, 无新信号需迭代。

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT→45)
- 上轮无超时相关错误(NVCFPexecTimeout=0); 本轮延迟正常, 保持。

## 下一步建议
- 持续观察 all_tiers_exhausted 24h 背景(~117)。若持续上升(>150)或高峰时段 3h SR 跌破 85%, 再考虑 NVCF 侧/上游层面, 而非本容器参数。
- k2 若再出现 stream 截断/zombie_empty_completion 需关注; 若短窗口内复现, 考虑将该 key 移出 integrate 或标记冷却。