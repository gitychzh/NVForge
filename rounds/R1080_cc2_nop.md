# R1080 cc2 NOP — 主链 110/111 或 108/109, 1 transient bad (同签名 SSLEOFError egress 离散抖动, 自愈)

> 日期: 2026-08-07 20:40 CST | 轮: R1080 | 决策: NOP 巡检轮 (不改码)

## 判决依据 (注入 20:36 CST 分析 + nv_gw 日志根因复核 + DB 时间线)

- **30min 主链 cc4101-primary = 110/111 = 99.1% SR (上轮 R1079 记为 108/109, 窗口滚动), 1 bad**:
  502 buffer_exhausted, avg_dur 62796ms, 完成态 **12:19:55 UTC (20:19:55 CST)**。
- **根因**: 与 R1077/R1078/R1079 完全相同的签名 — transient **SSLEOFError `UNEXPECTED_EOF_WHILE_READING`**
  多 key egress 离散抖动, 非配置漂移。AKE fail-fast 正确触发 (省 WaitQueue), ms_gw fallback time-locked 未接管 → 502。
- **20:19:55 后全 clean**: 最近 10min 主链 35/35 = 100%, 零坏, 已完全自愈。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | 110/111 = 99.1% SR, 1 bad (buffer_exhausted) | ⚠️ root-caused transient 已自愈 |
| 错误时间线 | 唯一 502 完成态 20:19:55; 此后全 200 | ✅ |
| 最近 10min | 35/35 = 100% | ✅ 已自愈 |
| fallback | 0 次 (0%) | ✅ |
| 容器 /health | 40006/4101 全 200, nv_gw Up 22h | ✅ |

## 行动
- 无改动 (NOP)。故障在上游 TLS egress 离散抖动, 超出 nv_gw 参数调整范围, 已自愈, 无配置漂移。

## 下一步
- 保持 NOP 观察。连续 4 轮同签名单 bad, 均同一瞬时 egress 抖动周期。
- 仅当 SSLEOFError 复发且呈**持续分布** (非单次抖动) 才查 egress IP / mihomo 代理线路 (7900-7904), 属宿主链路, 超出 nv_gw 范围。
- 单 key 连续多轮 100% 失败才考虑换 fid; 当前键抖动后恢复, 无需动作。