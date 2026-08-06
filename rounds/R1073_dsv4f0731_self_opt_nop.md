# R1073: dsv4f0731_nv self-opt NOP — NVCF 模型特异性劣化风暴第 48 轮 (全 5 key, 无容器 lever)

> 时间: 2026-08-06 19:5x BJT (11:5x UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Flash 0731 via NVCF)
> 状态: **NOP (无参数修改)** — 延续 R1072/R1071/R1021-R1070 的模型特异性劣化风暴,
>   R1067 (CONN_ERR_FAST_BREAK=5) 已落地为最佳可及收益, 无新增单参数 lever。

## 1. 背景 (改前必有数据)

### 30min 窗口 (pre-run 注入 + 复核) — tier_model=dsv4f0731_nv
- 总量 42, 200=14, 失败=28, **SR=33.3%** (复核: 42|14|167961)
- upstream_type: nvcf_pexec 25 (200=12, **SR=48.0%**, avg=90537), ms_fallback 8
  (200=0, **SR=0%**, avg=270867)
- 429: 0 实际计数; key_cycle_429s 分布 k0:25, k1:3, k2:4, k3:1 — 轮转伪影
- finish_reason: tool_calls 10, stop 2

### 错误分类 (30min, nv_tier_attempts)
| error_type | count | avg_ms |
|---|---|---|
| NVCFPexecRemoteDisconnected | 40 | 49523 |
| 529_nv_overloaded | 18 | - |
| NVCFPexecTimeout | 10 | 39464 |
| empty_200 | 10 | - |
| 504_nv_gateway_timeout | 1 | - |

### per-key 错误 (30min, nv_tier_attempts)
| key | 错误合计 | 主要类型 |
|---|---|---|
| 0 | 13 | 529(7), Tm(2), RD(2), empty(2) |
| 1 | 12 | RD(6), empty(4), 504(1), 529(1) |
| 2 | 16 | 529(5), Tm(4), empty(4), RD(3) |
| 3 | 19 | RD(12), 529(5), Tm(1), 504(1) |
| 4 | 19 | RD(15), Tm(3), 529(1) |

→ **错误跨全 5 key 均匀分散 (13/12/16/19/19)**, 无单 key 劣化。NVCFPexecRemoteDisconnected
主导, 混合 RD+529+timeout+empty_200 风暴, 延续 R1072。

### 关键证据
1. **同链路对照**: glm5_2_nv (同容器同 key 同出口) 30min **SR=70% (7/10)**, 1h
   SR=77.8% (14/18) vs dsv4f0731_nv 33.3% → 网络/mihomo/key/出口路径健康, 故障仅在
   dsv4f0731_nv 具体 function 远端执行层 (模型特异性, 第 48 次成立)。
2. **ms_fallback 仍旧 0%** (8/8 失败, avg 271s) — fallback 路径 (→ ms_gw) 完全失效,
   每次 burn ~271s buffer。fallback 不能兜底 → 调 primary 参数无助吞吐。
3. **3h 逐小时**: 09:00 SR=48.8%(63/129), 10:00 SR=37.8%(28/74), 11:00 SR=28.6%(18/63)
   — 稳定在 30-50% 劣化带, 非瞬时暴跌亦非恢复, 甚至有缓降趋势。
4. **24h ATE**: all_tiers_exhausted **409** 次 — 持续高位, 反映劣化风暴贯穿全天。

## 2. 决策: NOP (无参数修改)

全 5 key 同时劣化 (RD+529+timeout+empty_200 混合风暴), 无单 key 劣化可调 key 冷却,
0 实际 429 无冷却窗口问题, fast-break/budget 已按 R1067/R1070 调整到位。绑定约束是
NVCF 远端 deepseek-v4-flash 0731 function 执行层, 非容器 env。R1067
(CONN_ERR_FAST_BREAK=5) 已给出最佳可及收益, 无进一步容器参数 lever。

**不采取 NVU_EMPTY_200_FASTBREAK 3→1**: empty_200 占 30min 错误 13% (10/79), 跨 key
分散, 无单 key 连续空 200 序列; 改 1 会将瞬时空 200 误判为该 key 永久失效, 加速 key
轮转反降命中健康 key 概率。数据不支持此 lever 为绑定约束。

## 3. 验证

- [x] `docker exec dsvf0731_nv40666 env` 确认:
      `NVU_CONN_ERR_FAST_BREAK=5`, `NVU_TIER_BUDGET_DSV4F0731_NV=180`,
      `NVU_EMPTY_200_FASTBREAK=3`, `NVU_PEXEC_TIMEOUT_FASTBREAK=3`
- [x] `/health` = {"status":"ok", 5 keys, nvcf_pexec_models 含 dsv4f0731_nv} (端口 40666)
- [x] 容器 dsvf0731_nv40666 Up 2 hours, 本轮无配置改动, 无需重启

## 4. 当前状态 (30min)

- 30min SR: **33.3%** (14/42)
- Avg / P50 / P95: 167961 / - / - ms
- 错误分布: NVCFPexecRemoteDisconnected=40, 529_nv_overloaded=18,
  NVCFPexecTimeout=10, empty_200=10, 504_nv_gateway_timeout=1
- Fallback: hm4104 持续 PRIMARY-FAIL-STREAM → FALLBACK-STREAM (fallback 亦 0% 成功)
- upstream: nvcf_pexec 25/200=48.0%, ms_fallback 8/200=0%

## 5. 上次修改效果 (R1067 CONN_ERR_FAST_BREAK=5 持续)

| 指标 | R1067 后 | R1072 | R1073 当前 |
|---|---|---|---|
| 30min/1h SR | 31→47% | 38.7% | 33.3% |
| 逐小时 SR | ~46% | 39-51% | 28-49% |
| ATE (24h) | 高位 | 高 | 409 |

→ CONN_ERR_FAST_BREAK=5 的收益 (遍历全 5 key 命中瞬时健康 key) 仍在, 当前 SR 波动
属风暴强度变化, 无回退证据。

## 6. 根因结论与下一步建议

- **根因**: NVCF deepseek-v4-flash 0731 function 侧临时劣化 (全 5 key 同时
  RD+empty_200+529+timeout 风暴), 模型特异性第 48 次成立 (glm5_2_nv 同链路 SR=70%)。
  非本容器参数可解。
- **下一步**:
  1. 若持续 SR<40% 且 ms_fallback 仍 0%, 严重性升级 — 建议评估切换 primary 到
     dsv4f_nv (04 版本) 或 dsv4p_nv, 绕过该劣化 function (需协调 CC/agent 侧, 非本容器
     单独可决)。
  2. 优先恢复 ms_fallback 路径 (当前 0%, 每次 burn ~271s) — 若 fallback 可用, 用户侧
     至少保活; 但此为 ms_gw 侧工单, 不在本容器 env 范围。
  3. 持续比对 glm5_2_nv (30min 70%): 若其也开始劣化 → 链路级问题 (非 model-specific),
     需重新审视 mihomo/key/出口。