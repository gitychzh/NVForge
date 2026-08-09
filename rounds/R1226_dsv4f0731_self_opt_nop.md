# R1226: dsv4f0731_nv40666 NOP — 30min SR=97.1%(67/69), 2错均为k2/k4上游瞬态(非持续劣化), hm4104 fallback为content_filter僵尸非容器杠杆

## 结论: NOP (不改任何参数)

## 依据 (30min 窗口, 2026-08-09 ~13:04)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 69 / 67 / 2 (SR=97.1%) |
| Avg/P50/P95 | 24688 / 123991 / 146368 ms |
| 净429 | 0 |
| Fallback | 0 (容器级) |
| upstream_type | nvcf_pexec 69 req, 67 SR=97.1% |
| finish_reason | tool_calls 52, stop 15 |

### 错误分类
- `stream_absolute_cap` ×1 (k4, 159925ms) — k4 流到绝对上限(159s), 上游持续输出超长
- `zombie_empty_completion` ×1 (k2, 4096ms) — 报告200但无实际内容, 上游瞬态, 4秒极短, 未达 NVU_EMPTY_200_FASTBREAK=3 阈值

### per-key 200 延迟
- k0: 13req/46171 | k1: 15req/35452 | k2: 13req/34843 | k3: 10req/43767 | k4: 16req/32490
- 各 key 延迟均衡(32-46s), 无 key 劣化。错误分散 k2/k4, 各1次。

### key_cycle_429s (内部循环计数, 非净错误)
- k1=51 偏高, 但 key manager 已吸收(净429=0) → 429 cooldown 工作正常, 无需调整。

### hm4104 fallback 日志 (最近30min, 非容器级)
- 22 条 REQ 全部 model=dsv4f0731_nv, 其中 5× FALLBACK-STREAM + 4× PRIMARY-BREAKER-SKIP + 1× PRIMARY-ZOMBIE-FALLBACK + 1× FALLBACK-FAIL-STREAM(ms_gw 70s timeout) + 1× PRIMARY-RETRY-OK-STREAM
- **触发根因**: 1 次 `CONTENT_FILTER_ZOMBIE` (12:59:52) — primary 流中检测到 content_filter 僵尸 → 切 ms_gw。这是 **模型输出内容被判定为 content_filter**, 属上游 NVCF 内容审核瞬态, 与网关/容器 key/超时参数无关。
- 后续 PRIMARY-BREAKER-SKIP 是 zombie 触发后的 circuit-breaker 冷却窗口, 13:02:41 PRIMARY-RETRY-OK 已恢复 primary。

### 趋势
- 6h: 598/631 = 94.8% SR
- 3h逐小时: 05h=100% / 04h=95.7% / 03h=85.1%(11错, 已恢复) / 02h=97%
- 24h all_tiers_exhausted=116, 与近几轮持平(108-117)

## 为何不改
1. SR=97.1% 远超 95% 阈值, 净429=0, 容器级 fallback=0。
2. 2 个错误均为上游瞬态: stream_absolute_cap 是超长输出到绝对上限(正常边界行为), zombie_empty_completion 4096ms 极短单次, 均未达 FASTBREAK 阈值, 不构成持续劣化。
3. hm4104 的 fallback 由 content_filter 僵尸(模型输出内容层面)触发, 非本容器可调参数可治愈; circuit breaker 已自动恢复 primary。
4. k1 高 cycle_429s 已被 key manager 吸收(净429=0), 参数已生效。
5. all_tiers_exhausted 背景稳定(~116), 无上升趋势。

## 上次修改效果 (R1221 UPSTREAM_TIMEOUT→45)
- 持续生效: 近 4 轮无超时类错误(NVCFPexecTimeout=0), 延迟稳定, 保持。

## 下一步建议
- 观察 content_filter zombie 是否频发: 若 24h 内出现 ≥3 次, 属 NVCF 内容审核侧问题, 建议在 hm4104 侧评估(非本容器范围); 单次可忽略。
- 持续观察 all_tiers_exhausted 24h 背景(~116)。若持续上升(>150)或高峰时段 3h SR 跌破 85%, 再考虑 NVCF 侧/上游层面。
- k4 stream_absolute_cap 若复现, 关注是否超长输出集中; 当前 NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90 与 UPSTREAM_TIMEOUT=45 组合下 159s 才到 cap, 属预期边界。