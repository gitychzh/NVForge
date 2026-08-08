# RN1050: NOP — 链路持续健康 (SR 100%)，无参数调整

**时间**: 2026-08-08 09:16 (UTC)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**判定**: NOP — SR>95%, 0 错误, 0 429, 0 fallback, 5 key 均匀, 延迟稳定

## 30min 窗口数据 (dsv4f0731_nv)

| 指标 | 值 |
|---|---|
| 总量/成功/超时/错误 | 111 / 111 / 0 / 0 |
| SR | **100%** |
| Avg / P50 / P95 / max | 16086ms / 12262ms / 35168ms / 80539ms |
| 错误分类 | 无 (表为空) |
| 429 计数 | 0 |

## per-key 200 延迟 (30min)

| Key | 请求数 | avg_ms | max_ms | 错误 |
|---|---|---|---|---|
| k0 | 21 | 13489 | 29856 | 0 |
| k1 | 20 | 12190 | 28774 | 0 |
| k2 | 22 | 19549 | 40219 | 0 |
| k3 | 24 | 17161 | 34779 | 0 |
| k4 | 24 | 17356 | 62902 | 0 |

5 key 负载基本均匀 (20-24 请求/key)，per-key 错误全 0。延迟总体均匀 (12.2-19.5s avg)。
k4 max 62902ms 为长尾推理请求，与 k2/k3 的 max 同属推理型方差，零错误伴随 → 健康方差而非链路劣化。
进一步看，per-key avg 的标准差较小，无单 key 劣化。

## 趋势

- **6h: 1969 总 / 1966 成功 / 3 错误 → SR=99.85%**, 0 429
- 3h 逐小时: 01:00=60/60(100%), 00:00=310/310(100%), 23:00=316/316(100%),
  22:00=165/162(98.2%, 3 错误 为 >2h 前残留) → **最近 3 个整点小时全 100%**
- 24h all_tiers_exhausted: 43 (低频，24h 内可忽略)

## 其他状态

- upstream_type: **nvcf_pexec 111/111 全部成功 (100%)**，integrate 0 (纯 pexec 路径)
- finish_reason: tool_calls 85 / stop 26 (正常工具调用型负载)
- tier_attempts (30min): 空 — 所有请求首 key 即成功, 未触发 key 切换/重试
- hm4104 fallback: 0 (近 5min 无 fallback 日志)
- /health: status ok, proxy_role passthrough, 5 keys, port 40666, dsv4f0731_nv 在 nvcf_pexec_models
- 容器: dsvf0731_nv40666 Up 7 hours

## 当前参数 (env 实测，无漂移)

```
UPSTREAM_TIMEOUT=50, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120,
NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120, THRESHOLD=3,
NVU_PROBE_TIMEOUT=10, NVU_BUFFER_TIMEOUT_STAIRS=90×5,
NV_INTEGRATE_MODELS=空 (纯 pexec 路径), NV_INTEGRATE_PROXY_URLS / EGRESS_IPS 配置中
```

与 RN1049 完全一致，无漂移。

## 结论

链路完全健康且维持高度稳定：30min SR=100% (111/111)，6h SR=99.85% (1966/1969)，
最近 3 个整点小时全 100%，0 错误 / 0 429 / 0 fallback / tier_attempts 空，5 key 负载与延迟
完全均匀，upstream 全 pexec 100% 成功。整体 P95 35168ms 与 RN1049 (32309ms) 相当或在同一
量级，P50 12262ms 与 RN1049 的 9678ms 属正常上下波动，延迟未恶化。key_cycle_429s 的计数 (k0=40,
k1=70, k2=1) 为累积累计值非本轮 429 错误，当前窗口 429=0。遵循"改前必有数据 + 一次只改一个参数"
铁律，无任何持续劣化数据可归因于参数，改动只会引入风险。**NOP 轮**。

## 验证

- /health → status ok (proxy_role passthrough, 5 keys, port 40666, dsv4f0731_nv 在列表)
- env 实测与配置一致，无参数修改，无需重启
- 容器 Up 7 hours，状态正常

## 下一步建议

1. **维持现状**: 纯 pexec 路径 + UPSTREAM_TIMEOUT=50 + TIER_COOLDOWN=90 + TIER_BUDGET=180
   持续产出 100% SR 为理想稳态，不改任何参数。
2. **关注 P95/P99 长尾**: 若整体 P95 持续 >70s 或某 key p95 连续多轮 >45s 且伴随错误，
   才考虑扩展 TIER_TIMEOUT_BUDGET 或检查该 key 的 SOCKS5 代理质量。本轮 P95 35168ms 健康。
3. **若 6h SR 跌破 98% 或 30min 内任一 error_type 持续 >3**: 才开始考虑 UPSTREAM_TIMEOUT
   / key 冷却微调；当前无触发。