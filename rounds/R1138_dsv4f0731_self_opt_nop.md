# R1138: dsv4f0731_nv self-opt NOP

**日期**: 2026-08-08 04:08 UTC
**容器**: dsvf0731_nv40666 (port 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
**模型**: dsv4f0731_nv
**轮次类型**: NOP (数据正常，不改参数)

## 当前参数（live env 实测，与上轮一致无漂移）
| 参数 | 值 |
|---|---|
| UPSTREAM_TIMEOUT | 50 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 |
| TIER_COOLDOWN_S | 90 |
| KEY_COOLDOWN_S | 30 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120 |
| NVU_KEYMGR_CONN_BASE_COOLDOWN | 30 |
| NVU_KEYMGR_CONN_FAIL_THRESHOLD | 3 |
| NVU_KEYMGR_CONN_LONG_COOLDOWN | 120 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_CONN_ERR_FAST_BREAK | 5 |
| NVU_PEER_FALLBACK_ENABLED | 0 |
| NV_INTEGRATE_KEYS | 空 (integrate 未启用) |

## 数据（30min 窗口，脚本 04:08 UTC）
- **总量**: 204 | **成功**: 204 | **错误**: 0 | **fallback**: 0 → **SR = 100%**
- **延迟**: avg=9435ms, p50=8227ms, p95=22556ms
- **错误分类**: (无)
- **per-key 200 延迟**（全部健康，负载均衡，无劣化 key）:
  - key0: 40 req, avg=9187ms
  - key1: 42 req, avg=8919ms
  - key2: 40 req, avg=10235ms
  - key3: 39 req, avg=8171ms
  - key4: 43 req, avg=10569ms
- **upstream_type**: nvcf_pexec 204/204 OK (100%)，无 integrate 流量
- **finish_reason**: tool_calls=179, stop=25
- **429 计数**: 0
- **key_cycle_429s**: key0=88, key1=116（历史累积计数，非本窗口错误；本窗口 0 次 429）
- **tier_attempts**: (无)

## 趋势
- **6h**: 1844 total / 1834 ok / 10 err / 0 fb = **99.5%**
- **3h 每小时**:
  - 17:00: 244/239 (98.0%)
  - 18:00: 347/346 (99.7%)
  - 19:00: 349/348 (99.7%)
  - 20:00: 53/53 (100%)
- **24h all_tiers_exhausted**: 109（跨 tier 历史汇总，本窗口/本 tier 为 0，RN1009 修复持续奏效）
- **fallback 日志（hm4104, 最近5min）**: 无

## 容器状态
- dsvf0731_nv40666: Up 2 hours
- nv_gw: Up 25 hours
- hm4104: Up 3 days
- nv_gw_stable: Up 6 days
- ms_gw: Up 3 days
- /health: status ok, proxy_role=passthrough, 5 keys, 5 model tiers, port 40666

## 结论
30min SR=100%，零错误、零 fallback、零 429，per-key 延迟/负载高度均衡（各 39~43 req，8.1~10.5s，无劣化 key），all upstream=pexec 100% 成功，6h SR=99.5%。链路完全健康。

**决策：NOP，不改任何参数。** 100% SR 下修改参数违反"改前必有数据"铁律。

## 上次修改效果 (R1137 → R1138)
R1137 (04:06) 报 SR=100% (200/200)，avg=9583ms。本轮 (04:08) SR=100% (204/204)，avg=9435ms（-148ms，噪声内）。数据窗口高度重叠，系统延续稳定态，无退化。平均延迟连续多轮稳定在 9.4~9.6s 区间。

## 下一步建议
链路上游持续健康（连续 6+ 轮 NOP，SR 稳居 100%）。继续观察 30min 窗口：
- 若 pexec 死链重新聚集（≥3/30min 或单 key 集中）→ 评估源码级 socket.timeout→continue 修复
- 429 回升 → KEY_COOLDOWN_S 30→60s
- IncompleteRead/SSLEOFError 聚集 (≥30/h) → 检查对应 key SOCKS5 端口
- 关注 24h 109 次 all_tiers_exhausted 是否在更宽窗口回升