# R527 (HM1→HM2): CC清单HM2-A/B/C三项证伪 — 数据采集轮(无参数改动)

**轮次**: R527
**方向**: HM1 优化 HM2 (本轮执行者=HM1, 对端=HM2, host_machine=opc2sname)
**日期**: 2026-07-02 03:48 CST
**类型**: 数据证伪轮 (对标 R524 d36e53e)
**基线commit**: aeef7d1 (R526)
**Commit**: 本commit

## 0. 轮次定位

CC定向改动清单 HM2 节有三项:
- [HM2-A] MIN_OUTBOUND_INTERVAL_S 4.5→2.5
- [HM2-B] 补采 per-key 延迟+失败结构, 看是否有像 HM1-k4 那样的劣化 key, 若有则改其路由
- [HM2-C] TIER_TIMEOUT_BUDGET_S 128→100

铁律: 本轮选第1个未完成的执行; 若前提不成立则顺延; 三项都已做完或数据证伪时为证伪轮(规则允许, 对标 R524)。

## 1. 数据采集 (SSH HM2, host_machine=opc2sname)

### 1.1 对端当前运行态配置 (docker exec hm40006 env)
```
HM_NV_PROXY_URL1=http://host.docker.internal:7894
HM_NV_PROXY_URL2=http://host.docker.internal:7894
HM_NV_PROXY_URL3=http://host.docker.internal:7895
HM_NV_PROXY_URL4=                          (direct)
HM_NV_PROXY_URL5=http://host.docker.internal:7896
HM_PEER_FALLBACK_ENABLED=1
HM_PEER_FALLBACK_TIMEOUT=65
HM_PEER_FALLBACK_URL=http://100.109.153.83:40006
MIN_OUTBOUND_INTERVAL_S=1.0                ← CC清单A前提(4.5)不成立
TIER_TIMEOUT_BUDGET_S=100                  ← CC清单C前提(128)不成立
UPSTREAM_TIMEOUT=55
HM_PEXEC_TIMEOUT_FASTBREAK=1               (R517)
HM_FORCE_STREAM_UPGRADE_TIMEOUT=55         (R521 sync)
HM_FORCE_STREAM_UPGRADE=1
```

### 1.2 compose 文件证据 (grep /opt/cc-infra/docker-compose.yml)
```
472:      MIN_OUTBOUND_INTERVAL_S: "1.0"  # R518: HM1->HM2 — 1.2->1.0 ... R386: 5.0→2.5 -2.5s MIN_OUTBOUND (CC HM2-A) ...
470:      TIER_TIMEOUT_BUDGET_S: "100"  # R504/R500: HM1→HM2 — 95→100 +5s ...
489:      HM_PEXEC_TIMEOUT_FASTBREAK: "1"  # R517: HM1→HM2 — FASTBREAK 2→1 ...
483:      HM_FORCE_STREAM_UPGRADE_TIMEOUT: "55"
```
注: compose line 228/279/422 也有 MIN_OUTBOUND_INTERVAL_S: "1.5" (其他容器段, 非hm40006). hm40006 段为 line 472 = "1.0", 与容器运行态一致 ✅ (无 R320#4 / R322#1 的 compose 不同步问题).

## 2. 60min 窗口数据 (NOW() - interval '60 minutes', UTC)

### 2.1 per-model 总览
| request_model | reqs | ok | succ% | avg_s | p50_s | p95_s | ATE | reqs_with_429 |
|---|---|---|---|---|---|---|---|---|
| kimi_nv       | 1099 | 933 | 84.9 | 24.0 | 10.3 | 97.4 | 191 | 18 |
| glm5.1_hm_nv  |  161 | 152 | 94.4 | 23.5 | 12.0 | 97.0 |   9 | 39 |
| dsv4p_nv      |  154 | 150 | 97.4 | 12.5 |  9.6 | 29.4 |   5 |  0 |
| glm5_1_nv     |   37 |  37 |100.0 | 20.8 | 16.5 | 44.7 |   0 |  2 |

### 2.2 kimi_nv per-key (60min) — CC清单B核心
| nv_key_idx | reqs | ok | succ% | avg_s | p95_s |
|---|---|---|---|---|---|
| 0 | 192 | 192 | 100.0 | 15.1 | 48.7 |
| 1 | 186 | 186 | 100.0 | 14.1 | 44.0 |
| 2 | 178 | 178 | 100.0 | 13.9 | 41.1 |
| 3 | 183 | 183 | 100.0 | 14.9 | 46.5 |
| 4 | 169 | 169 | 100.0 | 13.2 | 39.8 |
| NULL | 191 |  25 |  13.1 | 70.3 | 98.3 |

**关键**: 5 个有 idx 的 key 全部 100% 成功, avg 13-15s, p95 39-49s, **无劣化 key** (不��� HM1-k4 那样 avg28.5s/p95=72.9s/max=162.9s 的单点劣化). 5 key 的 timeout 分布均匀 (见 2.3), 是 NVCF 后端整体行为, 非某 key 被限速.

nv_key_idx=NULL 的 191 req (succ 13.1%, avg 70.3s) = FASTBREAK=1 触发后 all_tiers_exhausted 路径 (见 2.4).

### 2.3 kimi_nv per-key timeout 分布 (hm_tier_attempts, 60min)
| nv_key_idx | error_type | cnt |
|---|---|---|
| 0 | NVCFPexecTimeout | 4 |
| 1 | NVCFPexecTimeout | 4 |
| 2 | NVCFPexecTimeout | 4 |
| 3 | NVCFPexecTimeout | 1 |
| 4 | NVCFPexecTimeout | 5 |

5 key 的 pexec timeout 均匀 (4/4/4/1/5), **无单点劣化**. R517 "90min 0个1st-timeout后2nd成功" 的判断在当前仍成立: timeout 是 NVCF 后端整体慢 (thinking 请求 >55s ceiling), 试第 2 个 key 大概率也 timeout.

### 2.4 失败请求路径分析 (docker logs hm40006, --since 30m)
```
[HM-TIMEOUT] tier=kimi_nv k5 NVCF pexec timeout: attempt=55948ms total=55951ms
[HM-PEXEC-FASTBREAK] tier=kimi_nv 1 consecutive NVCFPexecTimeout -> fast-break (saved remaining keys)
[HM-TIER-FAIL] tier=kimi_nv all 5 keys failed: 429=0, empty200=0, timeout=1, other=0, elapsed=55952ms
[HM-THINKING-TIMEOUT] (kimi_nv) thinking request stream=True → extended timeout 55s
[HM-PEER-FB] local all_tiers_exhausted (model=kimi_nv), attempting peer fallback to http://100.109.153.83:40006
[HM-PEER-FB] peer fallback OK: status=200 bytes=66473 ttfb=240ms        ← 偶尔成功
[HM-PEER-FB] peer-originated request (hop=1) also all_tiers_exhausted, no further fallback, returning 502  ← 多数失败
```
- 30min 内 peer fallback 触发 ~2 次 "attempting", 其中 2 次 `peer fallback OK` (ttfb 240/258ms). peer fb 并非 0% 救回, 但救回率低 (~1.2% of 166 fail).
- 失败请求 duration 分布 (30min, status<>200):
  - 30-55s: 42 (fast-break@55s 后 peer fb)
  - 55-60s: 37
  - >90s: 87 (peer fb 耗到 budget~100s 后 502)
- 成功请求里 >=55s 有 25 个 (50-55s 15 个), 说明 NVCF 确有 >55s 才返回的请求, 但 fast-break@55s ceiling 已由 R521 sync 至 55s 对称 HM1, 进一步提升涉及 ceiling + budget 联动, 超单参数铁律.

## 3. CC清单 HM2 三项证伪

### [HM2-A] MIN_OUTBOUND_INTERVAL_S 4.5→2.5 — 证伪 (前提过时)
- CC清单假设当前 4.5s. 实测当前 = **1.0s** (容器env + compose line 472 一致).
- 历史轨迹: R386 5.0→2.5 (CC HM2-A 已执行过), R517 1.5→1.2, R518 1.2→1.0. 已远低于 CC 清单目标 2.5.
- 结论: A 的目标值 (2.5) 早已被超越 (当前 1.0), 无可执行空间. **证伪**.

### [HM2-B] 劣化 key 路由修复 — 证伪 (数据无劣化 key)
- 60min per-key 数据 (2.2): 5 key 全 100% 成功, avg 13-15s, p95 39-49s, **无 HM1-k4 式单点劣化**.
- per-key timeout 分布 (2.3): 4/4/4/1/5 均匀, 是 NVCF 后端整体行为.
- 改路由 (HM_NV_PROXY_URL4 direct→proxy) 无数据支撑: k4 (idx=3) 实测 100% 成功 avg 14.9s p95 46.5s, 非 direct 通病 (与 HM1-k4 被 NVCF 标记的情况不同).
- 结论: 无劣化 key, 改路由方向 **证伪**.

### [HM2-C] TIER_TIMEOUT_BUDGET_S 128→100 — 证伪 (前提过时)
- CC清单假设当前 128s. 实测当前 = **100s** (容器env + compose line 470 一致, R500 95→100 已执行).
- 结论: C 的目标值 (100) 已是当前值, 无可执行空间. **证伪**.

## 4. 改动

**本轮无参数改动** (证伪轮, 对标 R524). 三项 CC 清单 HM2 节全部证伪:
- A/C: 目标值已被前轮 (R386/R517/R518/R500) 超越, 前提过时.
- B: 数据采集完成, 无劣化 key, 改路由方向无数据支撑.

## 5. 验证 (证伪轮, 无改前/改后对比)

证伪轮无参数改动, 无需 A/B 对比. 本轮 60min 数据 (2.1-2.4) 即为证伪证据, 所有结论可溯源至 DB 查询 / docker logs / env grep, 符合 R320#3 可溯源要求.

## 6. 给下轮 (HM2→HM1) 的观察

1. HM2 kimi_nv 失败 (15.1%/60min) 根因 = NVCF 后端 thinking 请求 >55s ceiling 的整体性 pexec timeout, 非 key 路由问题. FASTBREAK=1 (R517) 在 peer fallback 救回率低时仍合理 (试第2 key 大概率也 timeout, 省 47s/次).
2. HM2 peer fallback 当前救回率 ~1.2% (2/166), HM_PEER_FALLBACK_TIMEOUT=65 (远高于 HM1 的 25), 跨节点 fallback 窗口充足但 HM1 端 kimi_nv 同样 57s ceiling, 两端对称性 timeout 是瓶颈.
3. 若 CC 下轮清单仍指向 HM2 的 throttle/budget/key 路由, 建议基于本轮 60min 数据重新勘定 (当前 1.0/100/无劣化key 已是最优稳态), 否则继续证伪.
4. 潜在新方向 (不在本轮 CC 清单, 仅供 CC 勘定): 失败请求 >90s 段 87 个 (peer fb 耗到 budget~100s), 若确认 peer fb 在 HM1 端 kimi_nv 必失败, 可考虑降低 HM_PEER_FALLBACK_TIMEOUT 让失败更早返回 (但 R525/R526 刚在 HM1 端做了相反方向的 +3s/+7s, 方向冲突, 需 CC 重新勘定).

## 7. 本轮结论

- 采集 HM2 60min 完整数据 (per-model/per-key/失败路径/peer fb), 证伪 CC 清单 HM2-A/B/C 三项.
- A/C 前提过时 (目标值已被前轮超越), B 数据无劣化 key.
- 铁律遵守: 未改 HM2 任何配置 (证伪轮无改动); 未触碰 HM1 本地.
- 可溯源: 所有结论附 DB 查询结果 / docker logs / env+compose grep 证据.

## ⏳ 轮到HM2优化HM1
