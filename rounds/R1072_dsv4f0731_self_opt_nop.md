# R1072: dsv4f0731_nv self-opt NOP — NVCF 模型特异性劣化风暴第 47 轮 (全 5 key, 无容器 lever)

> 时间: 2026-08-06 18:5x BJT (10:5x UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Flash 0731 via NVCF)
> 状态: **NOP (无参数修改)** — 延续 R1071/R1021-R1070 的模型特异性劣化风暴,
>   R1067 (CONN_ERR_FAST_BREAK=5) 已落地为最佳可及收益, 无新增单参数 lever。

## 1. 背景 (改前必有数据)

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 31, 200=12, 失败=19, **SR=38.7%**
- Avg 159491ms, p50 175729ms, p95 281141ms, max 565348ms
- 429: 0 实际计数; key_cycle_429s 分布均匀 (k0:23, k1:3, k2:2, k3:3) — 轮转伪影
- upstream_type: nvcf_pexec 23 (200=12, **SR=52.2%**, avg=113879ms), ms_fallback 7
  (200=0, **SR=0%**, avg=235829ms)

### 错误分类 (30min)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 9 | 232028 |
| buffer_exhausted | 7 | 235829 |
| zombie_empty_completion | 2 | 13164 |
| client_gone_during_flush | 1 | 311361 |

### per-key 错误 (1h, nv_tier_attempts)
| key | RD | empty_200 | 529 | Tm | 504 | total |
|---|---|---|---|---|---|---|
| 0 | 6 | 13 | 13 | 6 | 2 | 41 |
| 1 | 24 | 12 | 6 | 5 | 1 | 48 |
| 2 | 20 | 11 | 3 | 3 | 3 | 40 |
| 3 | 29 | 7 | 9 | 3 | 2 | 51 |
| 4 | 39 | 2 | 8 | 6 | 4 | 59 |

→ **错误跨全 5 key 均匀分散 (k0:41, k1:48, k2:40, k3:51, k4:59)**, 无单 key 劣化。
1h 上游错误: NVCFPexecRemoteDisconnected=118 主导, 529_nv_overloaded=39, empty_200=45,
NVCFPexecTimeout=23, 504_nv_gateway_timeout=12。混合风暴, 延续 R1071。

### 关键证据
1. **2h nv_requests per-key SR**: k0=33.9%(20/59), k1=80.8%(21/26), k2=72.7%(16/22),
   k3=80.6%(29/36), k4=84.2%(16/19) — key 间有差异 (k0 因轮转首试被 429'd 最多), 但
   无任何 key 为绑定瓶颈; k0 的 8 个 all_tiers_exhausted (30min) 是首试被劣化风暴命中,
   非 k0 专属。
2. **ms_fallback 仍旧 0%** (7/7 失败, avg 236s) — fallback 路径 (→ ms_gw) 完全失效,
   每次 burn ~236s buffer。fallback 不能兜底 → 调 primary 参数无助吞吐。
3. **glm5_2_nv 同容器同 key 同出口 1h SR=82.4% (14/17)** vs dsv4f0731_nv 38.4% →
   网络/mihomo/key/出口路径健康, 故障仅在 dsv4f0731_nv 具体 function 远端执行层
   (模型特异性, 第 47 次成立)。
4. **3h 逐小时**: 08:00 SR=41.7%(43/103), 09:00 SR=51.2%(66/129), 10:00 SR=39.4%(28/71)
   — 稳定在 40-50% 劣化带, 非瞬时暴跌亦非恢复。

## 2. 决策: NOP (无参数修改)

全 5 key 同时劣化 (RD+empty_200+529+timeout 混合风暴), 无单 key 劣化可调 key 冷却,
0 实际 429 无冷却窗口问题, fast-break/budget 已按 R1067/R1070 调整到位。绑定约束是
NVCF 远端 deepseek-v4-flash 0731 function 执行层, 非容器 env。R1067
(CONN_ERR_FAST_BREAK=5) 已给出最佳可及收益 (SR 31→46%), 无进一步容器参数 lever。

**不采取 NVU_EMPTY_200_FASTBREAK 3→1**: empty_200 占 1h 错误 18% (45/239), 跨 key
分散, 无单 key 连续空 200 序列; 改 1 会将瞬时空 200 误判为该 key 永久失效, 加速 key
轮转反降命中健康 key 概率。数据不支持此 lever 为绑定约束。

## 3. 验证

- [x] `docker exec dsvf0731_nv40666 env` 确认:
      `NVU_CONN_ERR_FAST_BREAK=5`, `NVU_TIER_BUDGET_DSV4F0731_NV=180`,
      `NVU_EMPTY_200_FASTBREAK=3`, `NVU_PEXEC_TIMEOUT_FASTBREAK=3`
- [x] `/health` = {"status":"ok", 5 keys, nvcf_pexec_models 含 dsv4f0731_nv} (端口 40666)
- [x] 容器 Up (About an hour), 本轮无配置改动, 无需重启

## 4. 当前状态 (30min)

- 30min SR: **38.7%** (12/31)
- Avg / P50 / P95: 159491 / 175729 / 281141 ms
- 错误分布: all_tiers_exhausted=9, buffer_exhausted=7 (ms_fallback),
  zombie_empty_completion=2, client_gone_during_flush=1
- Fallback: hm4104 持续 PRIMARY-FAIL-STREAM → FALLBACK-STREAM (fallback 亦 0% 成功)
- upstream: nvcf_pexec 23/200=52.2%, ms_fallback 7/200=0%

## 5. 上次修改效果 (R1067 CONN_ERR_FAST_BREAK=5 持续)

| 指标 | R1065/R1066 基线 | R1067 后 | 当前 (R1072) |
|---|---|---|---|
| 30min/1h SR | ~36-39% | 31→47% | 38.7% |
| 逐小时 SR | ~40% | ~46% | 39-51% |
| ATE | 高 | 减半 | 9 (30min) |

→ CONN_ERR_FAST_BREAK=5 的收益 (遍历全 5 key 命中瞬时健康 key) 仍在, 当前 SR 波动
属风暴强度变化, 无回退。

## 6. 根因结论与下一步建议

- **根因**: NVCF deepseek-v4-flash 0731 function 侧临时劣化 (全 5 key 同时
  RD+empty_200+529 风暴), 模型特异性第 47 次成立 (glm5_2_nv 同链路 SR=82.4%)。
  非本容器参数可解。
- **下一步**:
  1. 若持续 >2h SR<40% 且 ms_fallback 仍 0%, 严重性升级 — 建议评估切换 primary 到
     dsv4f_nv (04 版本) 或 dsv4p_nv, 绕过该劣化 function (需协调 CC/agent 侧, 非本容器
     单独可决)。
  2. 优先恢复 ms_fallback 路径 (当前 0%, 每次 burn ~236s) — 若 fallback 可用, 用户侧
     至少保活; 但此为 ms_gw 侧工单, 不在本容器 env 范围。
  3. 持续比对 glm5_2_nv (1h 82.4%): 若其也开始劣化 → 链路级问题 (非 model-specific),
     需重新审视 mihomo/key/出口。