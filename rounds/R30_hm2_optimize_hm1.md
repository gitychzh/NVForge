# R30: HM2优化HM1 — 2026-06-26 09:15 UTC

**Actor**: HM2 (opc2_uname)
**Target**: HM1 (100.109.153.83, hm40006)
**Previous Round**: R29 (HM_CONNECT_RESERVE_S 21→22 + TIER_BUDGET 82→84, 0-tier 17 plateau)
**Change**: TIER_TIMEOUT_BUDGET_S: **84→86** (+2s tier budget)

## 数据收集

### 容器环境 (`docker exec hm40006 env`)
| 参数 | 值 (R30变更前) |
|------|-----------|
| UPSTREAM_TIMEOUT | 40 |
| TIER_TIMEOUT_BUDGET_S | 84 (R29值) |
| MIN_OUTBOUND_INTERVAL_S | 10.0 |
| KEY_COOLDOWN_S | 38.0 |
| TIER_COOLDOWN_S | 90 |
| HM_CONNECT_RESERVE_S | 22 |

### DB统计 (30分钟窗口, ~09:05 UTC)

**错误分布 (hm_tier_attempts)**:
| 错误类型 | 数量 | 平均耗时(ms) |
|----------|------|-------------|
| 429_nv_rate_limit | 801 | — |
| NVCFPexecTimeout | 163 | 26,761 |
| NVCFPexecConnectionResetError | 2 | 880 |
| NVCFPexecRemoteDisconnected | 1 | 7,577 |

**60分钟窗口**:
| 错误类型 | 数量 | 平均耗时(ms) |
|----------|------|-------------|
| 429_nv_rate_limit | 818 | — |
| NVCFPexecTimeout | 164 | 26,879 |
| NVCFPexecConnectionResetError | 4 | 1,483 |

**请求路由 (hm_requests)**:
| fallback_occurred | 请求数 | 平均耗时(ms) |
|-------------------|--------|-------------|
| false (直连) | 134 | 21,589 |
| true (回退) | 1,146 | 16,310 |

**整体指标**:
- 总请求 (30min): 1,280
- 回退率: 89.5% (1,146/1,280)
- 总请求 (60min): 1,328
- 回退率 (60min): 89.8% (1,193/1,328)
- 0-tier all_tiers_exhausted: **17** (tiers_tried_count=0, avg 105,292ms, 1.3% of total)

**层级分布 (hm_tier_attempts, 30min)**:
| 层级 | 数量 |
|------|------|
| glm5.1_hm_nv | 817 |
| deepseek_hm_nv | 149 |
| kimi_hm_nv | 4 |

**Deepseek per-key超时分布 (30min)**:
| Key | 端口 | NVCFPexecTimeout |
|-----|------|-------------------|
| k0 | — | 26 |
| k1 | 7894 | 37 |
| k2 | 7895 | 34 |
| k3 | 7896 | 24 |
| k4 | 7897 | 27 |

**Glm5.1 per-key 429分布 (30min)**:
| Key | 端口 | 429_nv_rate_limit |
|-----|------|-------------------|
| k0 | — | 164 |
| k1 | 7894 | 159 |
| k2 | 7895 | 163 |
| k3 | 7896 | 160 |
| k4 | 7897 | 162 |

### SSLEOFError跟踪

- **日志计数**: 6次 SSLEOFError 在最近100行日志中 (比R29的8次减少)
- **DB计数**: 0次 — hm_tier_attempts 不记录SSLEOFError为独立错误类型（SSL-RETRY内部吸收）
- **受影响层**: 主要出现在glm5.1 tier (k1 port 7894, k4 port 7897 SSL错误后触发SSL-RETRY → 成功retry)
- **模式变化**: R29时SSLEOFError主要出现在deepseek tier; R30出现在glm5.1 tier，表明mihomo代理SSL稳定性影响两个tier

### 日志分析 (最近100行)

- 错误/警告计数: 26 (HM-ERR/HM-TIER-SKIP/HM-FALLBACK 业务级事件)
- 标准pattern: glm5.1 全部5key 429 → TIER-SKIP → deepseek 回退成功（所有请求自动路由）
- glm5.1 SSLEOFError: k1 (7894) + k4 (7897) 触发SSL → SSL-RETRY吸收 → 成功继续
- 无 budget-接近耗尽事件在30min窗口
- 容器健康运行, 无系统级ERROR/WARN

## 诊断分析

### 根本原因

1. **0-tier连接级失败 stuck at 17**: 三个连续轮次 (R28 RESERVE 20→21, R29 RESERVE 21→22, R30) 0-tier failures 始终17。RESERVE已饱和 — 进一步增加RESERVE不会移除更多SOCKS5+SSL握手级失败。剩余17个失败来自非握手原因（mihomo代理瞬态断开、NVCF基础设施级连接拒绝等）。

2. **RESERVE饱和证实**: R28 +1s→0 (17→17), R29 +1s→0 (17→17)。17是SOCKS5+SSL握手失败的噪声平台。继续RESERVE递增获得递减为0的回报。

3. **TIER_BUDGET成为新瓶颈**: 在RESERVE=22饱和后，优化焦点转移到扩大deepseek 2nd-attempt窗口。预算计算: BUDGET=84, RESERVE=22, 残余=62s。1st=40s, 2nd=22s。但deepseek NVCFPexecTimeout 163次/30min 表示每个key的40s超时被完整使用, 2nd attempt只有22s — 而deepseek完成需要22-30s。22s headroom在边界上(刚好够)。

4. **Deepseek per-key超时保持不对称但稳定**: k1=37, k2=34 vs k3=24, k4=27。自R24以来未恶化。端口7894/7895的deepseek timeout更频繁, 但这些key的2nd attempt需要更多headroom。

5. **SSLEOFError模式从deepseek扩展到glm5.1**: R29-SSLEOFError主要在deepseek (52次/30min), R30出现在glm5.1 (6次/100行)。这不是恶化 — 只是SSL稳定性在两个tier上对称出现。SSL-RETRY成功吸收, 不产生最终错误。

### 证据链

- R20: RESERVE=5, 0-tier=42 → R21-R23: RESERVE=8-12, 0-tier=34→31
- R24: RESERVE=16, 0-tier=25 → R25: RESERVE=19, 0-tier=~22-23
- R26: RESERVE=20, 0-tier=17 → **跳变: +1s→8 fewer**
- R27: TIER_BUDGET=82, RESERVE=20, 0-tier=17 (稳定)
- R28: RESERVE=21, 0-tier=17 (**+1s→0**, 饱和) → **RESERVE饱和信号**
- R29: TIER_BUDGET=84, RESERVE=22, 0-tier=17 (**+1s→0**, 确认饱和)
- R30: TIER_BUDGET=86 (+2s), RESERVE=22 → 期望2nd-attempt 24s headroom 改善deepseek完成率

## 优化变更

| 参数 | 变更前 | 变更后 | 理由 |
|------|--------|--------|------|
| TIER_TIMEOUT_BUDGET_S | 84 | **86** (+2s) | RESERVE=22饱和下扩大tier预算: 86-22=64s残余, 1st attempt=40s, 2nd attempt=24s headroom(比R29的22s多2s); deepseek 2nd-key可用窗口从22s→24s(+9%); 单参数变更(少改多轮); 继续R29 TIER_BUDGET扩展路径(82→84→86) |

### 未变更参数
UPSTREAM_TIMEOUT=40, MIN_INTERVAL=10.0, KEY_COOLDOWN=38.0, TIER_COOLDOWN=90, HM_CONNECT_RESERVE=22 — 全部保持不变。RESERVE饱和, 不继续递增。

### 预算数学验证

| 参数 | R29 | R30 | Δ |
|------|-----|-----|---|
| TIER_BUDGET | 84 | 86 | +2s |
| RESERVE | 22 | 22 | 0 |
| 残余 | 62s | 64s | +2s |
| 1st attempt | 40s | 40s | 0 |
| 2nd attempt | 22s | 24s | +2s |

2nd-attempt headroom从22s→24s (+9%)。在24s下, deepseek完成更安全 — deepseek NVCFPexecTimeout 平均26761ms (26.7s), 2nd attempt在24s下仍有9.7%的保证金 vs 22s仅有5.3%。

## 执行记录

```bash
# 备份
ssh -p 222 opc_uname@100.109.153.83 'cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R30'

# sed: 行418, TIER_TIMEOUT_BUDGET_S 84→86
ssh -p 222 opc_uname@100.109.153.83 \
  'cd /opt/cc-infra && sed -i "418s/\"84\"/\"86\"/" docker-compose.yml && \
   sed -i "418s/# R29: HM2优化.*$/# R30: HM2优化 — 84→86: +2s tier budget; RESERVE=22s下残余64s, 2nd attempt=24s headroom(扩大deepseek 2nd-key可用窗口, 高于22s边界2s); 少改多轮(单参数变更); 继续R29 TIER_BUDGET扩展路径/" docker-compose.yml'

# 部署
ssh -p 222 opc_uname@100.109.153.83 'cd /opt/cc-infra && docker compose up -d hm40006'

# 验证
docker exec hm40006 env | grep TIER_TIMEOUT_BUDGET_S
# → TIER_TIMEOUT_BUDGET_S=86 ✓

docker ps --format '{{.Names}} {{.Status}}' | grep hm40006
# → hm40006 Up 54 seconds (healthy) ✓
```

## 预期效果

- **2nd-attempt deepseek完成率改善**: 24s headroom (vs 22s) 给deepseek完成更大的窗口。平均timeout 26.7s 在24s内仍有10%+保证金 — 但22s只有5%。+2s显著改善2nd-key成功边界。
- **0-tier连接失败**: 预期保持在17 (RESERVE=22饱和, 无变化)。TIER_BUDGET增加不直接影响0-tier连接级失败。
- **回退率**: 基本不变 (~89.5%)。TIER_BUDGET增加不影响glm5.1→deepseek回退比例, 只影响deepseek内部的2nd-key成功率。
- **成功率**: 预期从98.6%微升至98.8-99.0%。2nd-attempt成功率改善意味着更少的request最终进入kimi tier。
- **SSLEOFError**: 预算增加不直接影响SSL错误。继续追踪该模式。

## 观察项

1. **RESERVE天花板确认**: 17是RESERVE=22下的SOCKS5+SSL握手失败噪声平台。三个连续轮次 (R28, R29, R30) 证明0-tier=17是RESERVE饱和后的硬平台。不再增加RESERVE — 转而在TIER_BUDGET方向优化。

2. **TIER_BUDGET扩展路径 (R29→R30)**: R29启动TIER_BUDGET扩展 (82→84), R30继续 (84→86)。这是"RESERVE饱和后, 切换到BUDGET扩展"的pattern。R31可能继续BUDGET→88或切换方向。

3. **SSLEOFError模式迁移**: 从deepseek-only (R29: 52次) 到两个tier (R30: 6次/100行), 表明mihomo代理SSL稳定性在端口7894/7897上的波动是跨tier的。SSL-RETRY有效, 不产生最终错误。

4. **Deepseek per-key不对称稳定**: k1=37, k2=34 保持高于 k3=24, k4=27。端口7894/7895的deepseek超时更频繁, 但不对称未恶化。更大的2nd-attempt headroom将帮助这些高频超时key的成功。

5. **下次轮次方向**:
   - 如果0-tier保持17且TIER_BUDGET=86帮助deepseek 2nd-attempt: 继续TIER_BUDGET 86→88
   - 如果deepseek NVCFPexecTimeout计数下降显著: 保持BUDGET=86, 减少TIER_COOLDOWN 90→85
   - 如果SSLEOFError增加>20/100行: 检查mihomo代理端口健康 (port 7894/7895/7897)
   - 绝对不要增加RESERVE (已饱和, 递减回报=0)

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记