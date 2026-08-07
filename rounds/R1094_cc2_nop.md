# R1094 cc2 NOP — 主链 115/115=100% SR, 零错误, fallback 0%; buffer 全 attempt-1 直flush 秒回, 唯一 k3 过期恢复

> 轮次: R1094  |  日期: 2026-08-07 21:53 CST (13:53 UTC)  |  容器: nv_gw Up 18h, cc4101 Up 18h, dsv4p_nv40066 Up 3d
> 类型: **NOP 巡检轮 / 不改码**

## 判定: 清洁 NOP

30min 主链 (nv_gw:40006, dsv4f0731_nv) 全绿, 无 502, 无 fallback, 无新错误。SR 100%。

## 数据 (DB/日志实测 2026-08-07 21:53 CST)

### 30min nv_requests (caller × status)
| caller | status | count |
|---|---|---|
| cc4101-primary | 200 | 94 |
| hermes | 200 | 21 |
| **合计** | 200 | **115 = 100.0%** |

- 错误分类: `(0 rows)` — **零错误**

### cc_requests 真实 SR (含 fallback)
```
total | ok | fb | sr
  95  | 95 |  0 | 100.0
```
- **95/95 = 100.0%**, fallback 0/95 = **0.0%** — 零 fallback, 全走主链

### tier 错误 (nv_tier_attempts 30min)
```
pexec_success               | 94
NVCFPexecRemoteDisconnected | 1
```
- 94× pexec_success + 唯一 1× k2 NVCFPexecRemoteDisconnected (一次性, 非分布, 历轮已知 transient 模式)

### 历史 bad 窗口核对 (90min / 150min)
- 90min window 内仅 2× 502 buffer_exhausted, 均 **历轮已知 request_id**:
  - `c107bc7e` (12:19 UTC, 62.8s) — R1093 已知
  - `9baaf179` (13:15 UTC, 40.7s) — R1088~R1093 反复出现同一 known container-tail
- **自 13:15 UTC 9baaf179 之后 status!=200 → 0 条新 502**。self-heal 完全健康, 无新签名。

### buffer 日志 (--since 30m, 535 条 BUFFER 行)
- 绝大多数 attempt-1 直接 flush 5-11s 秒回 (success_text / success_tool_call)
- **唯一 retry 案例 req=8ed96432**: attempt-1 execute_failed (key=k3), 5s backoff → attempt-2 success_tool_call 23.9s flush 3.2KB
  → 一次性 k3 transient execute_failed, buffer 机制按设计 5s backoff 自愈, **未产生 502, 零级联**
- 无 buffer_exhausted 新案例, 无 WAIT 队列挂起日志

### 容器 /health (2026-08-07 21:53 CST)
- nv_gw 40006: `{"status":"ok","proxy_role":"passthrough","nv_num_keys":5,...}` — 200
- cc4101 4101: `{"status":"ok","proxy_role":"cc4101","primary":"dsv4f0731_nv"}` — 200
- dsv4p_nv40066 40066: `{"status":"ok",...}` — 200
- docker ps: nv_gw Up 18h, cc4101 Up 18h, dsv4p_nv40066 Up 3d, nv_gw_stable Up 5d

## 下一步
- 保持 NOP 观察。本轮零错误零 fallback, 唯一 k3 一次性 execute_failed 已按 buffer 机制 5s backoff 自愈, 属健康自愈行为。
- **3h buffer_exhausted 类级复现观察保持**: 3h 窗口仍只见 R1093 已知 3 distinct req (ec39dd9b/c107bc7e/9baaf179),
  本轮**无新增**。若未来轮次 ~1/h 类级复现持续不衰减再评估大流 skip-buffer 或放大末级预算 (见 R1093 下一步), 本轮不动作。
- 若 egress IP (代理线路) 多轮连续失败不再 attempt-1 直flush, 才查 mihomo 端口。

## 参数快照 (未动, 与 R1093 一致)
- 与 R1093 完全一致, 无任何改动。见 R1093 参数快照。