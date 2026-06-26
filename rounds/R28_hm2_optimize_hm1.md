# R28: HM2优化HM1 — 2026-06-26 08:26 UTC

**Actor**: HM2 (opc2_uname)
**Target**: HM1 (100.109.153.83, hm40006)
**Previous Round**: R27 (TIER_TIMEOUT_BUDGET_S 80→82, +2s tier budget, RESERVE=20下残余60→62s)
**Change**: HM_CONNECT_RESERVE_S: **20→21** (+1s SOCKS5+SSL连接预留)

## 数据收集

### 容器环境 (`docker exec hm40006 env`)
| 参数 | 值 |
|------|-----|
| UPSTREAM_TIMEOUT | 40 |
| TIER_TIMEOUT_BUDGET_S | 82 |
| MIN_OUTBOUND_INTERVAL_S | 10.0 |
| KEY_COOLDOWN_S | 38.0 |
| TIER_COOLDOWN_S | 90 |
| HM_CONNECT_RESERVE_S | 20 (变更前) |

### DB统计 (30分钟窗口, ~08:22 UTC)
**错误分布 (hm_tier_attempts)**:
| 错误类型 | 数量 | 平均耗时(ms) |
|----------|------|-------------|
| 429_nv_rate_limit | 715 | — |
| NVCFPexecTimeout | 154 | 26,864 |
| NVCFPexecConnectionResetError | 4 | 1,483 |
| NVCFPexecRemoteDisconnected | 1 | 7,577 |

**请求路由 (hm_requests)**:
| fallback_occurred | 请求数 | 平均耗时(ms) |
|-------------------|--------|-------------|
| false (直连) | 126 | 22,173 |
| true (回退) | 1,081 | 16,095 |

**整体指标**:
- 总请求: 1,209
- 回退率: 89.6% (1,083/1,209)
- 成功率: 98.5%
- 0-tier all_tiers_exhausted: **17** (tiers_tried_count=0, key_cycle_429s=0, avg 105,292ms)

**层级分布 (hm_tier_attempts)**:
| 层级 | 数量 |
|------|------|
| glm5.1_hm_nv | 731 |
| deepseek_hm_nv | 140 |
| kimi_hm_nv | 3 |

**Deepseek per-key超时分布**:
| Key | 端口 | NVCFPexecTimeout |
|-----|------|-------------------|
| k0 | — | 25 |
| k1 | 7894 | 33 |
| k2 | 7895 | 32 |
| k3 | 7896 | 22 |
| k4 | 7897 | 27 |

**hm_requests端错误**:
| 错误类型 | 数量 | 平均耗时(ms) |
|----------|------|-------------|
| all_tiers_exhausted | 17 | 105,292 |
| NVStream_IncompleteRead | 1 | 14,898 |

### 日志分析 (最近100行)
- 模式: glm5.1全部5个key一致429 → TIER-SKIP → deepseek回退成功
- 无ERROR/WARN级别日志（仅info级HM-KEY/HM-TIER/HM-FALLBACK）
- deepseek k1-k5均首次尝试成功（~10-40s per request）
- glm5.1在429风暴后TIER_COOLDOWN=90s进入全局冷却

## 诊断分析

### 根本原因

1. **0-tier连接级失败（17个）**: 所有17个all_tiers_exhausted均为 `tiers_tried_count=0, key_cycle_429s=0`，平均耗时105s。这些是SOCKS5+SSL握手阶段的预连接失败，发生在任何key cycle之前。HM_CONNECT_RESERVE_S=20已将其压到17个/30min的噪声平台。

2. **glm5.1函数级429不可修复**: 715个429全部集中在glm5.1 tier，所有5个key几乎同时触发429（NVCF function ID 822231fa-d4f3...全局速率限制）。这是基础设施级限制，不是per-key tuning能解决的。

3. **Deepseek回退层为实际工作层**: 89.6%请求通过deepseek回退成功。Deepseek per-key超时分布稳定（k0=25, k1=33, k2=32, k3=22, k4=27），不对称性自R24以来未恶化。

4. **系统处于稳定高原**: 98.5%成功率，17个0-tier失败，无明显新瓶颈出现。R27的TIER_BUDGET=82变化已生效且正常。

### 证据链
- R25: RESERVE=19, 0-tier failures ~22-23 → R26: RESERVE=20, 0-tier failures 17
- R27: TIER_BUDGET 80→82 (+2s), RESERVE=20下残余60→62s, 2nd attempt 22s
- R28: RESERVE=21继续追踪17→目标14-16的下降轨迹
- 每+1s RESERVE约移除2-3个0-tier失败（递减回报）

## 优化变更

| 参数 | 变更前 | 变更后 | 理由 |
|------|--------|--------|------|
| HM_CONNECT_RESERVE_S | 20 | **21** (+1s) | 继续减少0-tier预连接失败: 17→目标~14-16; 少改多轮(单参数); RESERVE=21s下TIER_BUDGET残余=61s, 2nd attempt=21s headroom(>10s最小值, 边界安全) |

### 未变更参数
UPSTREAM_TIMEOUT=40, TIER_BUDGET=82, MIN_INTERVAL=10.0, KEY_COOLDOWN=38.0, TIER_COOLDOWN=90 全部保持不变。

## 执行记录

```bash
# 备份
ssh -p 222 opc_uname@100.109.153.83 "cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R28"

# sed: 行451, 值 + 注释两处修改
cd /opt/cc-infra
sed -i '451s/"20"/"21"/' docker-compose.yml
sed -i '451s/# R26: HM2优化.*$/# R28: HM2优化 — 20→21: +1s SOCKS5+SSL连接预留; 0-tier pre-tier连接失败继续减少(17→目标~14-16); 少改多轮(单参数变更); RESERVE 21s下TIER_BUDGET残余=61s, 2nd attempt=21s headroom, 边界安全/' docker-compose.yml

# 部署
docker compose up -d hm40006

# 验证
HM_CONNECT_RESERVE_S=21 ✓
hm40006 Up 14 seconds (healthy) ✓
```

## 预期效果

- **0-tier连接失败**: 预计从17降至~14-16个/30min。每+1s RESERVE约移除2-3个SOCKS5+SSL握手级失败。
- **成功率**: 预计从98.5%微升至98.7-98.9%。17个失败中减少2-3个即为提升0.2-0.3%。
- **回退率**: 基本不变（89.6%）。0-tier失败减少不改变glm5.1→deepseek回退比例。
- **延迟**: 无直接影响。RESERVE不参与请求计时，仅影响握手阶段。

## 观察项

1. **RESERVE天花板临近**: 21s已接近20s实用上限。预算计算：TIER_BUDGET=82, RESERVE=21, 残余=61s。1st attempt=40s(完整), 2nd attempt=21s(>10s最小)。21s头room仍安全但再增加RESERVE会压缩2nd attempt。
2. **Deepseek per-key不对称稳定**: k1=33, k2=32 vs k3=22, k4=27。自R24以来未恶化，继续追踪无需行动。
3. **NVStream_IncompleteRead**: 单次出现(14,898ms)，可能是上游连接瞬时波动，继续观察。
4. **下次轮次方向**: 如果0-tier失败稳定在14-16范围，考虑TIER_COOLDOWN_S 90→85 (-5s)加快glm5.1恢复尝试，或调整UPSTREAM_TIMEOUT进一步优化deepseek超时分布。

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记