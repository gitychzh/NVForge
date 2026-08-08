# RN1051: NOP — 链路持续健康 (SR 100%)，无参数调整

**时间**: 2026-08-08 09:28 (UTC)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**判定**: NOP — SR>95%, 0 错误, 0 429, 0 fallback, 5 key 均匀, 延迟稳定

## 30min 窗口数据 (dsv4f0731_nv)

| 指标 | 值 |
|---|---|
| 总量/成功/超时/错误 | 99 / 99 / 0 / 0 |
| SR | **100%** |
| Avg / P50 / P95 / max | 15605ms / 12519ms / 35674ms / 65944ms |
| 错误分类 | 无 (表为空) |

## per-key 200 延迟 (30min)

| Key | 请求数 | avg_ms | max_ms | 错误 |
|---|---|---|---|---|
| k0 | 17 | 15443 | 36078 | 0 |
| k1 | 22 | 17691 | 47810 | 0 |
| k2 | 19 | 18679 | 37921 | 0 |
| k3 | 21 | 16515 | 35207 | 0 |
| k4 | 20 | 9571 | 22370 | 0 |

5 key 负载基本均匀 (17-22 请求/key)，per-key 错误全 0。延迟总体均匀 (9.6-18.7s avg)；k4 明显最快
(avg 9571ms, max 22370ms)，与 RN1050 中 k4 max 62902ms 不同——本轮 k4 无长尾，属正常波动非劣化。
无单 key 持续劣化。

## 趋势

- **6h: 1952 总 / 1949 成功 / 3 错误 → SR=99.85%**, 0 429
- 3h 逐小时: 01:00=96/96(100%), 00:00=310/310(100%), 23:00=316/316(100%),
  22:00=110/107(97.3%, 3 错误 为 >1.5h 前残留) → **最近 3 个整点小时全 100%**
- 24h all_tiers_exhausted: 42 (预脚本读取)；但按 nv_tier_attempts 逐小时明细查询，**最近 24h 内
  all_tiers_exhausted = 0 行** → 该 42 为跨多轮累积的陈旧/其它口径计数，非近期事件，可忽略。

## 其他状态

- upstream_type: **nvcf_pexec 99/99 全部成功 (100%)**，integrate 0 (纯 pexec 路径)
- finish_reason: tool_calls 68 / stop 31 (正常工具调用型负载)
- tier_attempts (30min): 空 — 所有请求首 key 即成功, 未触发 key 切换/重试
- key_cycle_429s: k0=48, k1=51 (累积累计值，非本轮 429 错误；当前窗口 429=0)
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
NVU_PROBE_TIMEOUT=10, NVU_BUFFER_TIMEOUT_STAIRS=90×5, NVU_BUFFER_DEADLINE=450,
NV_INTEGRATE_MODELS=空 (纯 pexec 路径), NV_INTEGRATE_PROXY_URLS / EGRESS_IPS 配置中
```

与 RN1050 完全一致，无漂移。

## 结论

链路完全健康且维持高度稳定：30min SR=100% (99/99)，6h SR=99.85% (1949/1952)，
最近 3 个整点小时全 100%，0 错误 / 0 429 / 0 fallback / tier_attempts 空，5 key 负载与延迟
完全均匀（无单 key 劣化），upstream 全 pexec 100% 成功。整体 P95 35674ms 与 RN1050 (35168ms)
同量级，P50 12519ms 与 RN1050 (12262ms) 高度一致，延迟稳定。24h ATE 计数 42 经明细查询确认为
陈旧计数（24h 内=0）。遵循"改前必有数据 + 一次只改一个参数"铁律，无任何持续劣化数据可归因于
参数，改动只会引入风险。**NOP 轮**。

## 验证

- /health → status ok (proxy_role passthrough, 5 keys, port 40666, dsv4f0731_nv 在列表)
- env 实测与配置一致，无参数修改，无需重启
- 容器 Up 7 hours，状态正常

## 下一步建议

1. **维持现状**: 纯 pexec 路径 + UPSTREAM_TIMEOUT=50 + TIER_COOLDOWN=90 + TIER_BUDGET=180
   持续产出 100% SR 为理想稳态，不改任何参数。
2. **关注 P95/P99 长尾**: 若整体 P95 持续 >70s 或某 key 连续多轮 p95 >45s 且伴随错误，
   才考虑扩展 TIER_TIMEOUT_BUDGET 或检查该 key 的 SOCKS5 代理质量。本轮 P95 35674ms 健康。
3. **定期复核 24h ATE 计数口径**: 确认 all_tiers_exhausted=42 为陈旧累积，未来若 30min/6h
   窗口内 ATE 开始增长，才视为真实信号并排查 budget/冷却。
4. **将 k4 的稳定低延迟 (avg≈9.6s) 纳入观察**: 若 k4 持续显著快于其它 key，可作为未来
   key 权重/integrate 分配的参考数据，但当前无修改必要。