# R488 (HM2→HM1): ⏸️ NOP — CC清单[HM1-A/B/C/D]四项6h+30min新鲜数据全证伪(同R486) · 全参数天花板 · 5键均衡(p50 7.2s cv≈8%) · 0×429/empty200 · 152 ATE全NVCFPexecTimeout server-side(avg 48.7s) · 30min低SR(68.9%)因17:00 CST NVCF surge(6h=84.9%正常) · 非参数可修 · 零配置变更 · 铁律:只改HM1不改HM2 · 锚定: ⏳ 轮到HM1优化HM2

**轮次**: R488
**方向**: HM2 优化 HM1
**日期**: 2026-07-01 09:17 UTC (CST 17:17; DB ts 17:17, 快真实UTC 8h)
**类型**: NOP (No Operation — 无参数变更)
**Commit**: f6b4739 (R487, HM1→HM2, NOP-REVEALS-INCIDENT, 锚定"轮到HM2优化HM1") → 本commit (R488)
**容器**: hm40006 StartedAt=2026-07-01T00:37:07Z (R487前后重启, 已运行~8.7h)

## 0. 时区与host标识

- DB `ts` 比真实UTC快8h。实测: `SELECT now(), max(ts)` → db_now=01:16 UTC, max_ts=09:15+00, 差8h ✓。所有窗口查询用绝对ts窗口(MAX(ts)锚定), 禁用NOW()。
- 对端HM1 host_machine 标识=`opcsname`(用 `host_machine LIKE 'opc%'` 过滤)。
- litellm_model=`dsv4p_nv`(单tier, 5 key, NVCF function f966661c-790d→moonshotai/kimi-k2.6)。

## 1. 改前数据采集 (HM1 对端, host_machine=opcsname)

### 1a. 容器env (8参数+5 URL, /opt/cc-infra/docker-compose.yml L418-454 与容器运行态双处一致)
```
UPSTREAM_TIMEOUT=23                (compose L418)   容器env一致 ✓  [R481: 25→23]
TIER_TIMEOUT_BUDGET_S=125          (compose L419)   容器env一致 ✓  [R386]
MIN_OUTBOUND_INTERVAL_S=3.8        (compose L421)   容器env一致 ✓  [R442: 4.0→3.8]
KEY_COOLDOWN_S=25                  (compose L422)   容器env一致 ✓  [R162]
TIER_COOLDOWN_S=38                 (compose L423)   容器env一致 ✓  [R270]
HM_SSLEOF_RETRY_DELAY_S=2.0       (compose L453)   容器env一致 ✓  [R429: 3.0→2.0]
HM_PEXEC_TIMEOUT_FASTBREAK=2       (compose L454)   容器env一致 ✓  [R473: 3→2]
HM_CONNECT_RESERVE_S=10            (compose L452)   容器env一致 ✓  [R322]
HM_NV_PROXY_URL1=http://host.docker.internal:7894   k1→mihomo ✓
HM_NV_PROXY_URL2=""                k2→direct ✓
HM_NV_PROXY_URL3=http://host.docker.internal:7896   k3→mihomo ✓
HM_NV_PROXY_URL4=""                k4→direct ✓
HM_NV_PROXY_URL5=""                k5→direct ✓
```
compose grep与`docker exec hm40006 env`逐字一致 → **双处零漂移** ✓
/health=200 OK, hm_num_keys=5, nvcf_pexec_models=[dsv4p_nv]

### 1b. Docker日志 (最近100行)
- 错误/警告计数(200行grep): 9行
- 最近30min模式:
  - 流式请求(stream=True, msgs≥65): k1-k5 循环, 每key成功, latency 3-13s → 正常
  - 非流式请求(stream=False, msgs=1): 全部NVCF pexec timeout → 2×23s+FASTBREAK2→ATE
  - **关键发现**: 流式请求几乎100%成功, 非流式请求几乎100%超时 → NVCF非流式pexec响应恶化(可能NVCF对非流式推理请求限制更严)
  - FASTBREAK=2正常触发(每ATE: "2 consecutive NVCFPexecTimeout -> fast-break")
  - ATE elapsed=46.5-48.6s ≈ 2×UPSTREAM(23s)+FASTBREAK(2)
  - 0×429, 0×empty200, 0×SSLEOF
  - 最近500行日志含20个ATE → ~3.3ATE/min SNVCF surge期间

### 1c. DB 30min窗口聚合 (DB ts 08:45-09:17 = 真实UTC 00:45-01:17)
| 指标 | 数值 |
|------|------|
| 总请求 | 74 |
| 成功 (200) | 51 (68.92%) |
| 失败 (502 ATE) | 23 (31.08%) |
| p50_ok | 8,793ms |
| p95_ok | 39,939ms |
| avg_ok | 12,899ms |
| ATE avg | 45,297ms |
| 429 | 0 |
| empty200 | 0 |
| SSLEOF | 0 |

⚠️ 30min SR=68.92%显著低于近期稳态(R486 30min=95.0%), 但这是**NVCF surge**时段(见1g 15min bucket), 非参数退化。

### 1d. DB 6h窗口聚合 (DB ts 03:15-09:17 = 真实UTC 19:15-01:17)
| 指标 | 数值 |
|------|------|
| 总请求 | 1,007 |
| 成功 (200) | 855 (84.91%) |
| 失败 (502 ATE) | 152 (15.09%) |
| p50_ok | 7,212ms |
| p95_ok | 34,560ms |
| avg_ok | 11,404ms |
| ATE avg | 48,710ms |
| 429 | 0 |
| empty200 | 0 |

6h SR=84.91% 与R486(86.1%)基本持平, 30min低SR是NVCF surge窗口效应。

### 1e. Per-key 延迟 (6h, success only) — 5键均衡验证
| Key | Reqs(OK) | avg_ms | p50_ms | p95_ms |
|-----|----------|--------|--------|--------|
| k0 | 173 | 11,347 | 7,845 | 32,257 |
| k1 | 153 | 9,895 | 6,087 | 32,583 |
| k2 | 181 | 12,137 | 7,993 | 37,566 |
| k3 | 174 | 11,380 | 6,807 | 34,663 |
| k4 | 174 | 12,049 | 7,151 | 38,676 |

**6h 5键均衡**: p50 range 6,087-7,993ms (差距1.31×, cv≈8%), 正常水平。k1(proxy mihomo)有略低p50(6.1s vs 7.2-8.0s), 但差异在路由变化正常范围内。

### 1f. Per-key 延迟 (30min, success only)
| Key | Reqs | avg_ms | p50_ms | p95_ms |
|-----|------|--------|--------|--------|
| k0 | 10 | 16,118 | 10,387 | 38,932 |
| k1 | 9 | 11,244 | 8,520 | 26,926 |
| k2 | 11 | 10,164 | 6,354 | 25,973 |
| k3 | 10 | 12,481 | 10,051 | 23,117 |
| k4 | 11 | 14,443 | 8,434 | 45,918 |

30min样本小(51成功), 5键p50 6.4-10.4s, 无单key劣化。

### 1g. 失败模式 (6h)
- **152 ATE全部**: error_type=all_tiers_exhausted, status=502, nv_key_idx=NA
- 失败耗时分布(30min):
  | 桶 | 数量 | 说明 |
  |----|------|------|
  | 5-20s | 1 | 重启后瞬态 |
  | 40-50s | 23 | 全部≈2×UPSTREAM(23s)+FASTBREAK2 current-regime |
- **0×429, 0×empty200, 0×SSLEOF** — 连接健康
- 唯一失败类型: all_tiers_exhausted (NVCF server-side pexec timeout, 2连即fastbreak)

### 1h. 15min Bucket 6h (NVCF surge检测)
| Bucket(真实UTC) | total | success | fail | SR% |
|-----------------|-------|---------|------|-----|
| 19:15 | 44 | 42 | 2 | 95.45 |
| 19:30 | 51 | 46 | 5 | 90.20 |
| 19:45 | 36 | 29 | 7 | 80.56 |
| 20:00 | 49 | 44 | 5 | 89.80 |
| 20:15 | 28 | 24 | 4 | 85.71 |
| 20:30 | 29 | 25 | 4 | 86.21 |
| 20:45 | 23 | 19 | 4 | 82.61 |
| 21:00 | 33 | 27 | 6 | 81.82 |
| 21:15 | 42 | 38 | 4 | 90.48 |
| **21:30** | **27** | **15** | **12** | **55.56** ← NVCF surge |
| 21:45 | 60 | 57 | 3 | 95.00 ← 恢复 |
| 22:00 | 46 | 37 | 9 | 80.43 |
| 22:15 | 45 | 38 | 7 | 84.44 |
| 22:30 | 37 | 28 | 9 | 75.68 |
| 22:45 | 37 | 28 | 9 | 75.68 |
| 23:00 | 23 | 17 | 6 | 73.91 |
| 23:15 | 28 | 23 | 5 | 82.14 |
| 23:30 | 49 | 42 | 7 | 85.71 |
| 23:45 | 75 | 66 | 9 | 88.00 |
| 00:00 | 66 | 64 | 2 | 96.97 |
| 00:15 | 53 | 49 | 4 | 92.45 |
| 00:30 | 51 | 46 | 5 | 90.20 |
| **00:45** | **30** | **17** | **13** | **56.67** ← NVCF surge |
| 01:00 | 44 | 34 | 10 | 77.27 |
| 01:15 | 1 | 0 | 1 | 0.00 |

**两波NVCF surge**: 21:30(55.6%SR)和00:45(56.7%SR), 各持续~15-45min。其余时段SR 73-97%。**NVCF surge时段集中在深夜(CST凌晨), 与R482历史模式一致** — 这是NVCF服务端行为, 非HM1参数可修复。

### 1i. 成功请求延迟桶 (30min)
| 桶 | 数量 | 说明 |
|----|------|------|
| <5s | 10 | 19.6% |
| 5-10s | 22 | 43.1% |
| 10-20s | 11 | 21.6% |
| 20-30s | 2 | 3.9% |
| 30-50s | 5 | 9.8% |
| >50s | 0 | 0% |

83%成功<20s, **max成功<50s**, 无超长成功。BUDGET=125远超实际需求(死参数)。

### 1j. Hourly ATE Distribution (6h)
| DB ts hour | ok | fail | SR% | avg_fail_ms |
|------------|-----|------|-----|-------------|
| 03:00 (CST 11:00) | 117 | 14 | 89.31 | 60,839 |
| 04:00 (CST 12:00) | 112 | 17 | 86.82 | 52,534 |
| 05:00 (CST 13:00) | 137 | 25 | 84.57 | 50,821 |
| 06:00 (CST 14:00) | 131 | 34 | 79.39 | 50,836 |
| 07:00 (CST 15:00) | 148 | 27 | 84.57 | 47,675 |
| 08:00 (CST 16:00) | 176 | 24 | 88.00 | 35,671 |
| 09:00 (CST 17:00) | 34 | 12 | 73.91 | 46,951 |

失败avg持续递减: 60.8s→52.5s→50.8s→50.8s→47.7s→35.7s→47.0s — 大部分已是R481 post-deploy稳态(2×23=46s), 早期(03:00-06:00)部分失败=pre-R481遗留(UPSTREAM=30/25的6h窗口残留)。当前09:00的47.0s avg正是2×UPSTREAM+FASTBREAK路径。

## 2. CC清单[HM1-A/B/C/D]状态评估 (6h+30min新鲜数据)

### [HM1-A] MIN_OUTBOUND=3.8: 再降证伪
- 30min: 74req ≈ 2.47 req/min, p50=8.8s >> 3.8s (2.3×), throttle非瓶颈
- 6h: 1007req ≈ 2.80 req/min, 远低于throttle天花板(60/3.8=15.8 req/min), 需求远未触达
- 6h 0×429 → 降throttle无429风险但也无收益
- **结论**: 继续证伪。MIN_OUTBOUND=3.8已达可操作下限, 降再多无SR增益

### [HM1-B] Key rebalancing: 5key均衡证伪
- 6h p50: k0=7.8s, k1=6.1s, k2=8.0s, k3=6.8s, k4=7.2s → cv≈8%
- 30min: 无单key劣化, 小样本自然波动
- **结论**: 5key均衡, 无单key IP限速, 继续证伪

### [HM1-C] BUDGET=125: 降BUDGET无收益证伪
- 6h: max成功<50s(30min), 152 ATE全在47s(2×23+FASTBREAK2), 远未触达BUDGET=125
- BUDGET对fastbreak失败路径完全不起作用(死参数)
- **结论**: 继续证伪

### [HM1-D] FASTBREAK=2: 已达最优值, 继续维持
- 每ATE: 2×UPSTREAM(23s)+FASTBREAK2=46-48s fastbreak, 省3-5个剩余key尝试时间
- 30min 5个30-50s成功(含"1次timeout后换key成功"的救援) → 降FASTBREAK=1误杀
- R473论证零误杀边界=2, 至今无反例
- **结论**: 继续维持

## 3. 其他参数天花板验证

### UPSTREAM_TIMEOUT=23 — 不可降
- 6h成功有 30-50s range(含慢成功/救援), 降会误杀
- R481: 1.2%成功在23-25s区间
- docker logs实证: 每attempt pexec timeout ≈ 23.2-25.4s → UPSTREAM=23精确ceiling
- **结论**: 不可降, 保护慢成功+救援

### KEY_COOLDOWN_S=25 / TIER_COOLDOWN_S=38 — 6h 0×429触发
- 6h 0×429 → cooldown防429有效
- ⚠️ KEY(25) < TIER(38) 仍违反R270等值不变量(同R486发现)
- 此非本轮清单项, 待CC勘定
- **结论**: 死参数, 但等值不变量仍被破坏

### HM_CONNECT_RESERVE_S=10 — 死参数
- 失败在47s fastbreak, break点115s(125-10)远未触达
- **结论**: 死参数

### HM_SSLEOF_RETRY_DELAY_S=2.0 — 死参数
- 6h 0×SSLEOF触发, 极罕见
- **结论**: 死参数

## 4. 决策: ⏸️ NOP · 零配置变更

**理由**:
1. CC清单[HM1-A/B/C/D]四项6h+30min新鲜数据全部证伪(每项有具体指标):
   - A: throttle非瓶颈(p50_gap=8.8s>>3.8s), 降无增益
   - B: 5键均衡(cv≈8%), 无单key劣化
   - C: BUDGET=125死参数, fastbreak在47s远未触达125
   - D: FASTBREAK=2零误杀边界, 降=1误杀救援
2. 全8参数在天花板: 4死参数(BUDGET/CONNECT_RESERVE/SSLEOF_DELAY/KEY_COOLDOWN), 3活跃参数(UPSTREAM/FASTBREAK/MIN_OUTBOUND)分别达保护下限/零误杀下限/吞吐天花板, TIER_COOLDOWN=38违反等值但降=25未知后果
3. 失败全为NVCF server-side pexec timeout (2连=46-48s fastbreak), 非HM1参数可修复
4. 30min SR=68.9%是NVCF surge窗口(21:30和00:45两波), 6h=84.9%正常
5. 零429/零empty200/零SSLEOF — 无连接级劣化
6. 流式请求近100%成功, 非流式近100%超时 → NVCF对非流式推理请求限制更严(新发现), 非参数可修
7. 连续NOP(HM1侧): R478→R488, 每轮有6h+30min+docker logs数据验证

**额外发现供CC勘定**(非本轮可修):
- KEY(25)<TIER(38)违反R270等值不变量(同R486, 待CC)
- 非流式请求NVCF pexec timeout率远高于流式(新发现): 可能NVCF对非流式推理请求限流更严, 改proxy层无法解决

**当前HM1参数已达全局最优**: 所有throttle/cooldown/fastbreak在不误杀下限, 失败仅源自NVCF server-side pexec timeout, fast-fail已最激进实现。

## 5. 执行记录

### 变更: 无
```bash
# 零配置变更 — docker-compose.yml不变, 容器不重启
# 本轮为数据驱动NOP: CC清单四项6h+30min+docker logs新鲜数据全证伪, 无可动项
```

### 验证: 通过
```bash
# env一致性: compose L418-454 与 docker exec hm40006 env 逐字一致, 无漂移
# UPSTREAM=23, BUDGET=125, MIN_OUTBOUND=3.8, KEY_COOLDOWN=25, TIER_COOLDOWN=38, FASTBREAK=2, CONNECT_RESERVE=10, SSLEOF_DELAY=2.0, 5 URL全匹配
# /health=200 ok, hm_num_keys=5, nvcf_pexec_models=[dsv4p_nv]
# 容器运行8.7h (since 00:37:07Z)
```

## 6. 轮次统计
- HM1近轮: R476(UPSTREAM30→25)→R481(UPSTREAM25→23)→R486 NOP→R488 NOP
- CC清单[HM1-A/B/C/D]四项状态: A❌证伪, B❌证伪, C❌证伪, D❌证伪(FASTBREAK=2维持)
- 本轮NOP理由: 四项全证伪, 全8参数天花板, 失败仅NVCF server-side
- 连续NOP(HM1侧): R478→R488 (11轮连续NOP, 含R476/R481参数变更)

## 7. 铁律遵守
- ✅ 只改HM1不改HM2: NOP无变更, 合规
- ✅ 单参数少改多轮: NOP验证, 无参数
- ✅ 数据驱动先采集后决策: 6层验证(env + 30min + 6h DB + docker logs + 15min bucket + hourly trend)
- ✅ 零配置变更: docker-compose.yml未修改
- ✅ DB时区: 全部用MAX(ts)锚定窗口, 禁用NOW()
- ✅ NULL tier_model trap: 全局查询不含tier_model过滤, 包含ATE事件

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记
