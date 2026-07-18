# R1856 (HM2→HM1): NOP — 全 zombie_empty_completion, NVCF content-filter 非 config 可修

## 改前数据 (6h window, HM1 DB, 2026-07-19 07:45 UTC)

```
SR: 32/43 = 74.4% (200:32 / 502:11)
```

### 502 分类 (11条)
| error_type | count | 分析 |
|---|---|---|
| zombie_empty_completion | 11 | NVCF content-filter 行为, glm5_2_nv, content_chars=12, reasoning_chars=0, 非 config-fixable |

### 模型维度
| mapped_model | total | ok | fail | avg_ms | max_ms |
|---|---|---|---|---|---|
| glm5_2_nv | 29 | 18 | 11 | 6456 | 14181 |
| dsv4p_nv | 14 | 14 | 0 | 14718 | 40603 |

### input size 分布 (glm5_2_nv)
| input_range | total | ok | fail | avg_ok_ms |
|---|---|---|---|---|
| 0-50k | 6 | 6 | 0 | 6137 |
| 50k-100k | 7 | 7 | 0 | 19697 |
| 100k-150k | 16 | 5 | 11 | 11413 |
| 200k+ | 14 | 14 | 0 | 6465 |

### tier attempts
| tier | error_type | count |
|---|---|---|
| glm5_2_nv | pexec_success | 40 |
| dsv4p_nv | 429_nv_rate_limit | 2 |
| glm5_2_nv | pexec_429 | 1 |

### 30min window
```
SR: 1/3 = 33.3% (2条 zombie_empty_completion)
```

### 关键观察
- 全部11条502 = zombie_empty_completion (glm5_2_nv): NVCF content-filter 返回空 completion, R852b zombie 检测在 2.3-8.0s 内 abort, 触发 cc4101 retry
- zombie 全集中在 100k-150k 输入区间 (115726-118366 chars), 0-50k/50k-100k/200k+ 区间 0 zombie
- 日志显示 5 keys 轮转均触发 zombie, 模式与 R1850/R1851 一致
- dsv4p_nv 14/14 OK, 延迟 NVCF 侧 (>14s avg), 2条 429 tier-level (0 request failure)
- 0 fallback 触发, 0 breaker OPEN, 0 新错误分类
- 0 restart 0 中断, StartedAt 维持 2026-07-18T21:26:29Z (R1839 改后字节码)
- env 无漂移: UPSTREAM_TIMEOUT=51, TIER_TIMEOUT_BUDGET_S=178, KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=60, NVU_TIER_BUDGET_DSV4P_NV=39, NVU_TIER_BUDGET_GLM5_2_NV=60, MIN_OUTBOUND_INTERVAL_S=0, NVU_PEER_FALLBACK_TIMEOUT=122, NVU_MS_GW_FALLBACK_TIMEOUT=120, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66

## 决策: NOP — 不改

- 全部 502 为 zombie_empty_completion: NVCF 侧 content-filter 行为, 非 HM1 任何 config 参数可修
- dsv4p_nv 高延迟: NVCF 侧, 非 config 可修
- input 100k-150k 区间 zombie 高发 — 但 BIG_INPUT_THRESHOLD=250000, 这些请求不触发大输入逻辑; 且 zombie 是 NVCF 侧行为, 调整阈值无法阻止 content-filter
- 无新错误分类, 无 fallback 恶化, 无 breaker OPEN
- 硬改违反铁律: 改前必有数据, 聚焦 nv_gw
- 0 restart 0 中断
- R1842-R1856 连续15轮 zombie 主导 (含 HM1 cc2 inspect 轮), SR 在 74-98% 区间抖动, 非系统退化

## 评判: 更少报错更快请求超低延迟稳定优先
- 11 条 zombie NVCF 非可控 → 不触发介入
- 链路稳, 无 config 可改依据 → NOP
- 铁律: 改前必有数据 → 0 改
## ⏳ 轮到HM1优化HM2
