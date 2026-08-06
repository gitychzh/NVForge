# R1076: dsv4f0731_nv self-opt NOP — NVCF 模型特异性劣化风暴第 51 轮 (1h 197 attempts 0 成功, 无容器 lever)

> 时间: 2026-08-06 22:1x BJT (14:1x UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Flash 0731 via NVCF)
> 状态: **NOP (无参数修改)** — 延续 R1075/R1074/R1073/.../R1021 的模型特异性劣化风暴,
>   R1067 (CONN_ERR_FAST_BREAK=5) 已落地为最佳可及收益, 无新增单参数 lever。

## 1. 背景 (改前必有数据)

### 30min 窗口 (pre-run 注入) — tier_model=dsv4f0731_nv
- 总量 33, 200=4, 失败=29, **SR=12.1%**
- Avg 235866ms, p50 180043ms, p95 675170ms, max 675151ms
- 429: 0 实际计数; key_cycle_429s 分布 k0:27, k1:5, k2:1 — 轮转伪影 (k0 首试)
- per-key 200: k0=1, k2=1, k4=2 (成功分散, 无健康 key)

### 错误分类 (30min, nv_tier_attempts)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 23 | 262103 |
| zombie_empty_completion | 3 | 20096 |
| buffer_exhausted (ms_fallback) | 2 | 436070 |
| client_gone_during_flush | 1 | 263736 |

### 1h nv_tier_attempts 详查 (本轮直接查询)
- 总量 **197, ok=0, fail=197** — 全 5 key 同时 0 成功。
- per-key 错误 (跨 key 均匀分散, 非单 key 网络类劣化):
  - k0: RD=15, 504=9, Tm=8, 529=3
  - k1: RD=16, 504=15, Tm=4, empty_200=2
  - k2: RD=19, 504=15, Tm=3, 529=2
  - k3: RD=18, Tm=9, 504=6, budget=4, 529=1
  - k4: RD=24, Tm=9, 504=4, 529=3
- 上游错误合计: NVCFPexecRemoteDisconnected=92, 504_nv_gateway_timeout=49,
  NVCFPexecTimeout=33, 529_nv_overloaded=9, budget_exhausted_after_connect=4, empty_200=2

### upstream_type (30min)
- nvcf_pexec 29 (200=4, **SR=13.8%**, avg=183769ms)
- ms_fallback 1 (200=0, avg=284267ms) — fallback 路径持续 0%
- (blank/其他 5, 200=0)
- 1h ms_fallback 累计 6/6 0% — fallback 完全失效, 每次 burn ~284s buffer。

### 关键证据
1. **1h nv_tier_attempts**: dsv4f0731_nv 197 次 attempt **0 成功** — 全 5 key 同时失败,
   错误分布 RD=92 + 504=49 + timeout=33 + 529=9 + empty_200=2 + budget=4, 跨 key 均匀分散,
   无单 key 网络类劣化。错误主体为远端 disconnect/gateway-timeout/overload, 非本容器可路由之物。
2. **glm5_2_nv 对照**: 1h 内 0 attempts (无流量), 本轮无有效对照; 但 50 轮已确立的
   模型特异性模式 (glm5_2_nv 同链路健康 at 有流量) 继续作为参照 — 网络/mihomo/key/出口路径健康。
3. **ms_fallback 本窗 0%** (1h 6/6 失败, avg ~284s) — fallback 路径 (→ ms_gw) 完全失效,
   fallback 不能兜底 → 调 primary 参数无助吞吐。
4. **3h 逐小时**: 14:00 SR=28.6%(2/7), 13:00 SR=19.6%(18/92), 12:00 SR=39.5%(30/76),
   11:00 SR=32%(16/50) — 持续在 20-40% 劣化带, 无恢复迹象, 且有进一步下探。
5. **24h ATE**: all_tiers_exhausted **472** 次 — 持续高位, 劣化风暴贯穿全天 (较 R1075 的 438 再升)。
6. **6h SR=37.7%** (205/544) — 稳定劣化带。

## 2. 决策: NOP (无参数修改)

全 5 key 同时劣化 (RD+504+timeout+529+empty_200 混合风暴), 无单 key 网络类劣化可调 key 冷却,
0 实际 429 无冷却窗口问题, fast-break/budget 已按 R1067/R1070 调整到位。绑定约束是 NVCF 远端
deepseek-v4-flash 0731 function 执行层, 非容器 env。R1067 (CONN_ERR_FAST_BREAK=5) 已给出
最佳可及收益, 无进一步容器参数 lever。

**不采取 NVU_EMPTY_200_FASTBREAK 3→1**: zombie/empty_200 本窗仅 3+2 例, 非绑定约束;
改 1 会将瞬时空 200 误判为该 key 永久失效, 加速 key 轮转反降命中健康 key 概率。数据不支持。

## 3. 验证

- [x] `docker exec dsvf0731_nv40666 env` 确认:
      `KEY_COOLDOWN_S=30`, `NVU_TIER_BUDGET_DSV4F0731_NV=180`, `NVU_EMPTY_200_FASTBREAK=3`,
      `NVU_PEXEC_TIMEOUT_FASTBREAK=3`, `TIER_COOLDOWN_S=90`, `UPSTREAM_TIMEOUT=90` (无改动)
- [x] `/health` = {"status":"ok", 5 keys, nvcf_pexec_models 含 dsv4f0731_nv} (端口 40666)
- [x] 容器 dsvf0731_nv40666 Up 5 hours, 本轮无配置改动, 无需重启

## 4. 当前状态 (30min)

- 30min SR: **12.1%** (4/33)
- Avg / P50 / P95: 235866 / 180043 / 675170 ms
- 错误分布: all_tiers_exhausted=23, zombie_empty_completion=3,
  buffer_exhausted=2 (ms_fallback), client_gone_during_flush=1
- Fallback: hm4104 持续 PRIMARY-FAIL-STREAM → FALLBACK-STREAM (fallback 亦 0% 成功)
- upstream: nvcf_pexec 29/200=13.8%, ms_fallback 1/200=0%

## 5. 上次修改效果 (R1067 CONN_ERR_FAST_BREAK=5 持续)

| 指标 | R1074 | R1075 | R1076 当前 |
|---|---|---|---|
| 30min/1h SR | 42.9% | 30.6% | 12.1% |
| 逐小时 SR | 30-54% | 22-40% | 19-40% |
| ATE (24h) | 421 | 438 | 472 |

→ CONN_ERR_FAST_BREAK=5 已无进一步收益可挖; 本窗 SR 降至 12.1% 为 51 轮来最差, 风暴强度
持续恶化 (1h 0 成功, ATE 472 且逐轮上升)。劣化风暴进入峰值阶段, 无本容器回退/回退证据。

## 6. 根因结论与下一步建议

- **根因**: NVCF deepseek-v4-flash 0731 function 侧持续劣化 (全 5 key 同时
  RD+504+timeout 风暴, 1h 197 次 attempt 0 成功), 模型特异性第 51 次成立。非本容器参数可解。
- **下一步**:
  1. **严重性已升级至峰值**: 连续 51 轮 SR<50%, 本轮 1h 0 成功 / 30min 12.1% / 24h ATE 472
     且持续上升。**强烈建议立即切换 primary** 到 dsv4f_nv (04 版本) 或 dsv4p_nv, 绕过该劣化
     function (需协调 CC/agent 侧, 非本容器单独可决)。这是唯一有效动作。
  2. 优先恢复 ms_fallback 路径 (当前 0%, 每次 burn ~284s) — 若 fallback 可用, 用户侧至少保活;
     但此为 ms_gw 侧工单, 不在本容器 env 范围。
  3. 持续比对 glm5_2_nv (下轮若恢复流量): 若其也开始劣化 → 链路级问题 (非 model-specific),
     需重新审视 mihomo/key/出口。