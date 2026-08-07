# R1137: dsv4f0731_nv self-opt NOP

**日期**: 2026-08-08 04:06 UTC
**容器**: dsvf0731_nv40666 (port 40666, HM2, DeepSeek V4 Pro via NVCF pexec)
**模型**: dsv4f0731_nv
**轮次类型**: NOP (数据正常，不改参数)

## 当前参数（live env 实测）
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
| NV_INTEGRATE_EGRESS_IPS | 5× 134.195.x.x |
| NV_INTEGRATE_PROXY_URLS | 5× socks5h://172.18.0.1:789x |
| NVU_PEER_FALLBACK_ENABLED | 0 |

## 数据（30min 窗口，脚本 04:06 UTC）
- **总量**: 200 | **成功**: 200 | **错误**: 0 | **fallback**: 0 → **SR = 100%**
- **延迟**: avg=9583ms, p50=8256ms, p95=28630ms
- **错误分类**: (无)
- **per-key 200 延迟**（全部健康，负载均衡，无劣化 key）:
  - key0: 40 req, avg=9988ms
  - key1: 41 req, avg=8684ms
  - key2: 40 req, avg=10332ms
  - key3: 38 req, avg=8300ms
  - key4: 41 req, avg=10543ms
- **upstream_type**: nvcf_pexec 200/200 OK (100%)，无 integrate 流量
- **finish_reason**: tool_calls=177, stop=23
- **429 计数**: 0
- **key_cycle_429s**: key0=82, key1=118（历史累积计数，非本窗口错误；本窗口 0 次 429）
- **tier_attempts**: (无)

## 趋势
- **6h**: 1841 total / 1831 ok / 10 err / 0 fb = **99.5%**
- **3h 每小时**:
  - 17:00: 252/246 (97.6%)
  - 18:00: 347/346 (99.7%)
  - 19:00: 349/348 (99.7%)
  - 20:00: 42/42 (100%)
- **24h all_tiers_exhausted**: 110（跨 tier 历史汇总，本窗口/本 tier 为 0）
- **fallback 日志（hm4104, 最近5min）**: 无

## 容器状态
- dsvf0731_nv40666: Up 2 hours
- nv_gw: Up 25 hours
- hm4104: Up 3 days
- /health: status ok, proxy_role=passthrough, 5 keys, 5 model tiers, port 40666

## 结论
30min SR=100%，零错误、零 fallback、零 429，per-key 延迟/负载高度均衡（各 38~41 req，8.3~10.5s，无劣化 key），all upstream=pexec 100% 成功，6h SR=99.5%。链路完全健康。

**决策：NOP，不改任何参数。** 100% SR 下修改参数违反"改前必有数据"铁律。

## 上次修改效果 (R1136 → R1137)
R1136 (04:04) 报 SR=100% (201/201)，avg=9467ms。本轮 (04:06) SR=100% (200/200)，avg=9583ms（+116ms，噪声内）。数据窗口高度重叠，系统延续稳定态，无退化。

## 下一步建议
链路上游持续健康。继续观察 30min 窗口：
- 若 pexec 死链重新聚集（≥3/30min 或单 key 集中）→ 评估源码级 socket.timeout→continue 修复
- 429 回升 → KEY_COOLDOWN_S 30→60s
- IncompleteRead/SSLEOFError 聚集 (≥30/h) → 检查对应 key SOCKS5 端口
- 关注 24h 110 次 all_tiers_exhausted 是否在更宽窗口回升