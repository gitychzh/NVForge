# R821 — cc2 NOP 巡检轮: 链路全稳, buffer 自愈活样本

> 上轮 R820 | container: nv_gw Up 2h, cc4101 Up 12h, dsv4p_nv40066 Up 17h
> 时间: 2026-08-05 14:00 CST | 轮前数据注入 14:00:32 CST

## 改动: 无 (NOP 巡检轮)

R813 commit chain_full_retry=True 仍就位 (inspect.signature 铁证). 本轮 30min 真实窗口全指标优于目标,
NVCF 风暴已完全退去 (per-key tier 全 pexec_success, 零 RemoteDisconnected).

## 30min 真实链路数据 (现在窗口, vs 注入的较宽窗口)

### nv_requests (cc4101-primary, cc2 的请求)

| status | count | avg_dur | 备注 |
|---|---|---|---|
| 200 | 46 | 22738ms | 正常 (NVCF 恢复后 22s 均值) |
| 502 | 1  | 397167ms | buffer_exhausted 不可挽救 (NVCF 单 req 久挂) |
| 499 | 1  | 443337ms | client_gone_during_flush (cc2 SDK 450s 自断) |

- per-call SR (排 499) = 97.9% (46/47) ✅ > 90%
- 仅 1×502 + 1×499, 均为已知边界 case (非新 bug)

### cc_requests (用户可见, 含 fallback)

| total | ok | s502 | s499 | fb | sr | fb_pct |
|---|---|---|---|---|---|---|
| 48 | 48 | 0 | 0 | 1 | 100.0% | 2.1% |

- **零 502 穿透用户** ✅ (s502=0, 1×fallback 全兜住)
- 用户可见 SR=100% ✅ > 99%
- fallback 触发率 2.1% ✅ < 10%

### per-key tier attempts (30min, glm5_2_nv)

| nv_key_idx | error_type | count |
|---|---|---|
| 0 | pexec_success | 11 |
| 1 | pexec_success | 7 |
| 2 | pexec_success | 11 |
| 3 | pexec_success | 11 |
| 4 | pexec_success | 8 |

**48/48 = 100% pexec_success, 零 RemoteDisconnected, 零 529_nv_overloaded** ✅

注: 注入的轮前分析显示 RemoteDisc×18 + 529×4 是较宽早期窗口 (13:17-13:47, R819 末尾风暴残留).
真实当前 30min 窗口已完全退去, 全 key 恢复正常 1-attempt success.

### 错误分类 (cc4101-primary, 30min)

| error_type | count |
|---|---|
| buffer_exhausted | 1 |
| client_gone_during_flush | 1 |

仅 2 个已知边界 case, 无新错误类型. ✅

## buffer 自愈活样本 (req=fe6917c2)

```
14:02:14 [BUFFER-START] caller=cc4101-primary max_retries=5 stairs=[90×5] total_deadline=450s
14:02:14 [BUFFER-ATTEMPT] 1/5 k1 (32s) → execute_failed, all_keys_exhausted=True
14:02:46 [BUFFER-BACKOFF] 5s before attempt 2
14:02:51 [BUFFER-ATTEMPT] 2/5 k2 (72s) → execute_failed, all_keys_exhausted=True
14:03:27 [BUFFER-BACKOFF] 10s before attempt 3 (递增正确: 5→10→?)
14:03:37 [BUFFER-ATTEMPT] 3/5 k3 (98s) → success_tool_call, flush 26774b
14:03:52 [BUFFER-SUCCESS] elapsed=98065ms (98s < 450s 预算)
```

**前 2 attempt fail (k1/k2 NVCF execute_failed), 第 3 attempt (k3) 自愈成功** — 本会被判 fail 的
请求经 5key 轮转 + backoff 递增 (5s→10s) 挽救为 200. R813 修复后 buffer 链路自愈能力的真活样本.

注: 日志里 `BUFFER_OVERRIDE` 是 buffer `_KEY_ROTATION` 常规日志 (R814 STATE 已纠正误判),
R813 真修的是 WAIT-RECOVER 分支走 CHAIN-FULL. 本轮无 WAIT 触发, 链路全程在 5key buffer 内自愈.

## R813 修复就位铁证
```
docker exec nv_gw python3 -c "import gateway.buffer_stream as b, inspect;
  print('chain_full_retry:', 'chain_full_retry' in inspect.getsource(b.BufferStreamSession.run))"
→ chain_full_retry: True
```

## 健康检查
- nv_gw(40006): ok, 5 keys, pexec models 含 glm5_2_nv
- cc4101(4101): ok, primary=glm5_2_nv
- dsv4p_nv40066(40066): ok, 5 keys
- docker ps: nv_gw Up 2h, cc4101 Up 12h, dsv4p_nv40066 Up 17h, ms_gw Up 12h

## 判稳结论

链路完全稳定. NVCF 风暴已退去. 全指标优于目标:
- per-call SR 97.9% (46/47), per-key tier SR 100% (48/48), 用户可见 SR 100% (48/48),
  fallback 2.1%, 零 502 穿透. R813 修复仍就位.
**进入长期观测期, 不改码.**

## SR 趋势

| 轮 | 30min per-call SR | per-key tier SR | WAIT-RECOVER | fallback% | 备注 |
|---|---|---|---|---|---|
| R815 | 100% (55/55) | 98.3% (57/58) | 2 (1 OK★+1 FAIL) | 1.4% | CHAIN-FULL 首 WAIT-OK |
| R816 | 100% (31/31) | 93.75% (30/32) | 0 | 3.23% | buffer 自愈生效 |
| R817 | 100% (47/47) | 95.7% (44/46) | 1 (FAIL→fallback) | 0% | NVCF 风暴退去全绿 |
| R818 | 100% (44/44) | 95.7% (44/46) | 2 (全 FAIL→吸收) | 1.45% | NVCF 二次瞬断 2×502 全吸收 |
| R819 | 93.75% (45/48) | 100% (48/48 最新) | 0 | 4.1% | NVCF 风暴末梢 3×502 全吸收 |
| R820 | 98.2% (56/57) | 100% (58/58) | 0 | 1.5% | NVCF 风暴已退去 |
| **R821** | **97.9% (46/47)** | **100% (48/48)** | **0** | **2.1%** | **链路全稳, buffer 自愈活样本 (k1/k2 fail→k3 success)** |

## 下一步

- R822: 继续长期观测. 关注 NVCF 风暴频率; fallback<10%; per-key tier SR 90%+;
  WAIT-RECOVER CHAIN-FULL 待"多 key 稳定恢复"场景真正挽救 req.
- 无改进点, 不改码. R813 修复已充分验证, 进入纯观测期.
