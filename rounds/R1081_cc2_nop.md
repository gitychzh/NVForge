# R1081 cc2 NOP — 主链 105/106 = 99.1%, 1 transient bad (同签名 SSLEOFError egress 离散抖动, 自愈)

> 日期: 2026-08-07 20:43 CST | 轮: R1081 | 决策: NOP 巡检轮 (不改码)

## 判决依据 (注入 20:43 CST 分析 + DB 时间线 + per-caller 归属复核 + 容器 /health)

- **30min 主链 cc4101-primary = 105/106 = 99.1% SR, 1 bad**：
  502 buffer_exhausted, avg_dur 62796ms, 完成态 **12:19:55 UTC (20:19:55 CST)**。
- **per-caller 归属复核 (铁证)**：错误分类表里的 NVStream_IncompleteRead×1 + zombie_empty_completion×1
  **全部归属 hermes** (20:39/20:40 CST), 与主链无关, out-of-scope；
  cc4101-primary 仅有 1 bad = buffer_exhausted。
- **根因**: 与 R1077/R1078/R1079/R1080 完全相同的签名 — transient **SSLEOFError `UNEXPECTED_EOF_WHILE_READING`**
  多 key egress 离散抖动, 非配置漂移。AKE fail-fast 正确触发 (省 WaitQueue), ms_gw fallback time-locked 未接管 → 502。
- **20:19:55 后全 clean**: 最近 10min 主链 34/34 = 100%, 零坏, 已完全自愈。
- **数据清理**: docker ps 实测 nv_gw Up 17h (上轮注入记 22h, 为本轮刷新), cc4101 Up 17h, 40006/4101 /health 全 200。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | 105/106 = 99.1% SR, 1 bad (buffer_exhausted) | ⚠️ root-caused transient 已自愈 |
| per-caller 归属 | 主链 1 bad; hermes 2 bad (IncompleteRead/zombie) 均 out-of-scope | ✅ |
| 错误时间线 | 唯一主链 502 完成态 20:19:55; 此后全 200 | ✅ |
| 最近 10min | 34/34 = 100% | ✅ 已自愈 |
| 30min fallback | 0 次 (0.0%) | ✅ |
| 容器 /health | 40006/4101 全 200; nv_gw Up 17h, cc4101 Up 17h | ✅ |

## 行动
- 无改动 (NOP)。故障在上游 TLS egress 离散抖动, 超出 nv_gw 参数调整范围, 已自愈, 无配置漂移。

## 下一步
- 保持 NOP 观察。连续 5 轮 (R1077-R1081) 各 1 主链 sam签名单 bad, 均同一瞬时 egress 抖动周期。
- 仅当 SSLEOFError 复发且呈**持续分布** (非单次抖动) 才查 egress IP / mihomo 代理线路 (7900-7904), 属宿主链路, 超出 nv_gw 范围。
- 单 key 连续多轮 100% 失败才考虑换 fid; 当前键抖动后恢复, 无需动作。