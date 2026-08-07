# R1081: dsv4f0731_nv self-opt — NOP (NVCF 风暴持续缓释, 30min 窗口 SR 97.9% 稳定健康)

日期: 2026-08-07 ~09:24 (BJT) = ~01:24 UTC

## 1. 数据 (30min 窗口 采集 + attempt 级分析)

### 主指标
- **SR = 97.9% (138/141)**, avg=17121ms, p50=9590ms, **p95=68993ms**
- 30min 错误: stream_absolute_cap=2 (avg 155678ms), all_tiers_exhausted=1 (avg 180061ms)
- **429 计数 = 0** (无 429 冷却杠杆)
- upstream_type: 100% nvcf_pexec, **integrate 0 请求**
- finish_reason: tool_calls=120, stop=18 (正常)
- tier_attempts: 窗口内无 attempt 行 (0 失败, 全请求直接命中成功)

### per-key 200 延迟 (全部健康)
| key | total | ok | avg_ok_ms | max_ms |
|---|---|---|---|---|
| k0 | 25 | 25 | 10165 | 18463 |
| k1 | 32 | 32 | 17640 | 73832 |
| k2 | 27 | 27 | 14742 | 45579 |
| k3 | 27 | 27 | 12113 | 42809 |
| k4 | 27 | 27 | 14034 | 27542 |

**无单 key 劣化** — 5 key 全部 100% 出 200, 延迟接近 (10-17.6s)。

### per-key 错误 (30min)
| key | error_type | count | avg_ms |
|---|---|---|---|
| k0 | all_tiers_exhausted | 1 | 180061 |
| k2 | stream_absolute_cap | 1 | 153015 |
| k3 | stream_absolute_cap | 1 | 158341 |

仅 3 次错误跨 k0/k2/k3 分散, **k1 0 错误**。均为缓冲帽/预算耗尽类 (上游长时间 hold 后剪断), 非 key 级故障。

### key_cycle_429s 分布
0=10, 1=125, 2=4, 3=1, 4=1

**k1=125 为轮转伪影**, 与 R1080 (k1=137) 一致: k1 为轮转首 key, 每次请求先 429-probe 后 fast-break 切走, 但 k1 本窗 0 错误、32×200 全成功 → 非 k1 真实劣化, 系统 fast-break/cycling 正常消化。

### 趋势 (持续上行, 恢复稳定)
| 时段 | total | ok | err | SR |
|---|---|---|---|---|
| 22:00 | 96 | 78 | 18 | 81.3% |
| 23:00 | 208 | 191 | 17 | 91.8% |
| 00:00 | 291 | 282 | 9 | 96.9% |
| 01:00 | 112 | 109 | 3 | 97.3% |
| 30min | 141 | 138 | 3 | **97.9%** |
| 6h | 1309 | 1227 | 82 | **93.7%** |

24h all_tiers_exhausted=458 (历史累计, 非当前风暴)。

### fallback 日志 (hm4104, 最近 5min)
09:19-09:22 见 content_filter zombie + PRIMARY-BREAKER-SKIP + FALLBACK-STREAM 数次 — 为 hm4104 侧主链路 content_filter 处理触发, 与 dsv4f0731_nv 上游错误不同源, 属 hm4104 adapter 自身行为, 非本容器 502/风暴。

## 2. 根因判定 (改前必有数据)

延续 R1021-R1080 的 **NVCF 模型特异性劣化风暴** (function_id 52e1ddb6) 缓释期:
1. **SR 97.9%, 6h 93.7% 且逐小时上行** (81.3%→97.3%) — 上游显著恢复且稳定。
2. **错误仅 3 次/30min** (stream_absolute_cap=2 缓冲帽 + all_tiers_exhausted=1), 跨 key 分散, 无单 key 劣化。
3. **429 = 0**, fast-break 先耗尽 key, 无 429 冷却杠杆空间。
4. **k1 key_cycle_429s=125 为轮转伪影** (R1080 同款), k1 本窗 0 错误 32×200 → 非真实劣化。
5. **pexec_success 链路健康** (avg 延迟 10-17.6s), 故障仅在 NVCF function 远端的偶发长 hold。

## 3. 决策: NOP (无参数修改)

SR 97.9% > 95% NOP 阈值, 延迟稳定, 无异常错误, 趋势上行。无单参数 lever 有数据支撑需调整。
维持 R1067 最佳配置 (UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET=180, CONN fast-break=5,
KEY_COOLDOWN=30, TIER_COOLDOWN=90, 429 base/max=120, EMPTY_200 fast-break=3), 等待 NVCF
deepseek-v4-flash-0731 function 完全恢复。

**不采取 k1 429 冷却调整**: key_cycle_429s=125 虽高, 但 k1 0 错误 + 32×200 全成功证实为轮转
伪影而非真实 429 劣化; 提高 NVU_KEYMGR_429_COOLDOWN 会减少 k1 重试机会, 无实际收益。

## 4. 验证

- [x] `/health` OK, 5 keys, proxy_role=passthrough, port=40666
- [x] 容器 dsvf0731_nv40666 Up 16 hours, 无重启, 无 env 改动
- [x] 30min SR=97.9%, 6h SR=93.7%, 延迟稳定 (p50 9.6s)
- [x] hm4104 fallback 为 content_filter adapter 行为, 与本容器上游无关

## 5. 下一步建议

- 上游持续恢复中, 保持 NOP 观察。若 6h SR 稳定 >95% 连续 2-3 轮, 可延长 NOP 轮间隔。
- 若 RD 风暴 (NVCFPexecRemoteDisconnected) 有回归且 6h SR<90%, 再评估 integrate.api 旁路
  (NV_KEY_INTEGRATE_KEYS) — 当前无需干预。
- 关注 hm4104 content_filter zombie 是否持续: 若为 ms_gw 侧内容过滤问题, 属 adapter/ms 侧工单,
  不在本容器 env 范围。