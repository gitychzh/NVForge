# R1082 cc2 NOP — 主链 107/108 = 99.1%, 1 transient bad (同签名 SSLEOFError egress 离散抖动, 自愈), 最近28min 104/104=100% clean

> 日期: 2026-08-07 20:50 CST | 轮: R1082 | 决策: NOP 巡检轮 (不改码)

## 判决依据 (轮前注入 20:48 CST 分析 + 本轮 DB 复核 + 容器 /health)

- **30min 主链 cc4101-primary = 107/108 = 99.1% SR, 1 bad**：
  502 buffer_exhausted, 完成态 **12:19:55 UTC (20:19:55 CST)** (与 R1081 同瞬时)。
- **per-caller 归属复核 (铁证)**：错误分类表 NVStream_IncompleteRead×1 (12:40 UTC) + zombie_empty_completion×1 (12:39 UTC)
  **全部归属 hermes** (out-of-scope); cc4101-primary 仅 1 bad = buffer_exhausted。
- **根因**: 与 R1077~R1081 完全相同签名 — transient **SSLEOFError `UNEXPECTED_EOF_WHILE_READING`**
  多 key egress 离散抖动, 非配置漂移。AKE fail-fast 正确触发, ms_gw fallback time-locked 未接管 → 502。
- **自愈复核**: 该 1 bad 之后 (最近 28min, 即 20:22 后) 主链 **104/104 = 100%**, 零坏, 已完全自愈。
- **buffer 实时流**: 20:49 CST 日志全部 attempt=1 verdict=success_tool_call, elapsed 6-9s, 无 BUFFER-EXHAUSTED/WAIT-/KEYMANAGER 事件。
- **fallback**: 0/111 = 0.0%, 全走主链。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | 107/108 = 99.1% SR, 1 bad (buffer_exhausted) | ⚠️ root-caused transient 已自愈 |
| per-caller 归属 | 主链 1 bad; hermes 2 bad (IncompleteRead/zombie) 均 out-of-scope | ✅ |
| 错误时间线 | 唯一主链 502 完成态 20:19:55; 此后全 200 | ✅ |
| 最近 28min | 104/104 = 100% | ✅ 已自愈 |
| 30min fallback | 0 次 (0.0%) | ✅ |
| buffer 实时流 | attempt=1 success, 6-9s, 无耗尽/等待 | ✅ |
| 容器 /health | 40006/4101 全 200; nv_gw Up 17h, cc4101 Up 17h | ✅ |

## 行动
- 无改动 (NOP)。故障在上游 TLS egress 离散抖动, 超出 nv_gw 参数调整范围, 已自愈, 无配置漂移。

## 下一步
- 保持 NOP 观察。连续 6 轮 (R1077-R1082) 各 1 主链同签名单 bad, 均同一瞬时的 egress 离散抖动周期
  (故障在上游 TLS 连接中断, 自愈于 20:19:55 后, 非配置漂移, 无参数可调)。
- 仅当 SSLEOFError 复发且呈**持续分布** (非单次离散抖动) 才查 egress IP / mihomo 代理线路 (7900-7904), 属宿主链路, 超出 nv_gw 范围。
- 单 key 连续多轮 100% 失败才考虑 KEY_FID_BIND 换 fid; 当前键抖动后恢复, 无需动作。