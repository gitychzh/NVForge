# R40: HM1 → HM2 优化报告

**轮次**: R40 (HM1→HM2, 偶数编号)
**执行者**: HM1 (opc_uname)
**时间**: 2026-06-26 12:25 UTC
**目标**: 降低HM2 hm40006链路的SSLEOFError和ConnectionResetError

---

## 📊 采集数据 (30min窗口 ~11:55-12:25 UTC)

### HM2 请求概览
| 指标 | 值 |
|------|------|
| 请求总数 | 1297 |
| 成功 | 1290 (99.5%) |
| Fallback数 | 1123 (86.6%) |
| 平均延迟 | 22,945ms |
| p50延迟 | 18,207ms |
| p90延迟 | 45,187ms |
| p95延迟 | 57,016ms |

### HM2 错误分布 (hm_tier_attempts 30min)
| 错误类型 | 数量 | 占比 |
|----------|------|------|
| 429_nv_rate_limit | 165 | 87.8% |
| NVCFPexecSSLEOFError | 17 | 9.0% |
| NVCFPexecConnectionResetError | 4 | 2.1% |
| NVCFPexecRemoteDisconnected | 2 | 1.1% |
| **总计** | **188** | 100% |

### glm5.1 Key级别错误分布
| Key | 429 | SSLEOF | ConnReset | RemoteDisc | 总错误 |
|-----|-----|--------|-----------|------------|--------|
| k1 | 33 | 1 | 0 | 0 | 34 |
| k2 | 33 | 1 | 1 | 0 | 35 |
| k3 | 34 | 0 | 1 | 2 | 37 |
| **k4** | **32** | **10** | **0** | **0** | **42** |
| k5 | 33 | 1 | 2 | 0 | 36 |

### deepseek fallback错误
| Key | SSLEOF |
|-----|--------|
| k1 | 1 (15551ms) |
| k2 | 1 (5533ms) |
| k3 | 1 (25064ms) |
| k4 | 1 (8132ms) |

### HM2 当前环境变量 (变更前)
| 参数 | 值 |
|------|------|
| TIER_COOLDOWN_S | 55 |
| UPSTREAM_TIMEOUT | 62 |
| HM_CONNECT_RESERVE_S | **4** → 目标 **6** |
| KEY_COOLDOWN_S | 26.0 |
| TIER_TIMEOUT_BUDGET_S | 111 |
| MIN_OUTBOUND_INTERVAL_S | 16.5 |

---

## 🔍 诊断分析

### 关键发现
1. **k4 SSLEOF异常**: k4有10次SSLEOF，其他key平均0.75次 → k4是13.3倍异常值
2. **SSLEOF是HM2最大可优化错误**: 17次SSLEOF占非429错误的81%（17/21）
3. **与HM1对比鲜明**:
   - HM2 SSLEOF=17 vs HM1 SSLEOF=2 → HM2是HM1的8.5倍
   - HM2 ConnReset=4 vs HM1 ConnReset=16 → HM2只有HM1的1/4
   - **核心差异**: HM2 `HM_CONNECT_RESERVE_S=4` vs HM1 `HM_CONNECT_RESERVE_S=22`
   - HM1有5.5倍的连接预留时间，因此SSLEOF极少
4. **429均匀分布**: k1=33, k2=33, k3=34, k4=32, k5=33 → 函数级429限速，非per-key
5. **Fallback率86.6%**: 结构性429驱动，非配置优化范围
6. **deepseek SSLEOF=4**: 代理层也偶尔断开deepseek连接

### 因果链
```
HM_CONNECT_RESERVE_S=4 (仅4s连接预留)
  → mihomo SOCKS5代理在高负载时TLS握手>4s
  → 连接超时表现为SSLEOF
  → k4尤其严重 (10/17 = 59%的所有SSLEOF)
  → 多余key尝试浪费时间 (avg SSLEOF elapsed=6259ms on k4)
  → tier fail elapsed更长 (up to 32599ms on one request)
```

---

## ⚡ 优化方案

**变更参数**: `HM_CONNECT_RESERVE_S: 4 → 6 (+2s, +50%)`

### 理由
- HM1用`HM_CONNECT_RESERVE_S=22`只有2次SSLEOF/30min
- HM2用`HM_CONNECT_RESERVE_S=4`有17次SSLEOF/30min
- 4s→6s给TLS握手50%更多缓冲，同时不至于浪费太多时间在真正失败的连接上
- 保守递增：先+2s观察效果，如不够下次再+1-2s
- k4的10次SSLEOF平均耗时6259ms → 实际连接过程远超4s，6s应能覆盖大部分场景

### 预期效果
| 指标 | 当前 (R40前) | 目标 (R40后) |
|------|------------|------------|
| NVCFPexecSSLEOFError | 17/30min | 6-10/30min |
| k4 SSLEOF | 10/30min | 2-4/30min |
| tier fail平均elapsed(mixed) | ~14s | ~12s |
| deepseek SSLEOF | 4/30min | 1-2/30min |

### 风险评估
- **低风险**: +2s连接预留 → 最坏情况下每个failed key多等2s
- **每轮时间影响**: 5 key全失败时 +2s×5=+10s, 但TIER_TIMEOUT_BUDGET_S=111足够
- **不可逆性**: 如反效果，下轮HM2可回滚到4

---

## 🔧 执行步骤

1. ✅ SSH到HM2 (opc2_uname@100.109.57.26)
2. ✅ 采集数据: docker logs, docker compose config, DB查询
3. ✅ 分析诊断: 识别k4 SSLEOF异常+HM_CONNECT_RESERVE_S过小
4. ✅ 修改 `/opt/cc-infra/docker-compose.yml` 第510行
5. ✅ 部署: `docker compose up -d --no-deps hm40006` 容器重建成功
6. ✅ 验证: `HM_CONNECT_RESERVE_S=6` 确认生效, proxy正常启动

### 配置变更详情
```yaml
# /opt/cc-infra/docker-compose.yml line 510
# Before:
HM_CONNECT_RESERVE_S: "4"
# After:
HM_CONNECT_RESERVE_S: "6"
```

---

## 📈 与R39对比 (HM2 vs HM1)

| 指标 | R39 HM1数据 | R40 HM2数据 | 备注 |
|------|-----------|-----------|------|
| 请求总数 | 86 | 1297 | HM2负载更大 |
| 成功率 | 100% | 99.5% | HM2有7个失败 |
| Fallback率 | 97.7% | 86.6% | HM2 fallback更低 |
| 429 | 1108 | 165 | HM2低(请求量不同) |
| SSLEOF | 2 | **17** | ⚠️ HM2 8.5倍 |
| ConnReset | 16 | 4 | HM2更低 |
| deepseek timeout | 142 | 0 | HM1因UPSTREAM_TIMEOUT=42s临界 |
| HM_CONNECT_RESERVE_S | **22** | **4→6** | 关键差异 |

---

## 🔭 下轮观察项 (R41 HM2→HM1)

1. **SSLEOF趋势**: R40后HM2 SSLEOF是否从17降至6-10? k4是否从10降至2-4?
2. **ConnectionReset**: 是否受影响? (预期不变, ConnReset是瞬时断连非超时)
3. **deepseek SSLEOF**: 4→? 是否也受益于更长的连接预留
4. **fallback elapsed时间**: tier_fail平均elapsed是否缩短(SSLEOF成功连接更快)
5. **TIER_COOLDOWN_S=55是否需调整**: 如果SSLEOF大幅降低,可考虑降低cooldown加速tier重试
6. **R39 HM1问题**: HM1的TIER_COOLDOWN_S=84产生反效果(Fallback率97.7%), 如R41 HM2要优化HM1, 优先回滚TIER_COOLDOWN_S

## ⏳ 轮到HM2优化HM1
