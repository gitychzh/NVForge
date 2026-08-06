# R1074: dsv4f0731_nv self-opt NOP — NVCF 模型特异性劣化风暴第 49 轮 (全 5 key, 无容器 lever)

> 时间: 2026-08-06 20:5x BJT (12:5x UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Flash 0731 via NVCF)
> 状态: **NOP (无参数修改)** — 延续 R1073/R1072/R1071/R1021-R1070 的模型特异性劣化风暴,
>   R1067 (CONN_ERR_FAST_BREAK=5) 已落地为最佳可及收益, 无新增单参数 lever。

## 1. 背景 (改前必有数据)

### 30min 窗口 (pre-run 注入) — tier_model=dsv4f0731_nv
- 总量 42, 200=18, 失败=24, **SR=42.9%**
- Avg 157976ms, p50 174877ms, p95 307012ms
- 429: 0 实际计数; key_cycle_429s 分布 k0:31, k1:6, k2:3, k3:2 — 轮转伪影 (k0 首试)
- per-key 200: k0=6, k1=1, k2=5, k3=5, k4=1 (成功均匀分散于各 key)

### 错误分类 (30min, nv_tier_attempts)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 13 | 213605 |
| buffer_exhausted (ms_fallback) | 8 | 269615 |
| zombie_empty_completion | 2 | 20624 |
| client_gone_during_flush | 1 | 286385 |

### per-key 错误 (30min)
| key | 错误合计 | 主要类型 |
|---|---|---|
| 0 | 12 | all_tiers_exhausted(12) |
| 1 | 1 | all_tiers_exhausted(1) |
| 2 | 1 | client_gone_during_flush(1) |
| 4 | 2 | zombie_empty_completion(2) |

→ 错误集中在 k0 (all_tiers_exhausted 12) 是 **轮转首试伪影** (k0 首试, 劣化风暴时最先
被耗尽), 非 k0 专属网络/key 问题 (k0 也有 6 个 200 成功)。其余 key 错误极少, 印证错误源
为上游 function 执行层, 非本容器可路由之物。

### upstream_type (30min)
- nvcf_pexec 33 (200=18, **SR=54.5%**, avg=115240ms)
- ms_fallback 8 (200=0, **SR=0%**, avg=269615ms) — fallback 路径持续 0%

### 关键证据
1. **同链路对照**: glm5_2_nv (同容器同 key 同出口) 本轮未显示劣化证据; 错误仅发生在
   dsv4f0731_nv 具体 function 远端执行层 (模型特异性, 第 49 次成立)。
2. **ms_fallback 本窗 0%** (8/8 失败, avg ~270s) — fallback 路径 (→ ms_gw) 完全失效,
   每次 burn ~270s buffer。fallback 不能兜底 → 调 primary 参数无助吞吐。
3. **n 3h 逐小时**: 09:00 SR=54.1%(33/61), 10:00 SR=37.8%(28/74), 11:00 SR=29.6%(21/71),
   12:00 SR=42.9%(18/42) — 稳定在 30-50% 劣化带, 非瞬时暴跌亦非恢复。
4. **24h ATE**: all_tiers_exhausted **421** 次 — 持续高位, 劣化风暴贯穿全天。
5. **6h SR=43.4%** (231/532) — 稳定劣化带。

## 2. 决策: NOP (无参数修改)

全 5 key 同时劣化 (RD+empty_200+529+timeout 混合风暴, 本窗主要表现为
all_tiers_exhausted), 无单 key 网络类劣化可调 key 冷却, 0 实际 429 无冷却窗口问题,
fast-break/budget 已按 R1067/R1070 调整到位。绑定约束是 NVCF 远端 deepseek-v4-flash 0731
function 执行层, 非容器 env。R1067 (CONN_ERR_FAST_BREAK=5) 已给出最佳可及收益, 无进一步
容器参数 lever。

**不采取 NVU_EMPTY_200_FASTBREAK 3→1**: empty_200/zombie 本窗仅 2 例, 非绑定约束; 改 1
会将瞬时空 200 误判为该 key 永久失效, 加速 key 轮转反降命中健康 key 概率。数据不支持。

## 3. 验证

- [x] `docker exec dsvf0731_nv40666 env` 确认:
      `NVU_CONN_ERR_FAST_BREAK=5`, `NVU_TIER_BUDGET_DSV4F0731_NV=180`,
      `NVU_EMPTY_200_FASTBREAK=3`, `NVU_PEXEC_TIMEOUT_FASTBREAK=3`
- [x] `/health` = {"status":"ok", 5 keys, nvcf_pexec_models 含 dsv4f0731_nv} (端口 40666)
- [x] 容器 dsvf0731_nv40666 Up 3 hours, 本轮无配置改动, 无需重启

## 4. 当前状态 (30min)

- 30min SR: **42.9%** (18/42)
- Avg / P50 / P95: 157976 / 174877 / 307012 ms
- 错误分布: all_tiers_exhausted=13, buffer_exhausted=8 (ms_fallback),
  zombie_empty_completion=2, client_gone_during_flush=1
- Fallback: hm4104 持续 PRIMARY-FAIL-STREAM → FALLBACK-STREAM (fallback 亦 0% 成功)
- upstream: nvcf_pexec 33/200=54.5%, ms_fallback 8/200=0%

## 5. 上次修改效果 (R1067 CONN_ERR_FAST_BREAK=5 持续)

| 指标 | R1067 后 | R1073 | R1074 当前 |
|---|---|---|---|
| 30min/1h SR | 31→47% | 33.3% | 42.9% |
| 逐小时 SR | ~46% | 28-49% | 30-54% |
| ATE (24h) | 高位 | 409 | 421 |

→ CONN_ERR_FAST_BREAK=5 收益 (遍历全 5 key 命中瞬时健康 key) 仍在; 本窗 SR 回升至 42.9%
属风暴强度波动, 无回退证据。24h ATE 仍 421 高位, 劣化持续。

## 6. 根因结论与下一步建议

- **根因**: NVCF deepseek-v4-flash 0731 function 侧持续劣化 (全 5 key 同时
  RD+empty_200+529+timeout 风暴, 本窗表达为 all_tiers_exhausted 主导), 模型特异性第 49 次
  成立 (glm5_2_nv 同链路健康)。非本容器参数可解。
- **下一步**:
  1. 若持续 SR<40% 且 ms_fallback 仍 0%, 严重性升级 — 建议评估切换 primary 到
     dsv4f_nv (04 版本) 或 dsv4p_nv, 绕过该劣化 function (需协调 CC/agent 侧, 非本容器
     单独可决)。
  2. 优先恢复 ms_fallback 路径 (当前 0%, 每次 burn ~270s) — 若 fallback 可用, 用户侧
     至少保活; 但此为 ms_gw 侧工单, 不在本容器 env 范围。
  3. 持续比对 glm5_2_nv (同链路): 若其也开始劣化 → 链路级问题 (非 model-specific),
     需重新审视 mihomo/key/出口。