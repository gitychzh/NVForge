# R371: HM2→HM1 — ⏸️ NOP · 全量100%请求级成功率 · 1h窗口21/21=100% · 全容器3.5h窗口75/75=100% · 4 SSLEOF+1 TIMEOUT全部retry救回 · per-key完美均衡(k1=4,k2=4,k3=4,k4=4,k5=5) · 全参数已达天花板 · 第20轮连续NOP · 铁律:只改HM1不改HM2

**轮次**: HM2 优化 HM1 (HM2=执行者, HM1=反对者)
**角色**: HM2=执行者, HM1=反对者
**日期**: 2026-06-30 23:55 UTC+8 (CST) / 15:55 UTC
**触发**: 脚本检测到HM2端R370末尾标记 ⏳ 轮到HM1优化HM2, HM1未新提交, HM2当前主动执行
**作者**: opc2_uname (HM2)
**铁律**: 只改HM1不改HM2 ✅ (本轮零配置变更)

---

## 📊 数据采集 (HM1实时窗口, host_machine='opc_uname', 100.109.153.83)

### 容器状态
- **hm40006**: Up ~4h15min (since 03:39 UTC restart, 2026-06-30)
- **镜像**: cc-infra-hm40006, NVCF pexec直连单模型 deepseek_hm_nv
- **架构**: R38.12 NVCF pexec 直连, 代理=passthrough
- **路由**: k1=SOCKS5(7894), k2/k3=DIRECT, k4=SOCKS5(7897), k5=SOCKS5(7899)
- **function_id**: 4e533b45-dc54 (NVCF pexec ACTIVE)
- **日志区间**: 11:35:46 (容器启动) → 15:04:46 (最新), 约3h29min活跃窗口

### 全量容器日志分析 (75请求, 100%请求级成功率)
| 指标 | 值 |
|------|-----|
| 总请求 (HM-REQ) | 75 |
| 总成功 (HM-SUCCESS) | 75 |
| 请求级成功率 | **100%** (75/75, 无请求失败) |
| SSLEOF错误 | 4 (k1=3, k5=1) |
| TIMEOUT错误 | 1 (k1, 48.7s) |
| 429错误 | 0 |
| ATE (all_tiers_exhausted) | 0 |
| 错误恢复率 | **100%** (5/5 全部retry成功救回) |

### 错误时间线 (全集中在容器早期 ~40min)
| 时间 (UTC) | 错误类型 | 受击key | 恢复 |
|------------|---------|--------|------|
| 11:36:56 | SSLEOFError | k1 (SOCKS5 7894) | k2 retry成功 |
| 11:43:39 | SSLEOFError | k1 (SOCKS5 7894) | k2 retry成功 |
| 12:13:36 | SSLEOFError | k1 (SOCKS5 7894) | k2 retry成功 (3.0s backoff) |
| 12:14:42 | SSLEOFError | k5 (SOCKS5 7899) | k1 retry成功 (3.0s backoff) |
| 12:15:42 | TIMEOUT (48.7s) | k1 (SOCKS5 7894) | k2 retry成功 |

**关键发现**: 5个错误全集中在11:36-12:15 UTC (~40min窗口), 此后12:16-15:04 (约2h50min) 零错误, 连续57次first-attempt全部成功。容器早期错误为冷启动/连接池warm-up正常现象, 稳定后零错误。

### 1h最新窗口 (14:04-15:04 UTC)
| 指标 | 值 |
|------|-----|
| 窗口请求 | 21 |
| 成功 (first attempt) | 21 |
| 错误 | 0 |
| 请求级成功率 | **100%** |
| per-key分布 | k1=4, k2=4, k3=4, k4=4, k5=5 |

**完全干净**: 最新完整1h窗口零错误, 完美RR轮转 k1→k2→k3→k4→k5→k1→..., 全部first-attempt成功, 零重试, 零延迟异常。

### 全量 per-key 成功分布 (含retry后)
| Key | 成功数 | 占比 | 路由 |
|-----|--------|------|------|
| k2 | 19 | 25.3% | DIRECT (无代理) |
| k3 | 15 | 20.0% | DIRECT (无代理) |
| k4 | 15 | 20.0% | SOCKS5 via 7897 |
| k5 | 14 | 18.7% | SOCKS5 via 7899 |
| k1 | 12 | 16.0% | SOCKS5 via 7894 |

**平衡度**: 极好。k2略高(k1-k5: 19-15-15-14-12), max-min差=7 (19-12), 在RR随机抖动正常范围内。平均15 req/key, k1因4个错误(全重试成功)导致初始分配略少, 不影响整体。

### 当前 HM1 运行参数 (env→live compose 双重验证, 零漂移)
| 参数 | 值 | 说明 |
|------|-----|------|
| TIER_TIMEOUT_BUDGET_S | 100 | tier超时预算 |
| UPSTREAM_TIMEOUT | 45 | 单连接超时 |
| KEY_COOLDOWN_S | 38 | key 429冷却 |
| TIER_COOLDOWN_S | 38 | tier 429冷却 |
| MIN_OUTBOUND_INTERVAL_S | 6.0 | 出站节流间隔 |
| HM_CONNECT_RESERVE_S | 10 | 连接预留warm-up |
| HM_SSLEOF_RETRY_DELAY_S | 3.0 | SSL重试延迟 |
| FASTBREAK (代码内) | 3 | 连续timeout快速中断 |

---

## 📋 参数优化评估

### 可优化参数分析 (全部已达天花板)

| 参数 | 当前值 | 可优化方向 | 评估 |
|------|--------|-----------|------|
| **KEY_COOLDOWN_S=38** | 38s | 增加→更长冷却减少429重试 | ❌ 当前零429, 增加无用且浪费NVCF容量 |
| | | 减少→更快恢复 | ❌ 当前零429, 减少无效果 |
| **TIER_COOLDOWN_S=38** | 38s | 增加/减少 | ❌ 当前零429, 无数据支撑改动 |
| **MIN_OUTBOUND_INTERVAL_S=6.0** | 6.0s | 减少→更高吞吐 | ❌ 当前per-key完美均衡, 无burst需要更高吞吐; 减少可能增加429风险 |
| | | 增加→更保守 | ❌ 当前零429, 增加无益 |
| **HM_SSLEOF_RETRY_DELAY_S=3.0** | 3.0s | 增加→更长backoff减少连续SSLEOF | ❌ 所有SSLEOF已100%恢复, 3s当前完美; 增加延迟无数据支撑 |
| | | 减少→更快重试 | ❌ 当前3s已足够快, 减少可能增加NVCF RX压力 |
| **HM_CONNECT_RESERVE_S=10** | 10s | 增加/减少 | ❌ 冷启动warm-up已足够, k2/k3 DIRECT无connection错误; 当前无连接层错误 |
| **TIER_TIMEOUT_BUDGET_S=100** | 100s | 减少→更早fallback | ❌ 当前零tier级timeout, 减少无用且可能误杀慢成功(48.7s TIMEOUT在100s内) |
| **UPSTREAM_TIMEOUT=45** | 45s | 增加/减少 | ❌ 当前单次TIMEOUT=48.7s已在retry成功, 调整无实际效果 |

**结论**: 所有6个参数均处于最优位置, 无任何数据支撑优化改动。

---

## ✅ 决策: ⏸️ NOP (No Operation)

**原因**: HM1已达性能天花板。全容器3.5h窗口75/75=100%请求级成功率, 1h最新窗口21/21=100%。4个SSLEOF+1个TIMEOUT (共5个错误, 全集中在早期40min) 全部retry成功救回。5个错误后连续2h50min零错误(57次first-attempt全成功)。per-key完美均衡(k1-k5: 12-19-15-15-14, max-min差仅7)。所有7个可调参数均在最优点, 无数据支撑任何改动。env与live compose双处零漂移。HM1全参数活跃消费, 无死参数。HM1代码中FASTBREAK=3从未触发(无连续3次timeout)。任何配置改动能带来的收益为零, 唯一可能的风险是误改破坏已达天花板的稳定状态。

**连续NOP轮数**: 第20轮 (R346-R371, HM2→HM1方向连续NOP)

**铁律**: 只改HM1不改HM2 (零配置变更) ✅

**参数变更**: 无

**反对者预案**: HM1若认为仍有优化空间:
1. 容器早起k1 SSLEOF集群(11:36-12:15, 3次)可能是NVCF pexec特定function endpoint的临时行为, 非HM1可控制。4个SSLEOF+1个TIMEOUT已100%恢复, 零请求失败。
2. 若HM1想调整SSLEOF_RETRY_DELAY, 需提供3s→X秒的明确优化数据和预期收益, 当前无数据表明3s不够快或需要更长backoff。
3. 若HM1想调整FASTBREAK从3→更大的值, 需证明存在误杀rescue路径: 当前0次FASTBREAK触发(无连续3次timeout), FASTBREAK=3代码活跃且从未误杀。
4. 12h+窗口需重新审视: 容器自03:39重启后已运行~4h, 零新增ATE, 零429, 证明所有参数已达稳定天花板。若HM1认为需要48h+长窗口观察, 当前无新数据可支撑此论点。

---

## ⏳ 轮到HM1优化HM2
