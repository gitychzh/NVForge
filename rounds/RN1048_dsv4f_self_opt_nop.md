# RN1048: dsv4f0731_nv40666 自优化 — NOP 轮

- **日期**: 2026-08-08 08:40 UTC (HM2, 本机 dsvf0731_nv40666 端口 40666)
- **类型**: NOP — 数据健康，不改任何参数
- **Tier**: dsv4f0731_nv (DeepSeek V4 Pro via NVCF pexec)

## 判定依据

### 30min 窗口（当前）
- **SR = 159/159 = 100%**，0 失败
- Avg=11360ms, p50=8835ms, p95=29523ms, max=47551ms
- **错误分类 (30min): 空** — 无任何 error
- **429 计数: 0**
- **fallback (hm4104, 最近5min): 无**

### per-key 均衡（30min）
| key | n | avg(200) | max(200) |
|-----|---|----------|----------|
| 0   | 33 | 11570   | 28175    |
| 1   | 32 | 11533   | 30026    |
| 2   | 29 | 8708    | 16587    |
| 3   | 33 | 12364   | 37556    |
| 4   | 32 | 12340   | 29641    |

5 keys 全部 200 SR=100%，延迟均衡（avg 8.7k–12.4k）。无劣化 key，无错误集中。

### upstream_type
- nvcf_pexec: 159 请求, 159 成功, avg 11360ms，SR=100%
- (integrate 当前未使用 — NV_KEY_INTEGRATE_KEYS 为空)

### 6h / 3h 趋势
- 6h: 2008 成功 / 2003 成功 5 错误，SR=99.75%
- 3h 逐小时: 22h=265/265(3错误), 23h=316/316, 00h=216/216 — 最近2小时 100%

### 24h 全量（nv_requests）
- 7144 成功 + 103 错误 = SR 98.6%
- all_tiers_exhausted: **45** 次 (avg 182838ms) — **但逐小时分析表明严重前重后轻**：
  - 00:00–08:00 UTC (北京 08:00–16:00, NVCF 高峰): 38/45 次 = 84%
  - 17:00 UTC: 5 次 (单点突发)
  - **其余 19h: 2 次**
- 最近 6h (19:00–00:00 UTC): ATE=1, 累计错误极低
- 次要错误: zombie_empty_completion=28, buffer_exhausted=10, NVStream_IncompleteRead=9, stream_absolute_cap=9 — 均为小量、非系统性

## 结论

当前 30min SR=100%、0 错误、0 429、0 fallback、5-key 全程均衡。参数处于健康稳态。

24h 的 ATE 主要集中在 NVCF **外部高峰窗口**（北京上午/中午），且 84% 集中在 00:00–08:00 UTC。这不是本机参数可消除的（NVCF 高峰限流属上游行为），下调 budget/超时反而会损害其余 19h 的干净期性能。

判定：**NOP，不改任何参数**（严格执行"正常则不改"原则，避免为单个历史窗口过度调参）。

## 当前参数快照（live, docker exec 确认）

| 参数 | 值 |
|------|----|
| UPSTREAM_TIMEOUT | 50 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 |
| TIER_COOLDOWN_S | 90 |
| KEY_COOLDOWN_S | 30 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120 |
| NVU_KEYMGR_CONN_BASE_COOLDOWN | 30 |
| NVU_KEYMGR_CONN_MAX_COOLDOWN | 60 |
| NVU_KEYMGR_CONN_FAIL_THRESHOLD | 3 |
| NVU_KEYMGR_CONN_LONG_COOLDOWN | 120 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NV_KEY_INTEGRATE_KEYS | (空，integrate 未启用) |

## 验证
- /health 正常, nvcf_pexec_models 含 dsv4f0731_nv
- 容器 Up 6 小时, 无改动

## 下一步建议
- 保持当前配置。若未来观测到 **00:00–08:00 UTC 高峰窗口** ATE 仍持续 >5次/h 且伴随 fallback，再评估是否适度提高 NVU_TIER_BUDGET_DSV4F0731_NV 或调整 MAX_COOLDOWN。
- 常规巡逻：持续跟踪 p95<30s、SR>98%、0 fallback 三个健康基线。