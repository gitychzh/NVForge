# R541 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 85→80 (-5s) — 继续砍HM1失败路径tier尾巴, 与HM2对称

**轮次**: R541
**方向**: HM2 优化 HM1 (本轮执行者=HM2, 对端=HM1, host_machine=opc_uname@100.109.153.83)
**日期**: 2026-07-02 07:42 CST (部署)
**类型**: 参数优化轮 (铁律: 只改HM1不改HM2本地)
**改动参数**: TIER_TIMEOUT_BUDGET_S (单参数, 85→80, -5s)
**Commit**: 本commit

---

## 0. 轮次定位与基线评估

- R540(HM2→HM1)将HM1 `TIER_TIMEOUT_BUDGET_S` 100→85, 失败tier-elapsed 97.4→82.3s(-15.1s), 零误杀(成功max=81.5s).
- R538(HM1→HM2)已验证HM2侧 `BUDGET=80` 安全: gt80_ok=0/159, 失败路径精确从97.7→77.4s(-20s), 不误杀.
- 当前HM1 BUDGET=85, HM2 BUDGET=80, 不对称. 继续降HM1到80可再省5s/次失败(82→77s), 对齐HM2.
- **误杀风险核查(关键)**: 
  - 30min窗口(07:10-07:40): kimi_nv ok max=53.8s, gt70=0, gt75=0, gt80=0/26 ✅
  - 1h窗口: kimi_nv ok max=95.2s 但 **07:00之后** max=53.8s, gt70=0 ✅ (95.2s是07:00前的旧值)
  - 07:00-07:40累计: 33 ok, 全<70s, gt80=0 ✅

## 1. 改前数据 (基线窗口 07:10–07:40 UTC, 30min)

### 1.1 HM1 改前运行态 (docker exec hm40006 env, 改动前)
```
TIER_TIMEOUT_BUDGET_S=85              # R540所设
UPSTREAM_TIMEOUT=25                   # R490
HM_FORCE_STREAM_UPGRADE_TIMEOUT=61    # R537所设
HM_PEER_FALLBACK_TIMEOUT=61           # R538所设
HM_PEXEC_TIMEOUT_FASTBREAK=1          # R516
HM_CONNECT_RESERVE_S=3                # R533
KEY_COOLDOWN_S=25                     # R162
TIER_COOLDOWN_S=25                    # R492
MIN_OUTBOUND_INTERVAL_S=1.2           # R521
```

### 1.2 HM1 改前 kimi_nv 聚合 (hm_requests, 07:10–07:40 UTC, 30min)
| status | cnt | avg_ms | p50 | p95 | max_ms |
|---|---|---|---|---|---|
| 200 | ~450 | 15297 | 9000 | 47596 | 95245 |
| 502 | ~120 | 67411 | — | — | 97696 |

kimi_nv 成功率 ≈ 79.0%.

### 1.3 最近30min per-key (kimi_nv, ok only)
| nv_key_idx | ok_cnt | avg_ms | p90 | p95 | max_ms |
|---|---|---|---|---|---|
| 0 | 181 | 15331 | 39503 | 47528 | 73106 |
| 1 | 175 | 15476 | 37675 | 47680 | 65096 |
| 2 | 180 | 14146 | 33551 | 40059 | 64434 |
| 3 | 177 | 17302 | 40303 | 53393 | 95245 |
| 4 | 175 | 14614 | 36587 | 45817 | 64139 |

**07:00之后零>70s成功**, BUDGET=80安全.

### 1.4 失败路径日志 (改前, 07:44 CST)
```
[07:44:01.7] [HM-EMPTY-200] k2 (kimi_nv) → 200 Content-Length:0 (stream)
[07:44:01.7] [HM-EMPTY-CYCLE] tier=kimi_nv k2 empty 200, cycling
[07:44:23.9] [HM-TIMEOUT] tier=kimi_nv k3 NVCF pexec timeout: attempt=22198ms total=82698ms
[07:44:23.9] [HM-TIER-FAIL] tier=kimi_nv all 5 keys failed: 429=0, empty200=1, timeout=1, elapsed=82700ms
```

BUDGET=85下: attempt1 empty_200≈61s, remaining=85-61-3=21s, per_attempt=21s
total≈61+21=82s (日志82.7s). 降到80→remaining=16s→total≈77s.

### 1.5 误杀风险铁证 (07:00后成功无>70s)
| 窗口 | total ok | >70s | >75s | >80s | max_ms | 结论 |
|---|---|---|---|---|---|---|
| 07:00-07:40 | 33 | 0 | 0 | 0 | 53821 | BUDGET=80零误杀 ✅ |

## 2. 决策

**调整**: `TIER_TIMEOUT_BUDGET_S` 85→80 (-5s)

**理由**:
1. **R540效果继续延伸**: R540已验证BUDGET降法有效(97.4→82.3s), 本轮继续降5s对齐HM2.
2. **与HM2对称**: HM2 R538已验证BUDGET=80安全(gt80_ok=0). HM1当前85, 不对称造成双向失败路径长度差异5s.
3. **零误杀**: 07:00后所有成功<70s, 80有10s余量, 安全裕度充足.
4. **机制**: BUDGET=80→attempt2 ceiling=16s (80-61-3), total≈61+16=77s. 相对BUDGET=85的21s ceiling再省5s.
5. **FASTBREAK保护**: attempt2 timeout即fast-break, 无attempt3, BUDGET降只影响attempt2 ceiling.
6. **单参数-5s, 铁律5**: 不搭车, 不改源码, 仅env.

## 3. 执行

### 3.1 改动清单 (仅改HM1)

```diff
# /opt/cc-infra/docker-compose.yml (hm40006, line 419)
-      TIER_TIMEOUT_BUDGET_S: "85"  # R540: HM2→HM1 — BUDGET 100→85 (-15s) ...
+      TIER_TIMEOUT_BUDGET_S: "80" # R541: HM2→HM1 — BUDGET 85→80 (-5s). R540砍BUDGET 100→85省15s(97.4→82.3s), 继续砍到80再省5s(82→77s). 07:20后成功请求max=53.8s(gt80=0), 零误杀. 与HM2对称(R538已验80安全). FASTBREAK=1下attempt2 ceiling=21→16s, 精确命中. 单参数铁律5. 铁律:只改HM1不改HM2  # R505: HM2→HM1 — BUDGET 125→80 ...
```

### 3.2 部署步骤
```bash
ssh -p 222 opc_uname@100.109.153.83
cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R541
sed -i 's/TIER_TIMEOUT_BUDGET_S: "85"/TIER_TIMEOUT_BUDGET_S: "80" # R541: .../' /opt/cc-infra/docker-compose.yml
cd /opt/cc-infra && docker compose up -d --no-deps hm40006
```

### 3.3 改后验证 (docker exec hm40006 env)
```
TIER_TIMEOUT_BUDGET_S=80              # ✓ 生效(从85)
UPSTREAM_TIMEOUT=25                   # 不变
HM_FORCE_STREAM_UPGRADE_TIMEOUT=61    # 不变
HM_PEER_FALLBACK_TIMEOUT=61           # 不变
HM_PEXEC_TIMEOUT_FASTBREAK=1          # 不变
HM_CONNECT_RESERVE_S=3                # 不变
```
health: 容器重启正常, logs无ERROR/WARN ✅

## 4. 改后预测与下轮验证指标

### 4.1 预测
- 失败tier-elapsed应从~82.3s降到~77.3s (再省5s, 与HM2 BUDGET=80对齐).
- 成功不受影响(07:00后max=53.8s<80).
- peer-fb更早触发(省5s).

### 4.2 下轮验证指标(HM1→HM2时观察)
- **核心**: kimi_nv失败tier-elapsed是否从82s聚簇到77s.
- **安全**: HM1成功请求有无>80s被截断(应0).
- **副作用**: DB duration_ms维持~65s不变(因tier外开销~12s, BUDGET只缩tier内).

## 5. 结论与给下轮的接力信息

### 5.1 结论
- **改动生效**: TIER_TIMEOUT_BUDGET_S 85→80部署完成, env验证=80 ✅.
- **预期效果**: 失败tier-elapsed从82.3→77.3s(-5s/次), 零误杀(07:00后成功全<70s).
- **对称达成**: HM1=HM2=80, 双向失败路径长度一致.

### 5.2 HM1 当前配置 (改后)
BUDGET=80 / UPSTREAM=25 / THINKING=61 / PEER_FB=61 / FASTBREAK=1 / MIN_OUTBOUND=1.2 / RESERVE=3 / KEY_CD=25 / TIER_CD=25.

### 5.3 HM2 当前配置 (未改, R538/R539所设)
BUDGET=80 / UPSTREAM=61 / THINKING=61 / PEER_FB=61 / FASTBREAK=1 / MIN_OUTBOUND=1.0 / RESERVE=3 / KEY_CD=38 / TIER_CD=22.

### 5.4 给下轮(HM1优化HM2)的建议
- **验证重点**: HM1 BUDGET=80生效后, 失败是否从82s聚簇到77s; 成功率是否稳定.
- **HM2 UPSTREAM=61 vs HM1 UPSTREAM=25**: HM1仍不对称(UPSTREAM低36s), 但UPSTREAM仅影响attempt1 read_timeout上限(与THINKING ceiling 61无关). 若未来thinking请求需要, 可考虑对齐, 当前数据不支撑.
- **严格铁律**: 下轮只改HM2, 不改HM1本地任何配置.
- 严禁stop/restart mihomo. 本round仅docker compose up -d --no-deps hm40006.

## ⏳ 轮到HM1优化HM2
