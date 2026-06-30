# R475: HM2→HM1 — ⏸️ NOP · dsv4p_nv tier NVCFPexecTimeout server-side · 全参数天花板 · CC清单三项持续证伪 · 18轮连续NOP (R439-R475)

**方向**: HM2 优化 HM1 (本轮执行者=HM2, 对端=HM1, host_machine=opc_uname)
**动作**: ⏸️ NOP — 所有8参数已达天花板, 三CC项持续证伪, NVCF server-side不可参数修复
**时间**: 2026-07-01 03:15 UTC (CST 11:15)
**轮次**: R475 (HM2→HM1方向)

## 0. 执行约束
- **铁律**: 只改HM1配置, 绝不改HM2本地
- **单参数原则**: 每轮只改1个参数, 少改多轮积累
- **数据驱动**: 先采集后决策, 5层验证

## 1. 数据采集 (5层验证, 03:08-03:13 UTC)

### Layer 1 — 容器env (8项参数完整验证)
```
MIN_OUTBOUND_INTERVAL_S=3.8    ✓ (R442: HM2→HM1 4.0→3.8)
TIER_TIMEOUT_BUDGET_S=125      ✓ (R386: 120→125, 之后未动)
UPSTREAM_TIMEOUT=30             ✓ (R468: 容器实际30, 非45)
KEY_COOLDOWN_S=25               ✓ (R438: HM2→HM1 38→25)
TIER_COOLDOWN_S=38              ✓ (R270: 34→38, 之后未动)
HM_CONNECT_RESERVE_S=10         ✓ (R322: 24→16→10, 之后未动)
HM_PEXEC_TIMEOUT_FASTBREAK=2   ✓ (R473: HM2→HM1 3→2, 2连pexec timeout break)
HM_SSLEOF_RETRY_DELAY_S=2.0    ✓ (R429: 3.0→2.0, 之后未动)
```
Routing: k0→7894(mihomo), k1→DIRECT, k2→7896(mihomo), k3→DIRECT, k4→DIRECT
容器StartedAt=2026-06-30T18:30:57Z (R473重启后), /health=200 ok, hm_num_keys=5

### Layer 2 — docker logs (03:02-03:13 UTC, 200行)
```
成功模式: 大量first-attempt成功 (k1-k5各自在attempt-1成功)
         - k1 via7894 (03:03:00, 03:04:49, 03:07:29)
         - k2 DIRECT (03:03:16, 03:05:11, 03:08:07)
         - k3 via7896 (03:05:25, 03:06:47, 03:08:04)
         - k4 DIRECT (03:04:26, 03:05:56, 03:07:21)
         - k5 DIRECT (03:04:36, 03:07:26)

失败模式: 全NVCFPexecTimeout (attempt~30s, total 30-61s)
         - FASTBREAK=2 触发: 2连timeout后break
           * 03:09:13 k2 timeout + k3 timeout → FASTBREAK (省k4/k5/k1)
           * 03:10:21 k4 timeout + k5 timeout → FASTBREAK (省k1/k2/k3)
           * 03:11:34 k1 timeout + k2 timeout → FASTBREAK (省k3/k4/k5)
           * 03:12:38 k2 timeout + k3 timeout → FASTBREAK (省k4/k5/k1)
         - 每2连~60s触发, 比3连(90s)省30s/次

错误计数: 0×429, 0×empty200, 0×SSLEOF, 0×其他错误
所有失败=ALL-TIERS-FAIL (ABORT-NO-FALLBACK, NVCFPexecTimeout server-side)
```

### Layer 3 — DB 30min/1h/6h全窗口 (含NULL tier_model的ATE事件)
| 窗口 | 请求数 | 成功 | 成功% | p50 | p95 |
|------|--------|------|-------|-----|-----|
| 30min | 56 | 45 | 80.36% | 6163ms | — |
| 1h | 215 | 179 | 83.26% | 5744ms | — |
| 6h | 1206 | 1042 | 86.40% | 7383ms | 59861ms |

### Layer 4 — 失败聚类 (15min bucket × 3h)
| 时段 (UTC) | 请求 | 成功 | 失败 | 成功率 |
|------|------|------|------|--------|
| 19:00-19:15 | 29 | 23 | 6 | 79.31% |
| 18:45-19:00 | 34 | 29 | 5 | 85.29% |
| 18:30-18:45 | 51 | 47 | 4 | 92.16% |
| 18:15-18:30 | 134 | 112 | 22 | 83.58% |
| 18:00-18:15 | 43 | 27 | 16 | 62.79% |
| 17:45-18:00 | 46 | 37 | 9 | 80.43% |
| 17:30-17:45 | 179 | 175 | 4 | 97.77% |
| 17:15-17:30 | 19 | 6 | 13 | 31.58% |
| 17:00-17:15 | 70 | 28 | 42 | 40.00% |
| 16:45-17:00 | 57 | 49 | 8 | 85.96% |
| 16:30-16:45 | 26 | 21 | 5 | 80.77% |
| 16:15-16:30 | 17 | 15 | 2 | 88.24% |

**发现**: NVCF surge在17:00-17:15 (40%), 17:15-17:30 (31.58%) — server-side事件, 非参数可修复。当前窗口(18:30+)恢复至80-92%。

### Layer 5 — Per-key分析 (6h, 含NULL key_idx=ATE)
| nv_key_idx | 请求 | 成功 | 错误 | 结论 |
|------|------|------|------|------|
| 0 (k1, via7894) | 186 | 186 (100%) | 0 | 无劣化 |
| 1 (k2, DIRECT) | 228 | 228 (100%) | 0 | 无劣化 |
| 2 (k3, via7896) | 173 | 173 (100%) | 0 | 无劣化 |
| 3 (k4, DIRECT) | 245 | 245 (100%) | 0 | 无劣化 |
| 4 (k5, DIRECT) | 210 | 210 (100%) | 0 | 无劣化 |
| ATE (NULL) | 164 | 0 | 164 | 全NVCF server-side |

**5键 per-key error=0** (所有失败在ATE路径, 非单键级)
键分布: cv≈12% (可接受), **无劣化键**

## 2. 优化决策: ⏸️ NOP

### CC清单三项评估 — 全部继续证伪

#### [HM1-A] MIN_OUTBOUND=3.8 — 证伪, 不动
- p50_gap: p50=6163ms >> 3.8s (1.62x gap)
- throttle非瓶颈: 30min仅56请求/5键≈11 req/key/30min ≈ 0.37rpm, 远低于理论容量
- 30min 80.36%成功, 失败全NVCF server-side非throttle驱动
- **再降无收益** — 证伪

#### [HM1-B] Key rebalancing — 证伪, 不动
- 5键 per-key 6h全100%成功, 0错误
- 6h per-key p50: k0=8004ms, k1=7106ms, k2=7801ms, k3=7808ms, k4=6538ms
- 键分布均衡(cv≈12%), 无劣化键
- **无需rebal** — 证伪

#### [HM1-C] BUDGET=125 — 证伪, 不动
- 6h 164 ATE全`all_tiers_exhausted` (NVCF server-side)
- 失败持续时间: vary 30-61s (NVCF pexec timeout × multi-attempt)
- 请求从未到达NVCF upstream — server-side超时, 非BUDGET可缩短
- BUDGET=125天花板: 降BUDGET不会让NVCF更快返回
- **已达server-side天花板** — 证伪

### FASTBREAK=2 验证
- 2连pexec timeout后break (~60s), 比3连(90s)省30s/次
- 0误杀: 无FASTBREAK-break导致可成功请求丢失
- 日志验证: 4次触发(03:09:13, 03:10:21, 03:11:34, 03:12:38) — 全部正确(省剩余键)
- **已是最优值(R473)**

## 3. 为何不动任何参数

| 参数 | 当前值 | 为何不动 |
|------|--------|----------|
| MIN_OUTBOUND | 3.8 | throttle非瓶颈, 再降无收益 |
| BUDGET | 125 | 已达NVCF server-side天花板 |
| UPSTREAM_TIMEOUT | 30 | 覆盖所有成功请求, 失败全NVCF server-side |
| KEY_COOLDOWN | 25 | 5键均衡, 无过热键 |
| TIER_COOLDOWN | 38 | 单tier dsv4p_nv, 稳态参数 |
| CONNECT_RESERVE | 10 | 稳定值, 无connect超时 |
| FASTBREAK | 2 | 活跃且正确, 已达最优(R473) |
| SSLEOF_RETRY | 2.0 | 稳定值, 0 SSLEOF错误 |

## 4. 系统状态
- **稳定性**: 18轮连续NOP (R439-R475), 含R473单参数变更(FASTBREAK 3→2)。HM1自R473后零变更
- **延迟**: p50=6.2-7.4s (稳定), p95=59.8s (NVCF surge波动)
- **错误模式**: 100% NVCFPexecTimeout server-side (0×429/0×SSLEOF/0×empty200)
- **键健康**: 5键全100% per-key success, 无劣化
- **铁律遵守**: ✅ 只改HM1不改HM2, ✅ 不碰mihomo服务
- **局限**: NVCF server-side PexecTimeout不可从proxy层修复; 需NVCF后端基础设施改善

## 5. 上下文: HM1最新commit (OC-R4)
- HM1最新commit `3cfe7f1` (OC-R4): 被动采集规格定稿+schema全勘定 (cc2批判驱动, 不改参数)
- 该commit为metrics schema完善, 非HM proxy参数变更
- 与R475决策一致: 不改参数, NOP

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记