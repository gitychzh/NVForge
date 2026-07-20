# R2122 (HM2→HM1): TIER_COOLDOWN_S 64→62 (-2s)

## 数据 (HM1, 2026-07-21 05:55 UTC)

### 6h DB (docker exec logs_db psql):
| Metric | Value |
|---|---|
| 总请求 | 47 |
| 成功 (status 200-299) | 28 |
| 失败 | 19 |
| **SR** | **59.57%** |
| 真实 ATE (error_type=all_tiers_exhausted AND status=502) | 9 |
| zombie_empty_completion (glm5_2_nv) | 10 |

### 错误明细:
- dsv4p_nv ATE ×9: tiers_tried_count=1, fallback_tiers_used={dsv4p_nv} — 所有 ATE 只试了 dsv4p 一个 tier，kimi_nv 和 glm5_2_nv fallback tier 全部被跳过
- glm5_2_nv zombie ×10: NVCF func-level empty completion
- 0 fallback_occurred (全 47 请求无 fallback)
- 0 peer-fb triggered
- glm5_2_nv 429 cycling: 24 cycles (22×1, 1×2, 1×5) — 轻微

### 延时:
- glm5_2_nv 成功: avg=13311ms (18/28)
- dsv4p_nv 成功: avg=16001ms (10/19)

### Tier attempts:
- dsv4p ATE 9 个 request_id 在 nv_tier_attempts 中 **0 条记录** — dsv4p tier 无任何 attempt 被记录
- glm5_2_nv tier_attempts: 24 pexec_success, 4 pexec_timeout, 1 pexec_SSLEOFError

### docker logs nv_gw --tail 100:
零错误。容器刚重启 (05:55)，日志只有 startup banner。

## 分析

核心问题：dsv4p_nv ATE 的 fallback chain (kimi_nv → glm5_2_nv) 完全未被触发。
9 个 ATE 全部 `tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}` — 只有 dsv4p 被尝试。
kimi_nv 和 glm5_2_nv 两个 fallback tier 被静默跳过。

TIER_BUDGET_GLM5_2_NV=25 (> UPSTREAM=24) → 不是预算问题 (R2112 已修)。
TIER_BUDGET_DSV4P_NV=48 (允许 2 key × 24s) → 足够。
FALLBACK_HEALTH_THRESHOLD=0.05 → 很低，不应排除 tier。

可能原因：TIER_COOLDOWN_S=64s — 如果 kimi_nv 或 glm5_2_nv 之前被标记 cooldown
(64s)，在 dsv4p ATE 密集爆发期 (18:00-18:08 UTC，9 个 ATE 在 ~8min 内) 会被跳过。

## 优化

TIER_COOLDOWN_S: 64 → 62 (-2s)

- 继续 storm-recovery walk-back (R2117: 66→64, R2121: KEY 68→66)
- KEY+TIER = 66+62 = 128 << 153 BUDGET (25s 余量，充分安全)
- -2s 缩短 tier cooldown 窗口，提高 fallback tier 在 ATE 爆发期的可用概率
- 保守步长 (-2s)，与历史 walk-back 步长一致
- 单参数修改；铁律：只改 HM1 不改 HM2

## 验证

```bash
# compose 确认
ssh -p 222 opc_uname@100.109.153.83 "sed -n '505p' /opt/cc-infra/docker-compose.yml"
# → TIER_COOLDOWN_S: "62"  # R2122 (HM2->HM1): ...

# live env 确认
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_gw env | grep TIER_COOLDOWN_S"
# → TIER_COOLDOWN_S=62

# health check
curl -s http://localhost:40006/health  # → {"status": "ok"}
```

容器已重启，env 已生效。等待下一轮数据验证 fallback chain 是否恢复触发。

## ⏳ 轮到HM1优化HM2
