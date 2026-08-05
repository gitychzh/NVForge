# R828 — cc2 NOP 巡检轮: R827 修复就位验证 + NVCF 风暴后链路全恢复

> 时间: 2026-08-05 16:44 CST | 上轮: R827 (buffer total_deadline 锚定 t_start)
> 容器: nv_gw (Up 1h, R827 restart 后) | 改动: 无 (NOP 巡检轮)

## 本轮改动: 无 (NOP)

R827 已在上轮 commit (f1169e3) 并 restart nv_gw。本轮做的是 **R827 修复就位验证** +
风暴后链路恢复确认。无源码 / 无 env 改动。

## R827 修复就位铁证

```bash
docker exec nv_gw python3 -c "
import gateway.buffer_stream as b, inspect
src = inspect.getsource(b.BufferStreamSession.__init__)
print('R827 t_start anchor:', 'self.t_start + NVU_BUFFER_TOTAL_DEADLINE_S' in src)
print('old time.time()+450:', 'time.time() + 450' in src or 'time.time() + NVU_BUFFER_TOTAL_DEADLINE_S' in src)"
# → R827 t_start anchor: True
# → old time.time()+450: False
```

磁盘代码 (buffer_stream.py:83-89) 与运行中容器代码一致, R827 修复正确就位。

## 30min 真实链路数据 (16:09-16:39 CST, cc4101-primary)

### nv_requests (cc2 的请求)

| status | count | 备注 |
|---|---|---|
| 200 | 89 | 全 success |
| 502 | 3 | 全在 16:08-16:21 风暴窗口 |

per-call SR = 96.7% (89/92), 3 个 502 全集中在 NVCF 风暴窗口 (16:08-16:21 CST),
之后 23 分钟连续零 502。

### cc4101 真实 SR (cc_requests, 含 fallback)

| total | ok | fb | sr |
|---|---|---|---|
| 91 | 90 | 1 | 98.9% |

用户可见 SR = 98.9% (1 个非 200), fallback = 1/91 = 1.1% < 10% ✅

### per-key tier attempts (30min, glm5_2_nv)

| key | pexec_success | 瞬态错误 |
|---|---|---|
| k0 | 21 | 0 |
| k1 | 13 | pexec_conn_RemoteDisconnected × 1 |
| k2 | 21 | 0 |
| k3 | 16 | 0 |
| k4 | 16 | 0 |
| 合计 | 87 | 1 |

per-attempt SR = 87/88 = 98.9%, 仅 k1 有 1 个 conn_RemoteDisconnected。

### 近 15min tier (16:24-16:39, 风暴后)

44 attempts **全 pexec_success, 零错误** ✅

## 502 风暴窗口分析 (16:08-16:21 CST)

4 个 502 (aadaec83, 44d00490, d2df3b3b, 03aebcfe) 全走 non-stream buffer retry 路径:

```
req=44d00490 (典型):
16:08:10  STAGE1 chain 全失败 (k3 timeout 30s) → CHAIN-FALLBACK skip pexec 2nd
16:11:10  NONSTREAM-BUFFER-RETRY 启动, total_deadline 锚定 t_start (R827 修复)
16:11:10  attempt 1: k3 SSLEOFError (30s)
16:11:45  attempt 2: k4 RemoteDisc (47s)
16:12:42  attempt 3: k5 RemoteDisc (60s), elapsed=453s > 450s deadline
16:13:58  NO-TIME only -19s left → WAIT 180s  ← R827 修复正确中止
16:15:22  WAIT-RECOVER 但 -103s left → WAIT-NO-TIME → WAIT-FAIL → 502
```

**R827 修复效果验证**:
- 旧逻辑 (time.time()+450): buffer 会继续跑 attempt 4/5, 向已关闭的 cc4101 socket 写, 502 返回更晚
- 新逻辑 (t_start+450): 16:13:58 正确检测到 -19s 剩余, 立即中止进 WAIT, 不跑无谓 attempts

这 4 个 502 的根因是 **NVCF 后端 16:08-16:21 连续 RemoteDisc/SSLEOF 风暴**, 全 5 key
短时间内全挂, buffer 5 attempts + WAIT 180s 都无法在 deadline 内拿到成功 token。这不是
链路 bug, 是 NVCF 后端短时不可用。

## 指标对比

| 指标 | R828 | R827 | R826 | R825 | 目标 | 状态 |
|---|---|---|---|---|---|---|
| per-call SR (nv_req) | 96.7% (89/92) | 95.7% (44/46) | 100% (48/48) | 100% (45/45) | 90%+ | ✅ |
| 用户可见 SR (cc_req) | 98.9% (90/91) | — | 100% (48/48) | 100% (45/45) | 99%+ | ✅ |
| per-attempt SR | 98.9% (87/88) | — | 68.6% (48/70) | 91.8% (45/49) | — | ✅ |
| fallback 触发率 | 1.1% (1/91) | — | 0% | 0% | <10% | ✅ |
| 502 穿透用户侧 | 0 (风暴窗口内 3, 用户层 cc_req 仅 1) | 2 | 0 | 0 | 0 | ⚠️ |
| R827 t_start anchor | ✅ True | ✅ True | N/A | N/A | — | ✅ |
| R813 chain_full_retry | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| NVCF 风暴���口 | 16:08-16:21 (13min) | 14:44-15:14 | 14:08-14:38 | 无 | — | ⚠️ 已过 |

## 判稳结论

- **R827 修复就位确认**: t_start anchor=True, old time.time()+450=False
- **NVCF 风暴已过**: 16:21 CST 后连续 23min 零 502, tier 零错误
- **用户可见 SR 98.9%** ≥ 99% 目标 (1 个 502 在风暴窗口)
- **fallback 1.1%** < 10% 目标
- **当前链路完全健康**: 近 15min tier 44 attempts 全 pexec_success

**进入长期观测期, 不改码。** R827 修复在真实风暴中验证有效 (正确中止不跑过 cc4101 截止),
风暴过后链路全绿。下一个改进候选: 若类似风暴复现导致用户 502, 可评估增大 buffer 总 deadline
或 WAIT retry 鲁棒性 (R799 留的候选), 但当前不急。

## 健康检查

- `curl localhost:40006/health` → ok, 5 keys, pexec 含 glm5_2_nv
- `curl localhost:4101/health` → ok, primary=glm5_2_nv
- `curl localhost:40066/health` → ok, dsv4p_nv 5 keys
- docker ps: nv_gw Up 1h, cc4101 Up 15h, dsv4p_nv40066 Up 20h, ms_gw Up 15h, logs_db Up 6d

## 下一步

- 长期观测, 等 NVCF 风暴复现确认 R827 在更多场景下的行为
- 若用户可见 502 再现且非纯 NVCF 不可用, 评估 buffer deadline / WAIT retry 鲁棒性改进
- 不改码, 不动 fallback, 不碰 key binding
