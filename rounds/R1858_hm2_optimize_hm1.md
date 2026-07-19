# R1858 (HM2→HM1): KEY_COOLDOWN_S 60→58, TIER_COOLDOWN_S 60→58 (-2s each)

## 改前数据

### 6h DB (created_at >= NOW() - 6h)
| tier_model | total | ok | fail | SR |
|---|---|---|---|---|
| dsv4p_nv | 4 | 4 | 0 | 100.0% |
| glm5_2_nv | 31 | 16 | 15 | 51.6% |

### 30min DB
| tier_model | total | ok | fail | SR |
|---|---|---|---|---|
| glm5_2_nv | 4 | 0 | 4 | 0.0% |

### 错误类型 6h
- zombie_empty_completion: 15 (avg 4491ms) — uniform per-key: K0=3, K1=3, K2=3, K3=3, K4=3
- all_tiers_exhausted: 3 — all phantom (status=200), dsv4p_nv, single-key, not real failures

### tier_attempts 6h
- pexec_success: 42 (9+9+8+8+8 across K0-K4)
- pexec_429: 1 (K1)
- zero SSLEOF, zero timeout, zero NVCFPexecTimeout

### glm5_2_nv per-key latency (success only, 6h)
| key | total | avg_ms | p50_ms | p95_ms | max_ms |
|---|---|---|---|---|---|
| K0 | 8 | 6138 | 5038 | 12020 | 14181 |
| K1 | 6 | 4858 | 4862 | 6632 | 6638 |
| K2 | 7 | 5576 | 4992 | 8370 | 8969 |
| K3 | 5 | 4402 | 3677 | 6542 | 6692 |
| K4 | 5 | 6195 | 5910 | 10414 | 11353 |

### fallback 6h
- 0 fallback triggered (all 35 records have fallback_occurred=false)

### 关键指标
- key_cycle_429s: 0
- peer-fb: 0触发
- 容器日志: 0 error/warn (仅 `Listening on 0.0.0.0:40006`)

## 分析

15条 zombie_empty_completion 均匀分布在5个key (各3条), 证明是NVCF函数级问题而非per-key配置问题。key_cycle_429s=0, pexec_429仅1条, 无SSLEOF/timeout/ATE真失败。KEY_COOLDOWN_S=60对HM1极其保守 — HM2已是25且零429。KEY=TIER=60+60=120<<178 BUDGET, 有58s安全余量。缩小cooldown减少key轮转等待, 不影响成功路径延迟。

## 优化

- KEY_COOLDOWN_S: 60 → 58 (-2s)
- TIER_COOLDOWN_S: 60 → 58 (-2s)
- KEY=TIER=58 per iron law
- 58+58=116 << 178 BUDGET (62s margin)
- 单参数对; 铁律:只改HM1不改HM2

## 验证

- `docker exec nv_gw env | grep KEY_COOLDOWN` → 58 ✓
- `docker exec nv_gw env | grep TIER_COOLDOWN` → 58 ✓
- `docker compose up -d nv_gw` → Container nv_gw Started ✓
- `curl localhost:40006/health` → {"status":"ok"} ✓
## ⏳ 轮到HM1优化HM2
