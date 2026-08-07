# R1206 cc2 nv_gw NOP 巡检轮 (SSLEOFError 瞬时 egress blip 泛化跨 key 复发)

**日期**: 2026-08-08 08:00 CST
**结论**: NOP 不改码。30min/40min 窗口内 3× buffer_exhausted (SR 96.6%),
其中 **2 个 (76fb2449/7562e67f) 为上轮 R1205 blip (22:43-22:47 UTC) 的重复计入**,
仅 1 个 (7f34c956, 23:06 UTC) 为本轮新失败, 由「Remote end closed」瞬时 egress resets
跨 k1-k3 连续 3 次命中触发。链路基线健康 (19-21 UTC 连续 3h 100% SR), mihomo 进程/端口稳定,
错误跨全 5 key 均匀分布 → 上游 egress 瞬时抖动, 非配置回归, 不改码。

## 数据 (40min 窗口, 活查复核)

### 活查 cc4101-primary (nv_requests, status × upstream × error)
| status | upstream_type | error_type | count | avg_dur(ms) |
|---|---|---|---|---|
| 200 | nvcf_pexec | | 86 | 18407 |
| 502 | nvcf_pexec | buffer_exhausted | 1 | 79860 |
| 502 | | buffer_exhausted | 2 | 112525 |

SR = **96.6%** (86/89)。fallback 触发率 ~0% (fallback 走 ms_gw 兜底, 7f34c956 时 ms 也败)。

### 3× buffer_exhausted 请求归属 (JOIN nv_requests request_id)
| req | 归属 | ts (UTC) | avg_dur(ms) | 说明 |
|---|---|---|---|---|
| 76fb2449 | R1205 blip 残留 | 22:43-22:44 | 58039 | 上轮已计入, 重复窗口 |
| 7562e67f | R1205 blip 残留 | 22:46-22:47 | 79860 | 上轮已计入, 重复窗口 |
| 7f34c956 | **本轮新失败** | 23:04-23:06 | 167010 | k1→k2→k3 连续 3 次 Remote end closed → AKE fail-fast → ms 兜底也败 |

### 6h 小时级 SR (cc2-primary) — 基线健康证据
| hr (UTC) | total | ok | SR |
|---|---|---|---|
| 17:00 | 135 | 131 | 97.0% |
| 18:00 | 185 | 181 | 97.8% |
| **19:00-21:00** | 665 | 665 | **100.0% (3h 连续全绿)** |
| 22:00 | 170 | 168 | 98.8% |
| 23:00 | 25 | 24 | 96.0% |

### 3h nv_gw 错误分布 (跨全 key)
| key | SSLEOFError | Remote end closed |
|---|---|---|
| k1 | 2 | 4 |
| k2 | 3 | 2 |
| k3 | 5 | 2 |
| k4 | 7 | 1 |
| k5 | 3 | 1 |

**所有 5 key 均出现错误, 均匀分布** — 非单隧道故障, 是 egress/上游到 NVCF 的瞬时重置。

## 根因分析

- **唯一新失败 7f34c956** (input=67915c thinking=True): 07:04:37 k1 → 07:05:43 k2 →
  07:06:49 k3, 各隔 ~60s 全为 `Remote end closed connection without response`, 触发
  3-consecutive all_keys_exhausted → AKE fail-fast (跳过 WaitQueue, 省 ~120s) →
  `NV-BUFFER-MS-FB-ATTEMPT` → ms_gw 兜底也败 (`NV-BUFFER-MS-FB-FAIL`) → 502。167s 全耗在
  3 次 attempt 的 60s timeout × 3。防御链按设计工作 (fail-fast + ms 兜底), 只是同一瞬时坏的
  运气差吃了连续 3 发。
- **多数相同信号自愈**: 同窗 180b7acd (07:10 k1 err → attempt2 k2 → 200 ✓)、
  69b33a57/63930dd2/d172056e 等均 attempt-2/3 自愈, 只有 7f34c956 连败 3 次。
- **非配置回归**: 参数与上轮一致, 容器长时间未重启漂移 (nv_gw 32h, cc4101 27h), mihomo pid 1056
  自 Jul30 稳定, 5 个 proxy 端口全绑定。错误跨全 key 均匀 + 存在连续 3h 100% SR 基线 →
  **上游 NVCF edge/egress 瞬时重置**, 非本机可控修复点。

## 行动

NOP 不改码。这是 `[[ssleof-error-transient-egress-blip]]` 记忆里「瞬时多 key egress 抖动」模式的
**复发 + 泛化** (R1205 集中 ~5min blip → R1206 跨 k1-k5 分散 ~10min), 当前已达该记忆的
「持续分布才查 mihomo 线路」触发门槛的临界, 但 mihomo 进程/端口实测稳定 + 错误全 key 均匀 +
存在 3h 100% 基线 → 倾向上游瞬时而非隧道配置故障, 暂不动 code。

## 下一步
1. **核心监控** (按记忆触发门槛): SSLEOFError/`Remote end closed` 是否继续跨轮复发且分布持续。
   若下轮 (R1207) 仍见此类分散错误 + SR 维持 <99%, 则已达到「持续分布」条件 → 查 mihomo
   隧道线路质量 (各 egress_ip 的失败率、隧道状态), 必要时调整 key→proxy 绑定。
2. 单个意外 buffer_exhausted / 瞬时自愈错误仍 NOP。
3. 主键: 最大化单位时间 NV 成功数; 当前链路整体 SR 高 (存在 3h 100% 窗口), 防御链工作正常。