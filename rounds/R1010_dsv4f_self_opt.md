# R1010 — NOP 巡检轮 (dsv4f0731_nv40666, 30min SR=98.6%)

> 时间: 2026-08-07 12:38 UTC (20:38 CST)
> 容器: dsvf0731_nv40666 (端口 40666, DeepSeek V4 Pro via NVCF, HM2 本机)
> 改动: 不改参数 (NOP)

## 依据 (脚本采集, 30min 窗口)

### 主指标
- **总量**: 141, **成功**: 139, **SR: 98.6%** (139/141)
- **延迟**: avg=15328ms, p50=9659ms, p95=67129ms, max=130073ms
- **错误分布**: `all_tiers_exhausted`=1 (180036ms, TIER_BUDGET=180 耗尽), `zombie_empty_completion`=1 (2958ms)
- **429 请求级**: 0

### Per-key 200 延迟 (成功)
| key | s200 | avg_ms |
|-----|------|--------|
| 0 | 29 | 18215 |
| 1 | 28 | 13509 |
| 2 | 28 | 13585 |
| 3 | 26 | 11282 |
| 4 | 28 | 14214 |

全 5 key 成功数均衡 (26-29). k0 延迟最高 (18.2s) 且承载本轮仅有的 2 个错误.

### Per-key 错误
- 仅 k0: `all_tiers_exhausted`=1, `zombie_empty_completion`=1 (其它 key 零错误)

### key_cycle_429s
- k0=11, **k1=125**, k2=5, k3=0, k4=0
- k1 在 key 轮转中频繁遇 429 (125 次), 但全部被 pool 吸收 (请求级 429=0, k1 仍交付 28 次成功) — 5-key pool 健康, 无需干预

### upstream_type
- `nvcf_pexec`: 141/139 (100% pexec, 无 integrate 路径)

### finish_reason
- tool_calls=118 (84%), stop=21 — 长推理/工具调用占比高, 解释 p95=67s 高延迟 (DeepSeek 推理正常特征)

### 趋势
- **6h**: 1587 total / 1528 success / SR=96.3%
- **逐小时**: 97.8% / 97.6% / 98.1% / 94.6% — 稳定
- **24h all_tiers_exhausted**: 391 (跨多小时摊薄, 非联级; 30min 窗口仅 1 次)

### Fallback
- hm4104 最近 5min: **无 fallback 日志** — 本容器可用性良好

## 判稳结论
- **30min SR=98.6% > 95%**, 6h SR=96.3%, 错误仅 2 次 (无系统性模式), 无 fallback
- key_cycle_429s k1=125 虽高, 但被 pool 完全吸收, 未造成任何请求级失败 → 5-key 轮转策略有效
- 延迟 avg=15.3s / p95=67s 符合 DeepSeek V4 Pro 长推理 (84% tool_calls) 特征
- **触发 NOP 规则**: 数据正常, 无可改项

## 验证
- `/health`: status=ok, 5 keys, 5 nvcf_pexec_models, port=40666 ✅
- `docker ps`: dsvf0731_nv40666 Up 19 hours ✅
- env 沿 R1009, 无漂移

## 下一步
- 持续 NOP 监控 SR + fb
- k1 的 125 次 429-cycle 若持续升高且开始影响请求级 SR (出现大量瞬时 ATE), 再评估 NVU_KEYMGR_429_MAX_COOLDOWN 或 per-key SOCKS5 代理质量
- k0 延迟偏高 (18.2s) 观察是否持续 (可能为 k0 出口路径劣化, 暂不干预)