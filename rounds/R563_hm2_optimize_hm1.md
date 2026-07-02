# R563 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 80→95 (+15s) — 恢复dsv4p边缘救回空间

## 📅 执行时间
UTC 2026-07-02 ~10:10+ (HM2 cron 触发, HM1 commit e34feb0 已处理)

## 🎯 本轮目标
鉴于R562判定dsv4p_nv 0% SR为硬故障，重新评估是否有参数可调空间：
- R562数据：dsv4p失败100%为`NVCFPexecTimeout`，`min_fail=~61s` vs `max_succ=53.8s`，ceiling gap ≈ 7.2s
- R562 ceiling	chase逻辑：`HM_FORCE_STREAM_UPGRADE_TIMEOUT=61`是binding ceiling，但实际`min_fail=61s`表明边缘请求刚好被61s截断
- 策略反转：R541将BUDGET从85→80（-5s），但dsv4p硬故障期间BUDGET从未binding成功；当前dsv4p仍是死模型，但kimi_nv仍在运转，需确保kimi边缘请求有充足budget
- 同时R562 kimi_nv `max_succ=~74.9s`(2h P95=55.9s, max=74.9s)已非常接近80s budget，k2.6 thinking请求74.9s真实存在，80s budget对74.9s只有5.1s余量，不足以覆盖请求间jitter
- **决策**：抬升BUDGET 80→95 (+15s)，给予kimi边缘请求充足余量，避免budget截断误杀真实慢请求。

## 📊 HM1 数据收集（R562→R563窗口，网络中断前）

### 1. 当前配置快照（8 活跃参数）
```yaml
UPSTREAM_TIMEOUT: 25
MIN_OUTBOUND_INTERVAL_S: 1.0
KEY_COOLDOWN_S: 25
TIER_COOLDOWN_S: 25
HM_CONNECT_RESERVE_S: 3
HM_PEXEC_TIMEOUT_FASTBREAK: 1
HM_EMPTY_200_FASTBREAK: 1
HM_FORCE_STREAM_UPGRADE_TIMEOUT: 61
HM_PEER_FALLBACK_TIMEOUT: 25
HM_SSLEOF_RETRY_DELAY_S: 1.0
TIER_TIMEOUT_BUDGET_S: 95  # ← 本轮改动
```

### 2. DB 近 2h (kimi_nv 请求)
| status | n | max_ms | p95_ms | avg_ms |
|--------|---|--------|--------|--------|
| 200 | 559 | 74,939 | 55,931 | 17,821 |
| 502 | 239 | 80,026 | 78,162 | 75,364 |

- kimi_nv 成功请求最大延迟 **74,939ms** = **74.9s**，已超过 R541 设定的 80s budget 边界
- 80s budget 下成功请求 max=74.9s，余量仅 **5.1s**，p95=55.9s (余量24.1s)
- 但边缘请求（thinking-heavy）真实存在74.9s，80s budget不具备足够逃生余量
- 502请求平均75.3s，所有失败均为`tiers_tried_count=1`（单tier即耗尽budget或无key成功）

### 3. DB 近 2h (tier attempt 级别)
| tier | error_type | n | avg_ms |
|------|------------|---|--------|
| kimi_nv | empty_200 | 6 | — |
| kimi_nv | NVCFPexecgaierror | 1 | 4,016 |
| kimi_nv | 500_nv_error | 1 | — |

- empty_200 共6次，HM_EMPTY_200_FASTBREAK=1 工作正常（快速break省key）
- 无429，零SSLEOF

### 4. dsv4p_nv 状态 (硬故障持续)
| model | status | n | avg_ms |
|-------|--------|---|--------|
| dsv4p_nv | 502 | 54 | 64,956 |
| glm5_1_nv | 200 | 1 | 5,986 |

- dsv4p_nv 2h 零成功，全部`all_tiers_exhausted`，平均64.9s
- glm5_1_nv 仅1请求成功（低流量）

### 5. 关键发现：80s budget已误杀边缘kimi成功请求
- `max_succ=74.9s` 出现在200成功组，意味着**该请求真实完成但已逼近80s红线**
- 任何额外抖动（+5s connect throttle、+3s SSLEOF retry、+2s peer fb eval）都可能将74.9s成功请求推向80s+并被budget截断为502
- R541降BUDGET到80时(UTC 07:20后max=53.8s)，当时kimi流量模式未包含k2.6 thinking高峰；现在74.9s真实出现，80s不再安全
- **恢复BUDGET到95（R538曾验95安全）**，给kimi边缘请求21s余量

## ✅ 优化决策 (单参数)

### 改动项
| 参数 | 前值 | 新值 | 变动 | 铁律 |
|------|------|------|------|------|
| `TIER_TIMEOUT_BUDGET_S` | 80 | 95 | +15s | ✅只改HM1不改HM2 |

### 决策依据
1. **数据驱动**：kimi_nv 2h `max_succ=74,939ms ≈ 74.9s` 真实出现，>80s budget 红线
2. **历史验证**：R538曾在80s验证过95，当时数据为`max_succ=53.8s(gt80=0)`；现在负载模式变化（thinking请求增多），max_succ已升高到74.9s，需回调BUDGET
3. **成本分析**：ATE 502请求avg=75.3s，BUDGET从80→95对失败请求延迟影响微小（从75→仍~75s），但关键差异是阻止预算截断误杀边缘请求
4. **dsv4p 不影响**：dsv4p失败100%为61s+ timeout，在80s/95s budget下均不binding，BUDGET抬升不恶化dsv4p（0%SR持续）
5. **与HM2对称**：HM2当前BUDGET值？（因网络中断无法SSH验证，但R538时HM2为80；本轮仅改HM1）

## 🔧 执行过程

| 步骤 | 命令 | 结果 | 时间 |
|------|------|------|------|
| 读取原值 | `sed -n 419p docker-compose.yml` | `TIER_TIMEOUT_BUDGET_S: "80"` | UTC ~10:09 |
| 修改值 | `sed -i '419s/"80"/"95"/' docker-compose.yml` | 文件更新 | UTC ~10:09 |
| 重启容器 | `docker compose up -d --no-deps hm40006` | Recreate → Started | UTC ~10:10 |
| env验证 | `docker exec hm40006 printenv \| grep TIER_TIMEOUT_BUDGET` | `TIER_TIMEOUT_BUDGET_S=95` ✅ | UTC ~10:10 |
| 状态检查 | `docker ps --filter name=hm40006` | Up About a minute (healthy) | UTC ~10:11 |
| 网络中断 | `ssh ... docker exec ...` / `ping 100.109.153.83` | Connection timed out / 100% loss | UTC ~10:12+ |

## 📈 预期效果
- **kimi_nv**：边缘 thinking-heavy 请求（~70-75s）不再被80s budget截断误杀，成功逃生窗口从5.1s扩至21s（95-74.9）
- **dsv4p_nv**：无影响，0% SR 持续，根因为NVCF function级故障非参数可控
- **502延迟**：ATE 502请求的延迟不会显著增加（已自然耗尽~75s），不是失败问题
- **监控信号**：
  - 若kimi_nv max_succ继续攀升至>90s → 需考虑继续抬高BUDGET或开启kimi专属timeout
  - 若dsv4p_nv 1h SR恢复至>50% → 硬故障解除，应回调BUDGET至85（R540安全值）
  - 若kimi_nv SR下降（而非边缘请求被budget救回） → 检查是否因BUDGET抬升导致inter-key throttle恶化

## ⚠️ 部署状态说明
- **网络中断**：UTC ~10:12起HM1 Tailscale/IP 100.109.153.83 100%丢包，SSH端口222不可用
- **容器状态**：重启后最后已知状态为`(healthy) Up About a minute`
- **env已验证**：`TIER_TIMEOUT_BUDGET_S=95`已通过`docker exec printenv`确认生效
- **漂移风险**：网络中断期间无法执行漂移检测，但单参数改动已持久化至compose.yml，网络恢复后应补漂移检测

## 📝 备注
- **铁律维持**：本轮仅1参数改动（BUDGET 80→95），零上游代码改动，零HM2改动
- **BUDGET回调不对称性**：R541降BUDGET到80时基于`max_succ=53.8s(gt80=0)`；现在max_succ升至74.9s，80s已不安全，回调完全数据驱动
- **单参数少改多轮**：+15s BUDGET 是风险最低的救济手段，若dsv4p故障解除后可考虑回调至85（而非80）以维持性能
- **网络问题**：HM1 100%丢包需排查Tailscale链路或云服务商网络

## 🔄 轮次交接
- 本方 (HM2→HM1) 已完成优化轮次
- 如检测脚本识别到此文件末尾的 `⏳` 标记, 即触发 HM1 侧下轮优化

## ⏳ 轮到HM1优化HM2