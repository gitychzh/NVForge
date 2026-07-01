# R539 (HM1→HM2): HM_PEER_FALLBACK_TIMEOUT 59→61 (+2s) — 对齐HM1真实ceiling(R538=61), 修复HM2→HM1 forwarding路径边缘截断

**轮次**: R539
**方向**: HM1 优化 HM2 (本轮执行者=HM1, 对端=HM2, host_machine=opc2_uname)
**日期**: 2026-07-02 06:48 CST (部署)
**类型**: 参数优化轮 (铁律: 只改HM2不改HM1本地)
**改动参数**: HM_PEER_FALLBACK_TIMEOUT (单参数, 59→61, +2s)
**Commit**: 本commit

---

## 0. 轮次定位与基线评估

- R538(HM2→HM1)将HM1的 `HM_PEER_FALLBACK_TIMEOUT` 59→61, 对齐HM2真实ceiling=61(R533), 修复HM1→HM2 forwarding路径的59s截断.
- 然而, HM2的 `HM_PEER_FALLBACK_TIMEOUT` 仍为59(R536所设), 未随HM1同步跟进.
- 本轮基于R538部署后HM2 forwarding路径的新数据, 勘定 `HM_PEER_FALLBACK_TIMEOUT` 59→61为本轮改动点 (单参数, 符合铁律5).

## 1. 改前数据 (基线窗口 06:43–06:48 UTC字面值, 5min)

### 1.1 HM2 改前运行态 (docker exec hm40006 env, 改动前)
```
HM_FORCE_STREAM_UPGRADE_TIMEOUT=61      # R533所设
HM_PEER_FALLBACK_TIMEOUT=59             # R536所设, 未随R538同步
HM_PEER_FALLBACK_ENABLED=1
HM_PEER_FALLBACK_URL=http://100.109.153.83:40006   (HM2→HM1 fallback)
UPSTREAM_TIMEOUT=61                     # R534所设
TIER_TIMEOUT_BUDGET_S=80                # R538所设(从100降)
HM_PEXEC_TIMEOUT_FASTBREAK=1
HM_CONNECT_RESERVE_S=3
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=22
MIN_OUTBOUND_INTERVAL_S=1.0
```

### 1.2 HM2 改前 docker logs 最近500行统计 (06:43–06:48窗口)
| 指标 | 数值 | 说明 |
|---|---|---|
| HM-ALL-TIERS-FAIL→502 | 1 | 本地tier全部失败, peer-originated请求无进一步fallback |
| peer-originated no-fb | 1 | `[HM-PEER-FB] peer-originated request (hop=1) also all_tiers_exhausted, no further fallback, returning 502` |
| HM-TIMEOUT | 1 | kimi_nv k4 NVCF pexec timeout, attempt=16233ms total=77430ms |
| HM-PEXEC-FASTBREAK | 1 | 1 consecutive NVCFPexecTimeout → fast-break |
| HM-TIER-FAIL | 1 | kimi_nv all 5 keys failed: 429=0, empty200=1, timeout=1, other=0 |
| THINKING-TIMEOUT | 10 | thinking request stream=True → extended timeout 61s (正常, 非错误) |
| REQ | 10 | 正常请求进入 |

**注意**: 窗口内未出现HM2→HM1 peer fallback的成功/失败日志, 因为当前负载中HM2本地失败后直接触发peer fb, 但peer fb timeout=59 < HM1 ceiling=61, 若HM1处理时间落在59-61s区间则会被截断.

### 1.3 HM2 DB 最近2小时聚合 (hm_requests)
| request_model | status | count | avg_duration_ms | max_duration_ms |
|---|---|---|---|---|
| dsv4p_nv | 200 | 3 | 30193 | 38242 |
| dsv4p_nv | 502 | 1 | 59343 | 59343 |
| kimi_nv | 200 | 217 | 17270 | 76982 |
| kimi_nv | 502 | 41 | 80665 | 97869 |

kimi_nv 502率 = 41/(217+41) = **15.9%**.

### 1.4 R538留给本轮的接力信息 (来自R538 §5)
> HM2 待验证: HM2的PEER_FALLBACK_TIMEOUT=R536所设59. 当时HM1 ceiling=59, 现HM1=61, 故HM2→HM1 forwarding存在对称的59s cliff. 建议下轮HM1优化HM2时升HM2 PEER_FALLBACK_TIMEOUT 59→61.

## 2. 决策

**调整**: `HM_PEER_FALLBACK_TIMEOUT` 59→61 (+2s)

**理由**:
1. **R538 ceiling提升后peer fb未跟进**: HM1 PEER_FALLBACK_TIMEOUT=61 (R538刚设), 但HM2 PEER_FALLBACK_TIMEOUT=59, 形成HM2→HM1 forwarding路径的59s cliff.
2. **对称性修复**: HM1 ceiling=61(R538). HM2 forwarding到HM1的最长等待应≥HM1的处理ceiling.
3. ** budgets独立不影响**: TIER_TIMEOUT_BUDGET_S=80约束本地tier处理; peer fb为ALL_TIERS_EXHAUSTED后的逃生通道, timeout独立设置.
4. **单参数+2s, 符合铁律5**: 不多改, 不 chasing symptoms, 逐个参数爬坡.
5. **R538明确标注的待修复项**: R538第5节明确建议本轮执行此改动.

## 3. 执行

### 3.1 改动清单 (仅改HM2)

```diff
# /opt/cc-infra/docker-compose.yml (hm40006 环境变量)
- HM_PEER_FALLBACK_TIMEOUT: "59"  # R536: HM1→HM2 — 65→59 (-6s) 对齐HM1旧ceiling=59
+ HM_PEER_FALLBACK_TIMEOUT: "61"  # R539: HM1→HM2 — 59→61 (+2s). R538恢复HM1 ceiling至61, HM2 peer fb仍59形成HM2→HM1 forwarding路径cliff; 对齐HM1真实ceiling=61消除边缘截断
```

### 3.2 部署命令 (铁律: 只改HM2容器, 不动mihomo)
```bash
ssh -p 222 opc2_uname@100.109.57.26
sed -i 's/HM_PEER_FALLBACK_TIMEOUT: "59"/HM_PEER_FALLBACK_TIMEOUT: "61"/g' /opt/cc-infra/docker-compose.yml
cd /opt/cc-infra && docker compose up -d --no-deps hm40006
```

### 3.3 改后验证 (06:48 CST)

- **compose 文件**: `grep 'HM_PEER_FALLBACK_TIMEOUT' /opt/cc-infra/docker-compose.yml` → `"61"` ✅
- **容器 env**: `docker exec hm40006 env | grep HM_PEER_FALLBACK_TIMEOUT` → `61` ✅
- **运行日志**: 重启后 `[HM-PROXY] Starting Hermes NV proxy` 正常, 零ERROR/WARN ✅
- **对称验证**: HM2 HM_FORCE_STREAM_UPGRADE_TIMEOUT=61 与 HM_PEER_FALLBACK_TIMEOUT=61 同值, 本端ceiling与forwarding ceiling一致 ✅

## 4. 改后预测与下轮验证指标

- **预测**: HM2→HM1 peer fallback 的59s→61s边缘救回. 若HM1侧处理时间落在59-61s区间, 此前会被HM2的59s timeout截断返502, 现可正常等待至61s后成功.
- **验证窗口**: 建议采集20min+ logs, 统计 `[HM-PEER-FB] peer connect/request failed after` 次数与耗时分布.
- **重点指标**: peer fallback 是否在59000ms附近仍有截断, 或是否出现>59000且<61000ms的成功peer fb.

## 5. 给下轮 (HM2 优化 HM1) 的接力信息

- HM2 当前配置: BUDGET=80 / THINKING=61 / UPSTREAM=61 / PEER_FB=61 / FASTBREAK=1 / MIN_OUTBOUND=1.0 / RESERVE=3 / KEY_CD=38 / TIER_CD=22.
- **HM1 当前配置**: BUDGET=100 / THINKING=61 / UPSTREAM=25 / PEER_FB=61 / FASTBREAK=1 / MIN_OUTBOUND=1.2 / RESERVE=3 / KEY_CD=25 / TIER_CD=25.
- **双向对称**: 经R538+R539两轮修复, HM1↔HM2的peer fallback ceiling现已双向对齐=61. 两侧forwarding路径均无59s cliff.
- **HM2日志重点**: peer-originated请求(HM1→HM2到达的请求)处理情况; 本地tier失败模式是否改善.
- **严禁**: 任何 stop/restart/kill mihomo服务. 本round仅通过`docker compose up -d --no-deps hm40006`重启proxy容器.

## ⏳ 轮到HM2优化HM1
