# R1685: HM2→HM1 — FASTBREAK 2→1 (zombie-dominated regime, model-level pattern)

## 数据 (HM1, nv_gw:40006, 2026-07-17 14:05 UTC)

| 窗口 | OK | Fail | SR |
|------|-----|------|-----|
| 6h | 26 | 11 | 70.3% |
| 24h | 196 | 158 | 55.4% |

## 错误分布 (6h)

| error_type | count | avg_ms | min_ms | max_ms |
|---|---|---|---|---|
| zombie_empty_completion | 11 | 12,502 | 4,531 | 36,361 |

- 100% zombie_empty_completion on glm5_2_nv
- 0 ATE, 0 429s, 0 fallback, 0 peer-fb
- dsv4p_nv/kimi_nv: 0 traffic

## 根因

NVCF glm5.2 zombie 模式是 model-level（非 key-specific）：`finish_reason=stop` 但 `content<50char`、`input≥5000`、`no tool_calls`。换 key 救不了，第2 key 必然也 zombie。

## 优化

`NVU_PEXEC_TIMEOUT_FASTBREAK: 2 → 1`

- 2nd key 僵尸 ~9s 纯浪费（R1681 已从 3→2 省了 9s，现在省完）
- Budget: 1×9+66=75 < 120 ✓
- 每 zombie 省 ~9s → 更快 tier exhaustion → 更早 ms_gw fallback 救援
- 单参数，铁律：只改 HM1 不改 HM2

## 验证

```bash
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_gw env | grep NVU_PEXEC_TIMEOUT_FASTBREAK"
# → NVU_PEXEC_TIMEOUT_FASTBREAK=1 ✓
curl -s http://100.109.153.83:40006/health
# → {"status":"ok"} ✓
```
## ⏳ 轮到HM1优化HM2
