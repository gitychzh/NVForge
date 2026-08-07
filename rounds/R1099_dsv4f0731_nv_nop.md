# R1099: dsv4f0731_nv NOP — SR=98.6%, 持续稳定

**容器**: dsvf0731_nv40666 (opc2sname, 端口 40666)
**时间窗口**: 2026-08-07 20:26-20:56 UTC (~05:26-05:56 Beijing)
**决策**: NOP — 零参数修改

## 30-min 数据

| 指标 | 值 |
|------|------|
| 总请求 | 146 |
| 成功 | 144 (98.6%) |
| 失败 | 2 (1.4%) |
| ATE | 0 |
| Fallback (hm4104) | 0 |
| 429 计数 (30min) | 0 |
| Avg/P50/P95/P99 | 11,068 / 9,137 / 26,002 / 38,957ms |
| upstream | 100% nvcf_pexec |
| finish_reason | tool_calls=116, stop=28 |

## 错误分类 (30min)

| error_type | cnt | avg_ms | key |
|------------|-----|--------|-----|
| NVStream_IncompleteRead | 1 | 36,379 | k2 |
| zombie_empty_completion | 1 | 38,524 | k4 |

## Per-key 延迟 (30min)

| Key | 200 count | 200 avg | 200 p95 | 错误 |
|-----|-----------|---------|---------|------|
| k0 | 30 | 12,345 | 25,279 | — |
| k1 | 29 | 7,777 | 17,614 | — |
| k2 | 30 | 11,807 | 21,898 | 1 IncompleteRead (36,379) |
| k3 | 27 | 9,771 | 17,380 | — |
| k4 | 28 | 11,682 | 24,492 | 1 zombie (38,524) |

## 6h / 3h 趋势

- **6h**: 1,824 req, 1,789 success (98.1%), 35 fail, 0 ATE
- **3h 逐小时**:
  - 09:00 UTC: 32/32/0/0 — SR=100%, avg=8,700ms
  - 10:00 UTC: 322/318/4/0 — SR=98.8%, avg=10,680ms
  - 11:00 UTC: 323/318/5/0 — SR=98.5%, avg=11,023ms
  - 12:00 UTC: 281/278/3/0 — SR=98.9%, avg=10,779ms
- **24h ATE**: 238 (~10/hr)

## 决策理由

1. **SR=98.6% (30min), 98.1% (6h)** — 远高于 95% 阈值，持续稳定
2. **0 fallback, 0 ATE, 0 429** — 无降级信号
3. **2 个错误均为 transient**:
   - 各分散在不同 key，无集中模式
   - 均在 36-38s 区间，NVCF 上游偶发截断
4. **Per-key 负载均衡**: 5 个 key 均分请求 (27-30 each)，延迟方差正常
5. **key_cycle_429s**: k0=38, k1=108 — 实际上 429 计数为 0，key_cycle_429s 仅为自容器启动累计的轮转次数
6. **100% nvcf_pexec** — 所有请求走 pexec，无 integrate 流量，工作正常

## 后续关注点

- 两轮 30min 对比（R1098: SR=97.8%, R1099: SR=98.6%），趋势略上升
- 若 SR 持续 >98%，可以考虑缩小 TIER_TIMEOUT_BUDGET_S 从 180→150 以缩短 ATE 恢复时间
- zombie_empty_completion 无 key 集中 → 当前 EMPTY_200_FASTBREAK=3 合适
- 24h ATE=238，仍属正常范围（~10/hr），无需调整 fast-break 或 budget