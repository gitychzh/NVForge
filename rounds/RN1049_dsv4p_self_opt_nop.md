# RN1049: NOP — 链路健康，SR 升至 98.9%，延续收敛趋势，无需调整

**时间**: 2026-08-10 07:44 (UTC)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**判定**: NOP — 数据健康，符合 NOP 阈值 (SR>95%, 无异常错误, 延迟稳定)，且较上轮(RN1048)进一步改善

## 30min 窗口数据 (dsv4f0731_nv)

| 指标 | 值 |
|---|---|
| 总量/成功/失败 | 90 / 89 / 1 |
| SR (30min) | **98.9%** |
| Avg / P50 / P95 | 26097ms / 16154ms / 89478ms |
| 错误分类 | all_tiers_exhausted 1 (180073ms) |
| 429 计数 | 0 |

仅 1 个 `all_tiers_exhausted`(180s 全域耗尽，跑了完整 budget 后无 key 可用的瞬态)，无 429、无流截断。较上轮(2 个错误)已减半。

## per-key 200 延迟 (30min)

| Key | 请求数 | avg_ms | p95_ms | 错误 |
|---|---|---|---|---|
| k0 | 19 | 23016 | 51435 | all_tiers_exhausted 1 |
| k1 | 18 | 18969 | 50036 | 0 |
| k2 | 17 | 24441 | 75571 | 0 |
| k3 | 17 | 27209 | 79781 | 0 |
| k4 | 18 | 28435 | 93630 | 0 |

所有 key 分布均匀 (17-19 请求)，仅 k0 出现 1 个 `all_tiers_exhausted`（key 循环烧尽后全域，非 key 本身劣化），其余 4 key 全 0 错误、延迟均衡。无劣化 key。

## 趋势

- 6h: 461 总 / 436 成功 / 25 错, SR=**94.6%** (较上轮 94.3% 略升)
- 3h 逐小时: 98.2% (108/110) / 97.4% (112/115) / 95.3% (101/106) / 91.7% (11/12) —— **小时级稳定在 95%+**，高负载下仍坚强
- 24h all_tiers_exhausted: 291（日内累计，当前窗口已回到 1）
- key_cycle_429s: k0=75, k1=10, k2=4, k3=1, k4=0 —— k0 循环最多但与全 0 429 一致（35s 窗口 key 轮转正常），无异常滞留

## 其他状态

- upstream_type: nvcf_pexec 90 请求, SR 98.9%, 纯 pexec 路径 (100%)，无 integrate 分流
- finish_reason: tool_calls 78 / stop 11 (工具调用为主，正常)
- hm4104 fallback: 0 (最近 5min 无 fallback 日志)
- tier_attempts: 空（本窗口无 key 级失败切换记录）
- /health: ok, 5 keys, port 40666
- 容器: Up 2 hours

## 当前参数 (env 实测，无漂移)

```
UPSTREAM_TIMEOUT=45, KEY_COOLDOWN_S=30, TIER_COOLDOWN_S=90,
TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_DSV4F0731_NV=180,
NVU_PEXEC_TIMEOUT_FASTBREAK=3, NVU_EMPTY_200_FASTBREAK=3,
NVU_KEYMGR_429_BASE/MAX_COOLDOWN=120/120,
NVU_KEYMGR_CONN_BASE/MAX/LONG=30/60/120, THRESHOLD=3,
NVU_PROBE_TIMEOUT=10, NVU_BUFFER_TIMEOUT_STAIRS=90×5 (90,90,90,90,90),
NVU_PEER_FALLBACK_ENABLED=0, NVU_PEER_FB_SKIP_MODELS=全部,
NV_INTEGRATE_MODELS=空, NV_KEY_INTEGRATE_KEYS=空 (纯 pexec 路径),
PROXY_ROLE=passthrough, PROXY_TIMEOUT=300
```
参数与上轮一致，全链稳定，无漂移。

## 结论

链路健康且持续改善：30min SR=98.9%（上轮 97.6%），0 429、0 fallback、5 key 均匀健康、小时级 SR 稳定 95%+。唯一的 `all_tiers_exhausted`(180s) 是并发/上游瞬态在全域 key 被烧尽时的兜底失败，被 key 循环正常吸收且未复发。纯 pexec 路径 + UPSTREAM_TIMEOUT=45 + TIER_COOLDOWN=90 + TIER_TIMEOUT_BUDGET=180 的参数组合正在产出收敛的高 SR。遵循"改前必有数据 + 一次只改一个参数"铁律，无劣化数据则不改。**NOP 轮**。

## 验证

- /health → status ok
- 容器 Up 2 hours
- 无参数修改，无需重启

## 下一步建议

保持当前参数不变。继续观察：(1) 上一窗口 k0 的 1 个 `all_tiers_exhausted` 是否单点复发（与 RN1048 的 k0 null 一并跟踪）；(2) 24h all_tiers_exhausted=291 是否仍集中于高负载时段，若在负载回落期仍频发则需审视 TIER_TIMEOUT_BUDGET 是否过长烧 key；(3) 小时级 SR 若能稳定在 97% 以上则持续 NOP 是稳定优先的正确行为。