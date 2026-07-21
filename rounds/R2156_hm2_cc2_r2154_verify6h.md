# R2156 (hm2_cc2): R2154 cc4101 动态 header timeout 持续验证轮 (2h07min 窗口)

> 巡检轮, 0 改动 0 restart. 接 R2155 (commit 5c3b413) 继续盯 R2154 6 档表 6h 全窗口验证.
> 轮号基线: git log 最新 = 5c3b413 R2155. 本轮 = R2156.

## 改前数据 (2026-07-21 ~15:36 CST = 07:36Z)

### nv_gw 30min 窗口 (SR + 错误分类)
| status | count |
|--------|-------|
| 200 | 72 |
| 502 | 10 |

SR = 72/82 = **87.8%** (-2.2pp vs R2155 90.0%, 仍在 85-91% 次稳态带).

非成功 (502×10) error_type:
| error_type | count |
|-------------|-------|
| all_tiers_exhausted | 6 |
| NVAnth_IncompleteRead | 2 |
| zombie_empty_completion | 2 |

全 NVCF 上游类 (5 key 全 429 / IncompleteRead / zombie), **无 cc4101 75s 误杀成分**.

### nv_tier_attempts 30min
| error_type | count |
|-------------|-------|
| pexec_success | 62 |
| pexec_429 | 12 |
| pexec_conn_RemoteDisconnected | 10 |
| pexec_SSLEOFError | 3 |
| pexec_empty_200 | 1 |

pexec_429 + conn_RemoteDisconnected + SSLEOFError 全 NVCF 侧上游抖动, 非 nv_gw 旋钮可修.

### cc4101 30min (fallback / breaker / 误杀类)
- FALLBACK = **0** (30min 纯窗口)
- PRIMARY-FAIL = **0**
- 75s timeout = **0**
- SKIP-CIRCUIT = **0**
- BREAKER = **0**

### R2154 后纯窗口 (05:28:52Z 起, 现 07:36Z = **2h07min**, 距 6h 全窗口还差 ~3h53min)
- **75s_timeout = 0** (旧误杀类持续归零 ✅, R2154 6 档表持续生效)
- FALLBACK = 2 (全 120s 档 NVCF header/ttfb timeout, 被 ms_gw 兜住, **0 真中断**)
  - 14:48:07 PRIMARY-FAIL glm5_2_nv timeout 120101ms → ms_gw FALLBACK-OK 4772ms
  - 14:56:56 PRIMARY-FAIL glm5_2_nv timeout 120107ms → ms_gw FALLBACK-OK 8406ms
- PRIMARY-FAIL = 4 (2 触发 fallback, 另 2 次重试自愈未 fallback)
- BREAKER = 0

### 实例未漂移确认
- cc4101 StartedAt = `2026-07-21T05:28:51Z` (R2154 restart 实例, RestartCount=0) ✅
- nv_gw StartedAt = `2026-07-21T01:44:55Z` (连续多轮未漂移, RestartCount=0) ✅
- docker ps: nv_gw Up 6h / cc4101 Up 2h / ms_gw Up 18h / logs_db Up 4d.

## 拟改 / 决策

**巡检轮, 不改代码.** 依据:
1. R2155 STATE 明确"下轮继续盯 6h 验证, 非编码".
2. nv_gw SR 87.8% 仍在次稳态带 (85-91%), fallback 30min=0, 75s 误杀类持续归零 — 符合"nv_gw 已稳"判定.
3. 错误全 NVCF 上游类 (all_tiers_exhausted / IncompleteRead / zombie), 非 nv_gw 旋钮可修, 记录不改.
4. R2154 后纯窗口 2h07min: 75s=0 / fallback=2 全 NVCF 慢非误杀 / 0 真中断 — 6h 验证进行中, 未到终点不改.

## 改动

0 改动, 0 restart, 0 .bak. 本轮纯复盘记录.

## 验证结果

| 指标 | R2155 (前轮) | R2156 (本轮) | 趋势 |
|------|---------------|---------------|------|
| nv_gw 30min SR | 90.0% (81/90) | 87.8% (72/82) | -2.2pp, 次稳态带内 |
| 75s timeout (R2154 后窗口) | 0 (1h28min) | 0 (2h07min) | 持续归零 ✅ |
| fallback (R2154 后窗口) | 2 | 2 (累计同窗口) | 全 120s 档 NVCF 慢 |
| 30min fallback | 0 | 0 | 持续 0 ✅ |
| 0 真中断 | 是 | 是 | 持续 ✅ |
| cc4101/nv_gw 实例漂移 | 否 | 否 | 持续 ✅ |

R2154 6 档表 (PRIMARY <30K=25s/30-50K=40s/50-90K=150s/90-150K=160s/150-350K=120s/>350K=120s + FALLBACK 对齐) 持续生效.

## 下轮建议 (R2157)

1. R2154 后窗口 2h07min, 离 6h 全窗口还差 ~3h53min. 下轮继续拉数据盯 75s 类是否持续 0, 120s 档 fallback 是否仍是 NVCF 慢而非误杀.
2. 重点验证 90-150K / >150K 档在大流量 + 大 input 下稳定性 (本轮 150s/160s 档仍 = 0 命中, 可能流量不够大未触发, 需更长窗口确认).
3. 若 6h 验证稳 (75s 类持续归零, fallback 持续低且全 NVCF 类), 可进 R2155+ (实际轮号 R2157+) nv_gw 动态 absolute_cap + zombie content ratio 方案 (监督者定的下一步, 撤 40007 后续).
4. all_tiers_exhausted 若抬头 (NVCF 5 key 全 429), 属上游类非旋钮可修, 记录不改.

## 铁律遵守

改前必有数据 / 改后有验证 / 聚焦 nv_gw(40006) (cc4101 适配层是 nv 链一部分) / 所有修改写入仓库 / 只改 HM2 不改 HM1 / 改 .py 必须 docker compose restart. 本轮 0 改动 0 restart, 纯复盘验证.

## nv_gw 参数快照 (本轮 2026-07-21 ~15:36 CST)
```
KEY_AUTHFAIL_COOLDOWN_S=60
KEY_COOLDOWN_S=60
MIN_OUTBOUND_INTERVAL_S=10
NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_FAIL_N=1
TIER_COOLDOWN_S=180
TIER_TIMEOUT_BUDGET_S=180
UPSTREAM_TIMEOUT=90
```
cc4101 StartedAt = 2026-07-21T05:28:51Z (R2154 restart 后, 本轮确认未漂移).
nv_gw StartedAt = 2026-07-21T01:44:55Z (连续多轮未漂移).
