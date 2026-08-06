# R1075: dsv4f0731_nv self-opt NOP — NVCF 模型特异性劣化风暴第 50 轮 (全 5 key, 无容器 lever)

> 时间: 2026-08-06 21:2x BJT (13:2x UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Flash 0731 via NVCF)
> 状态: **NOP (无参数修改)** — 延续 R1074/R1073/R1072/R1071/R1021-R1070 的模型特异性劣化风暴,
>   R1067 (CONN_ERR_FAST_BREAK=5) 已落地为最佳可及收益, 无新增单参数 lever。

## 1. 背景 (改前必有数据)

### 30min 窗口 (pre-run 注入) — tier_model=dsv4f0731_nv
- 总量 36, 200=11, 失败=25, **SR=30.6%**
- Avg 158861ms, p50 180039ms, p95 284129ms, p90 334933ms
- 429: 0 实际计数; key_cycle_429s 分布 k0:24, k1:2, k2:5, k3:4, k7:1 — 轮转伪影 (k0 首试)
- per-key 200: k0=7, k1=1, k2=1, k3=1, k4=1 (成功分散于各 key)

### 错误分类 (30min, nv_tier_attempts)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 17 | 179798 |
| buffer_exhausted (ms_fallback) | 4 | 302834 |
| stream_absolute_cap | 2 | 160950 |
| zombie_empty_completion | 2 | 107013 |

### per-key 错误 (30min)
| key | 错误合计 | 主要类型 |
|---|---|---|
| 0 | 19 | all_tiers_exhausted(17), buffer(3), zombie(1), stream_cap(1) |
| 4 | 2 | buffer(1), zombie(1) |
| 2 | 1 | stream_absolute_cap(1) |

→ 错误主体集中在 k0 (all_tiers_exhausted 17) 是 **轮转首试伪影** (k0 首试, 劣化风暴时最先
被耗尽), 非 k0 专属网络/key 问题 (k0 也有 7 个 200 成功)。其余 key 错误极少, 印证错误源
为上游 function 执行层, 非本容器可路由之物。

### upstream_type (30min)
- nvcf_pexec 32 (200=11, **SR=34.4%**, avg=140864ms)
- ms_fallback 3 (200=0, **SR=0%**, avg=306266ms) — fallback 路径持续 0%
- nv_integrate 1 (200=0, avg=292537ms) — integrate 单次尝试亦失败

### 关键证据
1. **3h nv_tier_attempts**: dsv4f0731_nv 468 次 attempt **0 成功** — 全 5 key 同时失败。
   错误分布 NVCFPexecRemoteDisconnected=258, NVCFPexecTimeout=66, 529=54, 504=45,
   empty_200=40, budget_after_connect=5 — 跨 key 均匀分散, 无单 key 网络类劣化。
2. **glm5_2_nv 对照**: 3h 内 0 attempts (无流量), 本轮无有效对照; 但 49 轮已确立的
   模型特异性模式 (glm5_2_nv 同链路健康 at 有流量时) 本轮继续成立 — 错误源为
   dsv4f0731_nv 具体 function 远端执行层。
3. **ms_fallback 本窗 0%** (3/3 失败, avg ~293s) — fallback 路径 (→ ms_gw) 完全失效,
   每次 burn ~293s buffer。fallback 不能兜底 → 调 primary 参数无助吞吐。
4. **3h 逐小时**: 13:00 SR=22.7%(5/22), 12:00 SR=39.5%(30/76), 11:00 SR=29.6%(21/71),
   10:00 SR=38%(19/50) — 持续在 22-40% 劣化带, 无恢复迹象。
5. **24h ATE**: all_tiers_exhausted **438** 次 — 持续高位, 劣化风暴贯穿全天。
6. **6h SR=41.4%** (220/531) — 稳定劣化带。

## 2. 决策: NOP (无参数修改)

全 5 key 同时劣化 (RD+504+timeout+529+empty_200 混合风暴, 本窗主要表现为
all_tiers_exhausted), 无单 key 网络类劣化可调 key 冷却, 0 实际 429 无冷却窗口问题,
fast-break/budget 已按 R1067/R1070 调整到位。绑定约束是 NVCF 远端 deepseek-v4-flash 0731
function 执行层, 非容器 env。R1067 (CONN_ERR_FAST_BREAK=5) 已给出最佳可及收益, 无进一步
容器参数 lever。

**不采取 NVU_EMPTY_200_FASTBREAK 3→1**: zombie/empty_200 本窗仅 2+0 例, 非绑定约束;
改 1 会将瞬时空 200 误判为该 key 永久失效, 加速 key 轮转反降命中健康 key 概率。数据不支持。

## 3. 验证

- [x] `docker exec dsvf0731_nv40666 env` 确认:
      `NVU_CONN_ERR_FAST_BREAK=5`, `NVU_TIER_BUDGET_DSV4F0731_NV=180`,
      `NVU_EMPTY_200_FASTBREAK=3`, `NVU_PEXEC_TIMEOUT_FASTBREAK=3`
- [x] `/health` = {"status":"ok", 5 keys, nvcf_pexec_models 含 dsv4f0731_nv} (端口 40666)
- [x] 容器 dsvf0731_nv40666 Up 4 hours, 本轮无配置改动, 无需重启

## 4. 当前状态 (30min)

- 30min SR: **30.6%** (11/36)
- Avg / P50 / P95 / P90: 158861 / 180039 / 284129 / 334933 ms
- 错误分布: all_tiers_exhausted=17, buffer_exhausted=4 (ms_fallback),
  stream_absolute_cap=2, zombie_empty_completion=2
- Fallback: hm4104 持续 PRIMARY-FAIL-STREAM → FALLBACK-STREAM (fallback 亦 0% 成功)
- upstream: nvcf_pexec 32/200=34.4%, ms_fallback 3/200=0%, nv_integrate 1/200=0%

## 5. 上次修改效果 (R1067 CONN_ERR_FAST_BREAK=5 持续)

| 指标 | R1067 后 | R1073 | R1074 | R1075 当前 |
|---|---|---|---|---|
| 30min/1h SR | 31→47% | 33.3% | 42.9% | 30.6% |
| 逐小时 SR | ~46% | 28-49% | 30-54% | 22-40% |
| ATE (24h) | 高位 | 409 | 421 | 438 |

→ CONN_ERR_FAST_BREAK=5 的收益 (遍历全 5 key 命中瞬时健康 key) 仍在; 本窗 SR 回落至 30.6%
属风暴强度持续波动 (逐小时 22-40% 是 50 轮以来最差小时带), 无回退证据。24h ATE 升至 438,
劣化持续且未见缓解。

## 6. 根因结论与下一步建议

- **根因**: NVCF deepseek-v4-flash 0731 function 侧持续劣化 (全 5 key 同时
  RD+504+timeout+529+empty_200 风暴, 3h 内 468 次 attempt 0 成功), 模型特异性第 50 次
  成立 (glm5_2_nv 同链路健康 at 有流量)。非本容器参数可解。
- **下一步**:
  1. **严重性已升级**: SR 连续 50 轮 <50%, 3h 逐小时 22-40% 为最差带, 24h ATE 438 且持续
     上升。建议**强烈推动切换 primary** 到 dsv4f_nv (04 版本) 或 dsv4p_nv, 绕过该劣化
     function (需协调 CC/agent 侧, 非本容器单独可决)。这是唯一有效动作。
  2. 优先恢复 ms_fallback 路径 (当前 0%, 每次 burn ~293s) — 若 fallback 可用, 用户侧
     至少保活; 但此为 ms_gw 侧工单, 不在本容器 env 范围。
  3. 持续比对 glm5_2_nv (下轮若恢复流量): 若其也开始劣化 → 链路级问�� (非 model-specific),
     需重新审视 mihomo/key/出口。