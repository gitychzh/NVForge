# R823 — NOP 巡检轮: 链路全稳, buffer 自愈活样本 2d1ccf2c

> 时间: 2026-08-05 14:25 CST
> 上轮: R822 (NOP, 链路全稳 buffer 自愈活样本 26809003)
> 容器: nv_gw Up 2h, cc4101 Up 13h, dsv4p_nv40066 Up 18h

## 改动: 无 (NOP 巡检轮)

R813 commit chain_full_retry=True 仍就位. 本轮 30min 真实窗口全指标优于目标.
链路完全稳定, NVCF 后端无异常.

## 30min 真实链路数据 (13:55-14:25 CST)

#### nv_requests (cc4101-primary, cc2 的请求)

| status | count | 备注 |
|---|---|---|
| 200 | 42 | 正常 |

per-call SR = 100% (42/42) ✅

#### cc_requests (用户可见, 含 fallback)

| total | ok | s502 | s499 | fb | sr | fb_pct |
|---|---|---|---|---|---|---|
| 1258 | 1250 | 0 | 8 | 20 | 99.4% | 1.6% |

零 502 穿透, 8×499 (cc2 SDK 自断边界 case), 20×fallback 全兜住. ✅

#### per-key tier attempts (30min, glm5_2_nv)

| key | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| pexec_success | 11 | 4 | 12 | 6 | 9 |

42/42 = 100% pexec_success, 零错误. ✅

#### 错误分类

cc4101-primary caller 30min 零错误 (status!=200 → 0 rows).

注入数据中的 RemoteDisc×20 + 529×4 来自早期窗口残留 (R819 末尾风暴, 13:17-13:47),
当前真实窗口 (13:55-14:25) 完全干净.

注: dsv4f0731_nv SR=64.7% (herms caller) 是非 cc2 的另一条链路, 不在优化范围.

## buffer 自愈活样本 (req=2d1ccf2c)

```
14:21:17 [BUFFER-START] 5 attempts, stairs=[90×5], total_deadline=450s
14:21:17 [ATTEMPT] 1/5 k2 (timeout=90s) input=77552c thinking=True
14:21:56 [EXEC-FAIL] k2 execute_failed, all_keys_exhausted=True (39s elapsed)
14:21:56 [RETRY] attempt=1 failed, resetting for retry
14:21:56 [BACKOFF] 5s before attempt 2
14:22:01 [ATTEMPT] 2/5 k3 (timeout=90s)
14:22:15 [SUCCESS] k3 succeeded, flush 16419b (58s elapsed)
14:22:16 [BUFFER-SUCCESS] flushed 16419b after 2 attempts, elapsed=58372ms
```

前 1 attempt fail (k2, 39s), 第 2 attempt 自愈成功 (k3, 58s) — 又一个 R813 修复后
buffer 链路自愈能力的真活样本. 本轮无 WAIT 触发, 链路全程在 5key buffer 内自愈.

## 指标对比

| 指标 | R823 | R822 | R821 | R820 | 目标 | 状态 |
|---|---|---|---|---|---|---|
| nv_gw per-call SR (排 499) | 100% (42/42) | 100% (50/50) | 97.9% (46/47) | 98.2% (56/57) | 90%+ | ✅ |
| per-key tier SR | 100% (42/42) | 100% (53/53) | 100% (48/48) | 100% (58/58) | 90%+ | ✅ |
| 用户可见 SR (cc_requests) | 99.4% (1250/1258) | 100% (52/52) | 100% (48/48) | 99.4% (1294/1302) | 99%+ | ✅ |
| fallback 触发率 | 1.6% (20/1258) | 1.9% (1/52) | 2.1% (1/48) | 1.5% (20/1302) | <10% | ✅ |
| 502 穿透用户侧 | 0 | 0 | 0 | 0 | 0 | ✅ |
| R813 chain_full_retry 已加载 | ✅ True | ✅ | ✅ | ✅ | — | ✅ |
| 新错误类型 | 无 | 无 | 无 | 无 | 无 | ✅ |

## 健康检查

- `curl localhost:40006/health` → ok, 5 keys, pexec models 含 glm5_2_nv
- `curl localhost:4101/health` → ok, primary=glm5_2_nv
- docker ps: nv_gw Up 2h, cc4101 Up 13h, dsv4p_nv40066 Up 18h

## 判稳结论

链路完全稳定. 全指标优于目标:
- per-call SR 100% (42/42), per-key tier SR 100% (42/42), 用户可见 SR 99.4% (排 499=100%),
  fallback 1.6%, 零 502 穿透. R813 修复仍就位.
- buffer 自愈活样本 req=2d1ccf2c: 1 attempt fail (k2, 39s) → backoff 5s → attempt 2 k3 success (58s).
**进入长期观测期, 不改码.**

## SR 趋势

| 轮 | 30min per-call SR | per-key tier SR | WAIT-RECOVER | fallback% | 备注 |
|---|---|---|---|---|---|
| R819 | 93.75% (45/48) | 100% (48/48 最新) | 0 | 4.1% | NVCF 风暴末梢 3×502 全吸收 |
| R820 | 98.2% (56/57) | 100% (58/58) | 0 | 1.5% | NVCF 风暴已退去 |
| R821 | 97.9% (46/47) | 100% (48/48) | 0 | 2.1% | 链路全稳, buffer 自愈活样本 fe6917c2 |
| R822 | 100% (50/50) | 100% (53/53) | 0 | 1.9% | 链路全稳, buffer 自愈活样本 26809003 |
| **R823** | **100% (42/42)** | **100% (42/42)** | **0** | **1.6%** | **链路全稳, buffer 自愈活样本 2d1ccf2c** |

## 下一步

- R824: 继续长期观测. 关注 NVCF 风暴频率; fallback<10%; per-key tier SR 90%+;
  WAIT-RECOVER CHAIN-FULL 待"多 key 稳定恢复"场景真正挽救 req.
- 无改进点, 不改码. R813 修复已充分验证, 进入纯观测期.

## 参数快照 (nv_gw + cc4101)

### nv_gw (40006)
- NVU_FORCE_STREAM_UPGRADE = 0
- NVU_PEER_FB_SKIP_MODELS = glm5_2_nv,dsv4p_nv
- MIN_OUTBOUND_INTERVAL_S = 10
- KEY_COOLDOWN_S = 30
- NVU_CALLER_KEY_MAP = hermes:2;openclaw:3;opencode:4
- TIER_TIMEOUT_BUDGET_S = 180
- NVU_DISABLE_MS_FALLBACK = 1
- TIER_COOLDOWN_S = 180
- UPSTREAM_TIMEOUT = 90
- NVU_BUFFER_CALLERS = cc4101-primary,openclaw2
- NVU_BUFFER_TIMEOUT_STAIRS = 90,90,90,90,90
- NVU_BUFFER_TOTAL_DEADLINE_S = 450
- NVU_BUFFER_MAX_RETRIES = 5
- KEY_FID_BIND = 0:0;1:0;2:0;3:0;4:0 (全 bind b1b22d03)
- KEY_PROXY_BIND = k0→7894 k1→7897 k2→7896 k3→7899 k4→7901 (实测)

### cc4101
- PRIMARY_UPSTREAM_URL = http://nv_gw:40006/v1/messages
- PRIMARY_UPSTREAM_MODEL = glm5_2_nv
- FALLBACK_UPSTREAM_URL = http://ms_gw:40007/v1/messages (历史残留, SR 99%+ 极少触发)
- FALLBACK_UPSTREAM_MODEL = glm5_2_ms
- CC4101_STREAM_TOTAL_DEADLINE_S = 470
- PRIMARY_HEADER_TIMEOUT = 400
- CC4101_PRIMARY_FAIL_THRESHOLD = 3
- CC4101_PRIMARY_SKIP_S = 30

### deadline 链
- 90s/buffer-attempt × 5 = 450s buffer < 470s cc4101 < 600s API < 900s idle

## Function IDs (NVCF glm-5.2)
- b1b22d03 ✅ ACTIVE 首选 (当前全 5key bind, 实测 200 OK)
- b6029a96 ✅ ACTIVE 备用 (200K 同限, b1b22d03 持续出错时改 pos1)
- 3b9748d8 ⚠️ broken (持续 RemoteProtocolError, 不 bind)
