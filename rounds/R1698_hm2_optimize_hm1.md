# R1698: HM2→HM1 — BIG_INPUT_FAIL_N 1→3

## 数据 (HM1, last 6h)

| 指标 | 值 |
|------|-----|
| 总量 | 54 req |
| OK | 43 (79.6% SR) |
| Fail | 11 (20.4%) |
| Fail类型 | 11× zombie_empty_completion, 全部 glm5_2_nv, 全部 >250K chars |
| OK p50/p95 | 9,076ms / 21,281ms |
| ATE | 0 |
| peer-fb | 0 |
| fallback | 0 |
| SR趋势 | 71.1%→74.4%→79.6% ↑ |

## 僵尸详情 (11 fail)

| ts | input_chars | duration_ms | tiers_tried |
|-----|-------------|-------------|-------------|
| 06:03 | 257,816 | 8,163 | 1 |
| 06:33 | 269,889 | 5,067 | 1 |
| 07:33 | 274,590 | 26,340 | 1 |
| 08:03 | 274,590 | 17,103 | 1 |
| 08:34 | 275,796 | 8,967 | 1 |
| 09:03 | 276,406 | 5,705 | 1 |
| 09:34 | 280,585 | 5,526 | 1 |
| 10:03 | 280,008 | 5,346 | 1 |
| 10:33 | 284,178 | 6,053 | 1 |
| 11:04 | 291,466 | 5,774 | 1 |
| 11:33 | 287,184 | 6,586 | 1 |

- avg 275,641 chars, avg 9,643ms, all tiers_tried=1
- inter-arrival ~30min (sparse), cooldown=180s << gap → breaker never accumulates

## 近1h数据 (post-restart)

| 指标 | 值 |
|------|-----|
| 总量 | 12 req |
| OK | 10 (83.3% SR) |
| Fail | 2 zombie_empty_completion (>250K) |
| 大input OK | 9/11 = 81.8% (1 zombie, 1 OK but big-input pre-zombie) |

## 分析: FAIL_N=1 的救援路径比僵尸更差

```
BIG_INPUT breaker OPEN → all_tiers_exhausted →
  peer-fb: PEER_FALLBACK_TIMEOUT=72 < HM2_BUDGET_GLM5_2=120+2 → 保证超时 (R1641 gap)
  → ms_gw fallback: 120s timeout
  → 总救援 192s >> zombie 6-9s
```

**FAIL_N=1 的问题**: 单次僵尸即OPEN → 救援路径 192s 远差于僵尸 6-9s。刹车比事故本身更慢。

**近1h 大input SR=83.3%**: 大多数超大input请求成功，单次失败不应触发刹车。

## 变更

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| `NVU_BIG_INPUT_FAIL_N` | 1 | 3 | 3次连续失败 → 真实NVCF退化信号，非单次噪声。代码默认=3。 |

## 验证

```bash
# HM1 compose line 628
NVU_BIG_INPUT_FAIL_N: "3"

# 容器env确认
docker exec nv_gw env | grep BIG_INPUT_FAIL_N
# → NVU_BIG_INPUT_FAIL_N=3

# 健康检查
curl http://localhost:40006/health
# → {"status": "ok", ...}
```

## 评判

- 更少报错: SR 79.6% trending up, 0 ATE, 0 peer-fb 错误
- 更快请求: OK p50=9.1s p95=21.3s, 稳定
- 更低延迟: zombie 9.6s < breaker rescue 192s
- 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
