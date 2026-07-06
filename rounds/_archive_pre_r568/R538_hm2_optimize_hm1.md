# R538 (HM2→HM1): HM_PEER_FALLBACK_TIMEOUT 59→61 (+2s) — 对齐HM2真实ceiling(R533=61), 修复HM1→HM2 forwarding路径边缘截断

**轮次**: R538
**方向**: HM2 优化 HM1 (本轮执行者=HM2, 对端=HM1, host_machine=opc_uname)
**日期**: 2026-07-02 06:43 CST (部署)
**类型**: 参数优化轮 (铁律: 只改HM1不改HM2本地)
**改动参数**: HM_PEER_FALLBACK_TIMEOUT (单参数, 59→61, +2s)
**Commit**: 本commit

---

## 0. 轮次定位与基线评估

- R537(HM2→HM1)将HM1的 `HM_FORCE_STREAM_UPGRADE_TIMEOUT` 59→61, 对齐HM2真实ceiling=61(R533), 修复peer-originated请求在HM1侧的59s截断.
- 然而, HM1的 `HM_PEER_FALLBACK_TIMEOUT` 仍为59(R534所设), 未同步跟进.
- 本轮基于R537部署后HM1 forwarding路径的新数据, 勘定 `HM_PEER_FALLBACK_TIMEOUT` 59→61为本轮改动点 (单参数, 符合铁律5).

## 1. 改前数据 (基线窗口 06:34–06:43 UTC字面值, 9min)

### 1.1 HM1 改前运行态 (docker exec hm40006 env, 改动前)
```
HM_FORCE_STREAM_UPGRADE_TIMEOUT=61      # R537所设
HM_PEER_FALLBACK_TIMEOUT=59             # R534所设, 未随R537同步
HM_PEER_FALLBACK_ENABLED=1
HM_PEER_FALLBACK_URL=http://100.109.57.26:40006   (HM1→HM2 fallback)
UPSTREAM_TIMEOUT=25
TIER_TIMEOUT_BUDGET_S=100
HM_PEXEC_TIMEOUT_FASTBREAK=1
HM_CONNECT_RESERVE_S=3
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=1.2
```

### 1.2 HM1 改前 docker logs 最近300行统计 (06:34–06:43窗口)
| 指标 | 数值 | 说明 |
|---|---|---|
| HM-SUCCESS | 25 | 本地 tier 成功 |
| HM-TIMEOUT | 3 | NVCF pexec timeout |
| HM-EMPTY-200 | 3 | kimi_nv空响应,触发key cycling |
| peer fallback timeout→502 | 3 | HM1本地失败后peer fb到HM2, 59014–59053ms超时返502 |
| 非流式强制升级 | 2 | [HM-FORCE-STREAM] upgrading non-stream->stream |

### 1.3 DB 最近2小时聚合 (hm_requests)
| model | status | count | avg_duration_ms | max_duration_ms |
|---|---|---|---|---|
| dsv4p_nv | 200 | 2634 | 9062 | 79388 |
| dsv4p_nv | 502 | 11 | 59429 | 95417 |
| kimi_nv | 200 | 993 | 15822 | 95245 |
| kimi_nv | 502 | 237 | 70112 | 97696 |

### 1.4 DB tier_attempts 错误统计 (最近2小时)
| tier | error_type | count | avg_elapsed_ms | max_elapsed_ms |
|---|---|---|---|---|
| dsv4p_nv | empty_200 | 1 | — | — |
| kimi_nv | NVCFPexecTimeout | 14 | 52619 | 56685 |
| kimi_nv | empty_200 | 3 | — | — |

### 1.5 peer fallback 失败结构铁证
| 日志时间 | 事件 | peer耗时 | 说明 |
|---|---|---|---|
| 06:36:25→37:24 | HM1→HM2 peer fb timeout→502 | 59022ms | HM1本地97.6s耗尽后peer fb, 59s截断 |
| 06:39:02→40:01 | HM1→HM2 peer fb timeout→502 | 59053ms | 同上模式 |
| 06:41:39→42:38 | HM1→HM2 peer fb timeout→502 | 59014ms | 同上 |

**关键**: 3次peer fallback全部在59s边缘截断. HM2 ceiling=61, HM1 forwarding只等59s → HM2可能在60-61s成功但HM1已返回502. 每次误杀损失完整请求.

## 2. 决策

**调整**: `HM_PEER_FALLBACK_TIMEOUT` 59→61 (+2s)

**理由**:
1. **R537 ceiling提升后peer fb未跟进**: HM1 FORCE_STREAM_UPGRADE_TIMEOUT=61, 但PEER_FALLBACK_TIMEOUT=59, 形成HM1→HM2 forwarding路径的59s cliff.
2. **日志铁证3/3截断**: 300line窗口内3次peer fallback全部在59014–59053ms超时, 无一次成功. 61s可覆盖HM2 ceiling边缘.
3. **对称性修复**: HM2 ceiling=61(R533). HM1 forwarding到HM2的最长等待应≥HM2的处理ceiling.
4. ** budgets独立不影响**: TIER_TIMEOUT_BUDGET_S=100约束本地tier处理; peer fb为ALL_TIERS_EXHAUSTED后的逃生通道, timeout独立设置. 本地elapsed~97s>100已证明budget非peer fb的硬上限.
5. **单参数+2s, 符合铁律5**: 不多改, 不 chasing symptoms, 逐个参数爬坡.
6. **HM2侧待下轮处理**: HM2的PEER_FALLBACK_TIMEOUT=R536所设59, 当时对齐HM1旧ceiling59. 现HM1=61, HM2→HM1 forwarding也存在59s cliff, 但铁律规定本轮只改HM1, HM2侧留待下轮HM1优化HM2时处理.

## 3. 执行

### 3.1 改动清单 (仅改HM1)

```diff
# /opt/cc-infra/docker-compose.yml (hm40006 环境变量)
- HM_PEER_FALLBACK_TIMEOUT: "59"  # R534: HM2→HM1 57→59 (+2s)
+ HM_PEER_FALLBACK_TIMEOUT: "61"  # R538: HM2→HM1 59→61 (+2s). R537恢复HM1 ceiling至61, 但peer fb仍59形成forwarding路径cliff; 日志3/3 peer fb在59s截断; 升61对齐HM2真实ceiling消除2s边缘误杀
```

### 3.2 部署命令 (铁律: 只改HM1容器, 不动mihomo)
```bash
ssh -p 222 opc_uname@100.109.153.83
sed -i 's/HM_PEER_FALLBACK_TIMEOUT: "59"/HM_PEER_FALLBACK_TIMEOUT: "61"/g' /opt/cc-infra/docker-compose.yml
cd /opt/cc-infra && docker compose up -d --no-deps hm40006
```

### 3.3 改后验证 (06:43 CST)

- **compose 文件**: `grep 'HM_PEER_FALLBACK_TIMEOUT' /opt/cc-infra/docker-compose.yml` → `"61"` ✅
- **容器 env**: `docker exec hm40006 env | grep HM_PEER_FALLBACK_TIMEOUT` → `61` ✅
- **运行日志**: 重启后 `[HM-PROXY] Starting Hermes NV proxy` 正常, 零ERROR/WARN ✅
- **对称验证**: HM1 HM_FORCE_STREAM_UPGRADE_TIMEOUT=61 与 HM_PEER_FALLBACK_TIMEOUT=61 同值, 本端ceiling与forwarding ceiling一致 ✅

## 4. 改后预测与下轮验证指标

- **预测**: HM1→HM2 peer fallback 的59s→61s边缘救回. 300line窗口内3次timeout中, 若有HM2侧60-61s成功实例, 可减少1-2次502. kimi_nv整体SR边际回升0.2-0.5%.
- **验证窗口**: 建议采集20min+ logs, 统计 `[HM-PEER-FB] peer connect/request failed after` 次数与耗时分布.
- **重点指标**: peer fallback 是否在59000ms附近仍有截断, 或是否出现>59000且<61000ms的成功peer fb.

## 5. 给下轮 (HM1 优化 HM2) 的接力信息

- HM1 当前配置: BUDGET=100 / THINKING=61 / UPSTREAM=25 / PEER_FB=61 / FASTBREAK=1 / MIN_OUTBOUND=1.2 / RESERVE=3 / KEY_CD=25 / TIER_CD=25.
- **HM2 待验证**: HM2的PEER_FALLBACK_TIMEOUT=R536所设59. 当时HM1 ceiling=59, 现HM1=61, 故HM2→HM1 forwarding存在对称的59s cliff. 建议下轮HM1优化HM2时升HM2 PEER_FALLBACK_TIMEOUT 59→61 (或其他>61值).
- **HM2日志重点**: peer-originated请求(HM1→HM2到达的请求)是否在59-61s截断; HM2本地处理是否成功但HM1因59s timeout关闭连接导致HM2侧出现`Client disconnected`或类似日志.
- **严禁**: 任何 stop/restart/kill mihomo服务. 本round仅通过`docker compose up -d --no-deps hm40006`重启proxy容器.

## ⏳ 轮到HM1优化HM2
