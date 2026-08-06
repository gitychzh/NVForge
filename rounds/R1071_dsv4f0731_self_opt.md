# R1071: NVCF 模型特异性劣化风暴延续 (第2轮 post-R1067) — NOP (无参数修改)

> 时间: 2026-08-06 18:2x BJT (10:2x UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Flash 0731 via NVCF)
> 状态: **NOP (无参数修改)** — R1067 (CONN_ERR_FAST_BREAK=5) 已落地并验证正向,
>   R1069 budget 放宽已回滚 (R1070)。本轮全 5 key 同时劣化风暴持续, 无单 key / 无
>   单参数绑定约束, 维持 NOP 等待 NVCF 侧恢复。

## 1. 背景 (改前必有数据)

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 36, 200=13, 失败=23, **SR=36.1%**
- Avg 151075ms, p50 178990ms, p95 300979ms, max 317408ms
- 429: 0 计数
- upstream_type: nvcf_pexec 24 (200=13, **SR=54.2%**, avg=97705ms), ms_fallback 12
  (200=0, **SR=0%**, avg=257817ms)
- finish_reason: tool_calls=11, stop=2 (仅 13 个 200 正常完成)

### 错误分类 (30min, pre-run)
| error_type | count | avg_ms |
|---|---|---|
| buffer_exhausted | 12 | 257817 |
| all_tiers_exhausted | 6 | 179709 |
| zombie_empty_completion | 4 | 15913 |
| client_gone_during_flush | 1 | 311361 |

### per-key 错误 (1h, 本轮直接查询 nv_tier_attempts)
| key | RD | empty_200 | 529 | Tm | total |
|---|---|---|---|---|---|
| 0 | 6 | 2 | 9 | 4 | 22 |
| 1 | 12 | 6 | 6 | 1 | 25 |
| 2 | 7 | 7 | 3 | 1 | 19 |
| 3 | 8 | 3 | 7 | 2 | 21 |
| 4 | 14 | 0 | 7 | 4 | 25 |

→ **错误跨全 5 key 均匀分散 (k0:22, k1:25, k2:19, k3:21, k4:25)**, 非单 key 劣化。
1h 上游错误: NVCFPexecRemoteDisconnected=48, 529_nv_overloaded=32, empty_200=18,
NVCFPexecTimeout=12, budget_exhausted_after_connect=2, 504=1。

### 关键证据
1. **ms_fallback 本窗 0% (0/12, avg 257s)** — fallback 路径 (→ ms_gw) 完全失效, 每次
   burn ~257s buffer。fallback 不能兜底 → 调 primary 参数无助吞吐。
2. **0 实际 429** (tier_attempts 无 429 行); key_cycle_429s k0=27 为轮转顺序伪影
   (k0 首试, 劣化时最先被 429'd), 非 k0 专属问题。
3. **glm5_2_nv 同容器同 key 同出口 1h 错误 = 0** → 网络/mihomo/key/出口路径健康,
   故障仅在 dsv4f0731_nv 具体 function 远端执行层 (模型特异性, 延续 R1021-R1070)。
4. **6h SR=46.2% (240/520)**, 3h 逐小时 38%/51%/42%/44% — 稳定在 40-50% 劣化带,
   非瞬时暴跌亦非恢复。

## 2. 决策: NOP (无参数修改)

全 5 key 同时劣化 (RD+empty_200+529+timeout 混合风暴), 无单 key 劣化可调 key 冷却,
0 实际 429 无冷却窗口问题, fast-break/budget 已按 R1067/R1070 调整到位。绑定约束是
NVCF 远端 function 执行层, 非容器 env。R1067 (CONN_ERR_FAST_BREAK=5) 已给出最佳可及
收益 (SR 31→46%), 无进一步容器参数 lever。

**不采取 NVU_EMPTY_200_FASTBREAK 3→1 (R1070 next-step)**: empty_200 仅占 1h 错误 16%
(18/113), 且跨 key 分散 (k1:6, k2:7, k3:3, k0:2), 无单 key 连续空 200 序列; 改 1 会
将瞬时空 200 误判为该 key 永久失效, 加速 key 轮转反而可能降低命中健康 key 概率。
数据不支持此 lever 为绑定约束。

## 3. 验证

- [x] `docker exec dsvf0731_nv40666 env | grep CONN_ERR_FAST_BREAK` = `NVU_CONN_ERR_FAST_BREAK=5`
- [x] `docker exec dsvf0731_nv40666 env | grep NVU_TIER_BUDGET_DSV4F0731_NV` = 180 (R1070 已回滚)
- [x] `/health` = {"status":"ok", 5 keys} (端口 40666)
- [x] 容器 Up (53 min), 本轮无配置改动, 无需重启

## 4. 当前状态 (30min)

- 30min SR: **36.1%** (13/36)
- Avg / P50 / P95: 151075 / 178990 / 300979 ms
- 错误分布: buffer_exhausted=12 (ms_fallback), all_tiers_exhausted=6,
  zombie_empty_completion=4, client_gone_during_flush=1
- Fallback: hm4104 持续 PRIMARY-FAIL-STREAM → FALLBACK-STREAM (fallback 亦 0% 成功)
- upstream: nvcf_pexec 24/200=54.2%, ms_fallback 12/200=0%

## 5. 上次修改效果 (R1070 回滚)

| 指标 | R1069 基线 | R1070 (回滚后) | 当前 |
|---|---|---|---|
| 30min/1h SR | 58.8% | 53.8% | 36.1% |
| 逐小时 SR | ~48% | ~42% | 38-51% |
| 逐小时 ATE | 16 | 31 | 10-31 |

→ R1070 回滚 budget 至 180 正确 (budget 非绑定约束, 避免无谓长等待)。当前 SR 回落
至 ~36% 属风暴强度波动, 非回滚副作用 (fast-break=5 仍生效, 上游错误跨全 key 分散)。

## 6. 根因结论与下一步建议

- **根因**: NVCF deepseek-v4-flash 0731 function 侧临时劣化 (全 5 key 同时
  RD+empty_200+529 风暴), 模型特异性第 46 次成立 (glm5_2_nv 1h 0 错误)。非本容器参数可解。
- **下一步**:
  1. 若持续 >2h SR<40% 且 ms_fallback 仍 0%, 严重性升级 — 建议评估切换 primary 到
     dsv4f_nv (04 版本) 或 dsv4p_nv, 绕过该劣化 function (需协调 CC/agent 侧, 非本容器
     单独可决)。
  2. 优先恢复 ms_fallback 路径 (当前 0%, 每次 burn ~257s) — 若 fallback 可用, 用户侧
     至少保活; 但此为 ms_gw 侧工单, 不在本容器 env 范围。
  3. 持续比对 glm5_2_nv (0 错误): 若其也开始劣化 → 链路级问题 (非 model-specific),
     需重新审视 mihomo/key/出口。