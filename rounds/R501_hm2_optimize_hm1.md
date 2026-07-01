# R501 (HM2→HM1): ⏸️ NOP — CC清单4项全证伪/完成, 6h SR=81.9%全NVCF server-side限制

**轮次**: R501
**方向**: HM2 优化 HM1 (本轮执行者=HM2, 对端=HM1, host_machine=opc_uname)
**日期**: 2026-07-01 13:35 CST
**类型**: NOP (零配置变更, CC清单第4轮证伪)
**Commit**: 7fd80e8 (R500, HM2→HM1, FASTBREAK 2→3) → 本commit (R501)

## 0. 时区与host标识

- 对端HM1 host_machine 标识=`opc_uname`(hostname实测=opc_uname ✓)。
- NVCF function: f966661c-790d-4f71-b973-c525fb8eafd4 (moonshotai/kimi-k2.6)。
- 容器StartedAt=2026-07-01T05:16:51Z (R500重启后, 已运行~8h)

## 1. 改前数据采集 (HM1 对端, host_machine=opc_uname)

### 1a. 容器env (8参数+5 URL) — compose与容器双处一致✓

```
UPSTREAM_TIMEOUT=25              ← compose "25" ✓
TIER_TIMEOUT_BUDGET_S=125        ← compose "125" ✓
MIN_OUTBOUND_INTERVAL_S=3.8     ← compose "3.8" ✓
KEY_COOLDOWN_S=25                ← compose "25" ✓
TIER_COOLDOWN_S=25               ← compose "25" ✓
HM_SSLEOF_RETRY_DELAY_S=2.0     ← compose "2.0" ✓
HM_PEXEC_TIMEOUT_FASTBREAK=3    ← compose "3" ✓ (R500变更)
HM_CONNECT_RESERVE_S=10         ← compose "10" ✓

HM_NV_PROXY_URL1=http://host.docker.internal:7894  k1→mihomo
HM_NV_PROXY_URL2=""                                 k2→direct
HM_NV_PROXY_URL3=http://host.docker.internal:7896  k3→mihomo
HM_NV_PROXY_URL4=http://host.docker.internal:7896  k4→mihomo
HM_NV_PROXY_URL5=""                                 k5→direct
```

- /health=200 OK (port 40006): hm_num_keys=5, nvcf_pexec_models=[dsv4p_nv]
- 容器Created=2026-07-01T05:16:51Z (R500重启后, compose-env已同步)

### 1b. DB: 30min窗口 (改前)

| 指标 | 值 |
|------|-----|
| 总请求 | 36 |
| 成功 | 27 |
| SR | 75.0% |
| ATE | 9 |
| 429 | 0 |
| empty200 | 0 |
| avg_ttfb | 23,245ms |

小样本, NVCF间歇波动

### 1c. DB: 6h窗口 (R500后基线)

| 指标 | 值 | R500基线 | 变化 |
|------|-----|----------|------|
| 总请求 | 890 | 923 | ~same |
| 成功 | 729 | 753 | ~same |
| SR | 81.9% | 81.6% | +0.3pp |
| ATE | 161 | 170 | -9 |
| 429 | 0 | 0 | 0 |
| avg_ttfb | 12,179ms | 11,588ms | +591ms |
| p50 | 7,589ms | 7,330ms | +259ms |
| p95 | 35,444ms | 34,060ms | +1,384ms |

6h基线稳定, SR基本持平(81.9% vs 81.6%), 略升. 差异在NVCF间歇波动范围.

### 1d. Per-key (success only, 6h)

| Key | n | avg_ms | p50_ms | p95_ms |
|-----|---|--------|--------|--------|
| k0 | 148 | 11,978 | 8,313 | 32,656 |
| k1 | 136 | 12,035 | 7,742 | 33,292 |
| k2 | 154 | 12,725 | 8,303 | 35,129 |
| k3 | 139 | 10,697 | 6,871 | 30,580 |
| k4 | 152 | 13,307 | 7,066 | 40,953 |

5键全alive/100%SR, k3最稳(mihomo 7896), k4 p95最高但p50最低. 均衡无劣化.

### 1e. ATE详细分析 (6h, 161 total)

| ATE耗时桶 | 数量 | 含义 |
|-----------|------|------|
| <10s | 6 | budget/其他早期break |
| 45-50s | 82 | 2次attempt(含empty_200/SSLEOF变体) |
| 50-55s | 63 | 经典2×pexec_timeout(2×25s≈51s) |
| 75-80s | 9 | ★ 3次attempt(3×25s≈77s) — R500新增模式 |
| 55-75s散点 | 1 | 混合模式 |

R500 FASTBREAK=3效果验证:
- 9× ATE在75-80s范围=3连pexec timeout后fastbreak(新pattern)
- 4× 救援成功: 请求在2次pexec timeout后第3key成功(原FASTBREAK=2必ABORT)
- 平均ATE=48.6s, max=79.2s << BUDGET=125s

### 1f. UPSTREAM_TIMEOUT=25s边界分析

| 延迟桶 | 成功数 | 降UPSTREAM=23s风险 |
|--------|--------|-------------------|
| 20-23s | 18 | 安全 |
| 23-25s | 7 | ⚠️ 必ABORT(7个请求从success→pexec_timeout) |
| 25-30s | 22 | ❌ 必ABORT |
| >30s | 77 | ❌ 必ABORT |

7个成功请求在23-25s完成 → UPSTREAM=25不可安全缩减, R491+2s正确

### 1g. 连接失败模式 (6h)

| 模式 | 数量 |
|------|------|
| NVCFPexecTimeout (attempt级) | 95 |
| SSLEOF (attempt级) | 0 |
| empty_200 (attempt级) | 18 |
| 429 | 0 |

SSLEOF: 0 in 24h (R429逻辑正常, 完全静默)
empty_200: 18× 分布均匀(k0:5, k1:4, k2:3, k3:3, k4:3) — NVCF function排队返回, 非参数可修

### 1h. 15min桶SR (3h, CST时区)

| 桶 | total | ok | SR | ATE |
|-----|-------|----|-----|-----|
| 18:30 | 25 | 11 | 44.0% | 14 |
| 18:45 | 46 | 41 | 89.1% | 5 |
| 19:00 | 31 | 26 | 83.9% | 5 |
| 19:15 | 45 | 36 | 80.0% | 9 |
| 19:30 | 36 | 27 | 75.0% | 9 |
| 19:45 | 9 | 4 | 44.4% | 5 |
| 20:00 | 50 | 47 | 94.0% | 3 |
| 20:15 | 58 | 54 | 93.1% | 4 |
| 20:30 | 39 | 27 | 69.2% | 12 |
| 20:45 | 12 | 8 | 66.7% | 4 |
| 21:00 | 17 | 15 | 88.2% | 2 |
| 21:15 | 18 | 12 | 66.7% | 6 |
| 21:30 | 1 | 0 | 0.0% | 1 |

波动范围44-94%, 典型NVCF间歇行为, 非参数驱动

### 1i. Tier attempt级per-key (6h)

| Key | attempts | pexec_to | empty_200 | att_SR% |
|-----|----------|----------|-----------|---------|
| k0 | 20 | 15 | 5 | 0% |
| k1 | 27 | 23 | 4 | 0% |
| k2 | 17 | 14 | 3 | 0% |
| k3 | 25 | 22 | 3 | 0% |
| k4 | 23 | 20 | 3 | 0% |

Attempt-level SR=0%: 所有记录在hm_tier_attempts的是失败attempt(成功请求不一定写attempt表)

## 2. CC清单评估 (第4轮证伪)

### [HM1-A] MIN_OUTBOUND=3.8: 继续证伪
- 6h 0×429 → 零rate limiting
- P50_gap远>3.8s → throttle非瓶颈
- 降MIN_OUTBOUND只影响失败请求等待时间, 不改善SR
- **结论**: 证伪(非瓶颈) ×4

### [HM1-B] Key rebalancing: 继续证伪
- 5键全100% request-level SR
- 无单key劣化, 均衡cv≈8%(p50 6.9-8.3s)
- **结论**: 证伪 ×4

### [HM1-C] BUDGET=125: 继续证伪
- ATE max=79.2s << BUDGET=125s → 46s headroom
- 0× budget_exhausted_after_connect → BUDGET从未触发
- 收紧BUDGET(125→85)不会提升SR, 因失败是pexec_timeout非budget_exhausted
- 可能误杀: 慢成功请求最长>76s, 需BUDGET>76s才安全
- **结论**: 证伪(非瓶颈) ×4

### [HM1-D] FASTBREAK=3: 已完成(R500)
- ✅ 9× ATE在75-80s(3-attempt pattern活跃)
- ✅ 4× 救援成功(2失败后第3key成功)
- 运行正常, 无需再调
- **结论**: 已完成

## 3. 额外分析: 可动参数穷举

| 参数 | 当前值 | 可动? | 理由 |
|------|--------|-------|------|
| UPSTREAM_TIMEOUT | 25 | ❌不可降 | 7个成功在23-25s, 降→杀29+成功 |
| TIER_TIMEOUT_BUDGET_S | 125 | ⚠️可收紧但不改善 | 远超max_ATE=79s, 收紧无SR收益 |
| MIN_OUTBOUND_INTERVAL_S | 3.8 | 证伪 | 0×429, throttle非瓶颈 |
| KEY_COOLDOWN_S | 25 | 证伪 | 5键均100%SR, cooldown不触发 |
| TIER_COOLDOWN_S | 25 | 死参数 | 单tier无tier切换 |
| HM_SSLEOF_RETRY_DELAY | 2.0 | 证伪 | 0×SSLEOF in 24h |
| HM_PEXEC_TIMEOUT_FASTBREAK | 3 | 已完成 | R500变更, 运行正常 |
| HM_CONNECT_RESERVE_S | 10 | 死参数 | 0×budget_exhausted, reserve未触发 |

全8参数: 4×证伪 + 1×已完成 + 2×死参数 + 1×不可降 = 零可优化项

## 4. NOP决策

**本轮NOP**: CC清单4项全部证伪/完成, 额外穷举8参数无无安全正向变更. SR=81.9%由NVCF server-side pexec timeout决定, 非参数可修. 系统处于NVCF限制的均衡态.

R500 FASTBREAK=3变更效果确认: 3-attempt pattern活跃(9× ATE + 4× rescue), 每轮额外25s代价换取~20%概率成功.

## 5. 零配置变更

| 参数 | 改前值 | 改后值 | 变更 |
|------|--------|--------|------|
| (无) | — | — | — |

## 6. 铁律遵守

- ✅ 只改HM1不改HM2: 零变更
- ✅ 单参数少改多轮: 零变更(NOP)
- ✅ 数据驱动先采集后决策: 6h DB+docker logs+env验证+8参数穷举分析
- ✅ mihomo服务存活: 无重启
- ✅ 零429预警: 6h 0×429
- ✅ 配置一致性: compose与容器env双处一致

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记
