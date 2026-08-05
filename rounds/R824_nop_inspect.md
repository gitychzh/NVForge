# R824 (NOP 巡检轮 — 链路全稳, 全指标优于目标, 2026-08-05 14:55 CST)

上轮 R823 NOP. 本轮 30min 真实窗口 (14:25-14:55 CST) 全指标优于目标, NVCF 后端健康
(buffer 全 1-attempt 成功, 无自愈 retry 触发). 不改码.

## 30min 真实窗口数据 (cc4101-primary, cc2 请求)

### nv_requests (per-call SR)
| status | count |
|---|---|
| 200 | 47 |

per-call SR = 100% (47/47) ✅, 零错误 (status!=200 → 0 rows)

### cc_requests (用户可见, 含 fallback)
| total | ok | s502 | s499 | fb | sr | fb_pct |
|---|---|---|---|---|---|---|
| 1250 | 1242 | 0 | 8 | 20 | 99.4% | 1.6% |

零 502 穿透, 8×499 (cc2 SDK 自断边界 case), 20×fallback 全兜住 ✅

### per-key tier attempts (glm5_2_nv)
| key | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| pexec_success | 13 | 4 | 13 | 7 | 10 |

47/47 = 100% pexec_success, 零错误 ✅

### buffer 行为
本窗口 30min 内所有 buffer session 均 1-attempt 成功 (10-34s), 无 EXEC-FAIL/BACKOFF/自愈 retry 触发.
NVCF 后端本窗口健康, 链路全程在 buffer 第 1 attempt 内完成.

## R813 修复就位铁证
docker exec nv_gw python3 -c "import gateway.buffer_stream as b, inspect;
  print('chain_full_retry:', 'chain_full_retry' in inspect.getsource(b.BufferStreamSession.run))"
→ chain_full_retry: True ✅

## 健康检查
- curl localhost:40006/health → ok, 5 keys, pexec models 含 glm5_2_nv ✅
- curl localhost:4101/health → ok, primary=glm5_2_nv ✅
- docker ps: nv_gw Up 2h, cc4101 Up 13h, dsv4p_nv40066 Up 18h, ms_gw Up 13h ✅

## 注入数据说明
注入轮前数据中 RemoteDisc×20 + 529×4 + all_tiers_exhausted×6 是 R819 末尾 NVCF 风暴早期窗口
(13:17-13:47) 残留, 当前真实窗口 (14:25-14:55) 完全干净. dsv4f0731_nv SR=57.1% 是 hermes caller
另一条链路, 不在 cc2 优化范围 (cc2 优化目标是 glm5_2_nv).

## 指标对比
| 指标 | R824 | R823 | R822 | 目标 | 状态 |
|---|---|---|---|---|---|
| nv_gw per-call SR | 100% (47/47) | 100% (42/42) | 100% (50/50) | 90%+ | ✅ |
| per-key tier SR | 100% (47/47) | 100% (42/42) | 100% (53/53) | 90%+ | ✅ |
| 用户可见 SR | 99.4% (1242/1250) | 99.4% (1250/1258) | 100% (52/52) | 99%+ | ✅ |
| fallback 触发率 | 1.6% (20/1250) | 1.6% (20/1258) | 1.9% (1/52) | <10% | ✅ |
| 502 穿透用户侧 | 0 | 0 | 0 | 0 | ✅ |
| R813 chain_full_retry | ✅ True | ✅ | ✅ | — | ✅ |
| 新错误类型 | 无 | 无 | 无 | 无 | ✅ |

## 判稳结论
链路完全稳定, 全指标优于目标. 进入长期观测期, 不改码.

## 下一步
- R825: 继续长期观测. 关注 NVCF 风暴频率; fallback<10%; per-key tier SR 90%+.
- R813 修复已充分验证, 进入纯观测期.
