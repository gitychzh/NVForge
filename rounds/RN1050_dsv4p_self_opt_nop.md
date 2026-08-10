# RN1050: NOP — SR 升至 100%，零错误零 fallback，纯 pexec 链路高度收敛，无需调整

**时间**: 2026-08-10 07:58 (UTC)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**判定**: NOP — 数据健康，符合 NOP 阈值 (SR>95%, 无异常错误, 延迟稳定)，且较上轮(RN1049)进一步改善至 100%

## 30min 窗口数据 (dsv4f0731_nv)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 64 / 64 / 0 |
| SR (30min) | **100%** |
| Avg / P50 / P95 | 25874ms / 19643ms / 63637ms |
| 错误分类 | (空) |
| 429 计数 | 0 |

**0 错误、0 429、0 fallback**，延续上轮收敛趋势并登顶 100%。较 RN1049 (98.9%) 进一步改善。

## per-key 200 延迟 (30min)

| Key | 请求数 | avg_ms | p95_ms | 错误 |
|---|---|---|---|---|
| k0 | 16 | 26834 | 50996 | 0 |
| k1 | 11 | 14375 | 34867 | 0 |
| k2 | 11 | 23394 | 51052 | 0 |
| k3 | 14 | 27669 | 67733 | 0 |
| k4 | 12 | 35314 | 96369 | 0 |

所有 key 全 0 错误、分布均匀 (11-16 请求)。k4 的 p95=96369 略高于其他 key，但属健康分布内的正常方差（无错误、key_cycle 正常），非劣化信号。无需要隔离的 key。

## 趋势

- 6h: 486 总 / 462 成功 / 24 错, SR=**95.1%** (较上轮 94.6% 略升)
- 3h 逐小时: 98.6% (142/144, avg 24108) / 97.4% (112/115, avg 27972) / 95.3% (101/106, avg 23606) —— **小时级稳定 95%+，逐时上升**
- 24h all_tiers_exhausted: 291（日内累计，与上轮持平，非本窗口新增问题）
- key_cycle_429s: k0=50, k1=11, k2=3 —— 与全 0 429 一致（key 轮转正常），无滞留

## 其他状态

- upstream_type: nvcf_pexec 64 请求, SR 100%, 纯 pexec 路径 (100%)，无 integrate 分流
- finish_reason: tool_calls 55 / stop 9 (工具调用为主，正常)
- hm4104 fallback: 0 (最近 5min 无 fallback 日志)
- tier_attempts: 空（本窗口无 key 级失败切换记录）
- /health: ok, 5 keys, port 40666
- 容器: Up 2 hours

## 当前参数 (env 实测，无漂移)

```
KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180,
NVU_TIER_BUDGET_DSV4F0731_NV=180, UPSTREAM_TIMEOUT=45,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120,
NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120, THRESHOLD=3,
NVU_PROBE_TIMEOUT=10, NVU_BUFFER_TIMEOUT_STAIRS=90×5 (90,90,90,90,90),
NVU_PEER_FALLBACK_ENABLED=0, NVU_PEER_FB_SKIP_MODELS=全部,
NV_INTEGRATE_MODELS=空, NV_KEY_INTEGRATE_KEYS=空 (纯 pexec),
NV_INTEGRATE_PROXY_URLS=socks5h://172.18.0.1:7897,7904,7894,7896,7895,
NV_INTEGRATE_EGRESS_IPS=134.195.101.197,...,
PROXY_ROLE=passthrough, PROXY_TIMEOUT=300
```
参数与上轮一致，全链稳定，无漂移。

## 结论

链路健康且登顶最优：30min SR=**100%**（上轮 98.9%），0 429、0 fallback、0 错误，5 key 全部健康、分布均匀。小时级 SR 稳定 95%+ 且逐时上升 (95.3%→97.4%→98.6%)。纯 pexec 路径 + UPSTREAM_TIMEOUT=45 + TIER_COOLDOWN=90 + TIER_TIMEOUT_BUDGET=180 的组合已完全收敛。遵循"改前必有数据 + 一次只改一个参数"铁律，无劣化数据则不改。**NOP 轮**。

## 验证

- /health → status ok
- 容器 Up 2 hours
- 无参数修改，无需重启

## 下一步建议

保持当前参数不变。继续观察：(1) k4 的 p95 偏高 (96369) 是否在后续窗口稳定为健康方差还是持续抬升（若 3 轮内持续领先并伴随错误再考虑 key 隔离）；(2) 24h all_tiers_exhausted=291 是否仍集中于高负载时段，若负载回落期仍频发则审视 TIER_TIMEOUT_BUDGET 是否过长烧 key；(3) 持续 NOP 是稳定优先的正确行为，仅当小时级 SR 跌破 97% 或出现新错误类型才考虑调参。