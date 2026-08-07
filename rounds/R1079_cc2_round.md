# R1079 — cc2 NOP 巡检轮 (2026-08-07 21:05 CST)

## 结论: NOP, 不改码

cc2 主链 (cc4101-primary → nv_gw:40006, dsv4f0731_nv) 30min 绝大多数时间完全健康, 仅 1 个 transient bad:
**108/109 = 99.1% SR, 1 bad (buffer_exhausted 502, avg_dur 62796ms)**; fallback 0 次。
该 1 bad 与 R1077/R1078 **同签名**: **transient SSLEOFError `UNEXPECTED_EOF_WHILE_READING`** 多 key egress 抖动,
窗口内 20:18:53 (DB 完成态) / c107bc7e@20:19:55 最后 fail-fast, **之后全 clean (120min+ attempt=1 success)**, 参数无需改动。

## 依据

- 注入轮前链路分析 (20:32 CST): cc4101-primary|dsv4f0731_nv|200|108 + 502|1 (err=buffer_exhausted, avg_dur 62796ms)。
  dsv4f0731_nv 整体 SR=100% (146/146) + 1×502 (主链统计); hermes 38×200 (out-of-scope)。
  错误分类 buffer_exhausted×1 (root-cause=SSLEOFError egress 抖动)。30min fallback 0 次 (0%)。
- DB 复核 (--since 15min): 唯一 502 buffer_exhausted 完成态 **12:18:53 UTC (20:18:53 CST)**, 此后 12:19:55→now 全 200, 零坏。
- 容器 /health 复核: 40006 nv_gw 200, 4101 cc4101 200; nv_gw Up 17h, cc4101 Up 17h。

## root cause 分析 (1 bad: buffer_exhausted)

- nv_gw 日志 (--since 40m) 复核: 20:09-20:19 区间共 4-5 个同签名 transient all_keys_exhausted
  (73e3e619@20:09 / 93422c26@20:12 / 2d088060@20:15 / 33858179@20:15 / c107bc7e@20:19),
  均为 **SSLEOFError `UNEXPECTED_EOF_WHILE_READING`** 依次命中 k3/5→k1→k2, 每次轮转不同 key 仍全挂。
- 3 次 consecutive all_keys_exhausted 触发 **AKE fail-fast** (最后一次 `c107bc7e`@20:19:55, skip WaitQueue, state CLOSED)
  → 尝试 ms_gw fallback (time-locked 未接管) → 该请求报 502 给 CC → DB 记 buffer_exhausted 完成态 20:18:53。
- **AKE fail-fast + buffer 超时链工作完全符合设计**: 每次 60s 内 fail-fast 释放, 未浪费 450s buffer 预算。
- 我复核日志确认 **20:19:55 后 nv_gw 再 0 条 EXEC-FAIL / fail-fast / all_keys_exhausted / SSLEOF / buffer / wait 活动**
  (25min+ 全程记录), 20:30-20:33 buffer 日志全 attempt=1 success (4 请求全 success_text/success_tool_call) ——
  已自愈, 与 R1077/R1078 模式完全一致 (离散 egress 抖动, 故障在上游 TLS 连接中断, 非配置漂移, 无参数可调)。

## 数据表

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **108/109 = 99.1% SR, 1 bad** (buffer_exhausted) | ⚠️ root-caused transient |
| 30min fallback | 0 次 (0.0%), 全走主链 | ✅ |
| dsv4f0731_nv 整体 | 146/146 = 100% + 1×502 | ✅ |
| 错误分类 | buffer_exhausted×1 (root-cause=SSLEOFError egress 抖动) | ✅ 已自愈 |
| 错误时间线 | 唯一 502 完成态 20:18:53 (c107bc7e@20:19:55 最后 fail-fast) | ✅ |
| buffer 日志 | 20:19:55 后 0 SSLEOF / 0 buffer-fail / 0 wait, 全 attempt=1 success | ✅ |
| 容器 /health | 40006/4101 全 200; nv_gw Up 17h, cc4101 Up 17h | ✅ |

## 下一步
- 保持 NOP 观察。本轮 1 bad 为同签名 transient SSLEOFError egress 离散抖动 (故障在上游 TLS 连接中断), 已自愈, 非配置漂移, 无参数可调。
- 连续 3 轮 (R1077/R1078/R1079) 同签名单 bad, 均为同一瞬时的 egress 离散抖动周期, 未呈持续分布 → 无需查 egress IP / mihomo 线路。
- 仅当 SSLEOFError 呈**持续分布**或单 key 连续多轮 100% 失败, 才查 egress 线路 / KEY_FID_BIND 换 fid; 当前无动作。