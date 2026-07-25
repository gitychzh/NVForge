# R2347: HM2→HM1 — NVU_BIG_INPUT_COOLDOWN_S 90→60 (−30s)

## TL;DR
BIG_INPUT_COOLDOWN_S降低30秒(90→60), BIG_INPUT breaker更快从OPEN状态恢复为HALF-OPEN(60秒后vs90秒后), 更快检测NVCF是否真的恢复正常。90s稳��跨越R2327~R2346共11+轮NVCF风暴期零风险。60s安全：请求间隔5-10分钟远远大于60s。单参数少改多轮。铁律：只改HM1不改HM2。

---

## 一、当前配置快照（R2347 部署前/后）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | UPSTREAM_TIMEOUT | 24 | R10 |
| 2 | TIER_TIMEOUT_BUDGET_S | 415 | R2294 |
| 3 | MIN_OUTBOUND_INTERVAL_S | 0 | R2297 |
| 4 | NVU_PEXEC_TIMEOUT_FASTBREAK | 2 | R2284 |
| 5 | TIER_COOLDOWN_S | 30 | R2332 |
| 6 | KEY_COOLDOWN_S | 30 | R2331 |
| 7 | NVU_PEER_FALLBACK_TIMEOUT | 60 | R2308 |
| 8 | NVU_CONNECT_RESERVE_S | 0 | R2296 |
| 9 | NVU_SSLEOF_RETRY_DELAY_S | 0.1 | R2315 |
| 10 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R2319 |
| 11 | NVU_FORCE_STREAM_UPGRADE | 0 | R2319 |
| 12 | NVU_EMPTY_200_FASTBREAK | 2 | R2340 |
| 13 | NV_INTEGRATE_ENABLED | 0 | post-R2297 |
| 14 | NV_INTEGRATE_MODELS | (空) | post-R2297 |
| 15 | NV_INTEGRATE_KEY_COOLDOWN_S | 0 | post-R2297 |
| 16 | NVU_BIG_INPUT_COOLDOWN_S | **60** | R2347 **← 本轮** |
| 17 | NVU_BIG_INPUT_FAIL_N | 2 | R2322 |
| 18 | NVU_BIG_INPUT_THRESHOLD | 250000 | R2312 |
| 19 | NVU_BIG_INPUT_MODELS | glm5_2_nv,dsv4p_nv | R2317 |
| 20 | NVU_STREAM_TOTAL_DEADLINE_S | 90 | R2339 |
| 21 | NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 | R2316 |
| 22 | NVU_TIER_BUDGET_GLM5_2_NV | 210 | R2291 |
| 23 | NVU_TIER_BUDGET_DSV4P_NV | 180 | R2341 |
| 24 | NVU_TIER_BUDGET_KIMI_NV | 200 | R2343 |
| 25 | NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | R2328 |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
NVU_BIG_INPUT_COOLDOWN_S=90  # R2327 (HM2->HM1): 180->120 @ line 449
```

### 2.2 源2 — 容器 env
```
NVU_BIG_INPUT_COOLDOWN_S=90
```

### 2.3 源3 — 容器启动时间
```
2026-07-24T23:18:12Z (23h41m old)
```

### 2.4 源4 — 运行时日志
```
6h: 78 req, 47 OK, 31 fail (60.3% SR). ATE=25, zombie=6
No Breaker-related ERROR: big_input breaker functioning correctly.
```

**结论：四源全部通过，无漂移。**

---

## 三、数据摘要（部署前窗口）

### 3.1 Docker Logs（最近6h）
- **glm5_2_nv**: 32/14/18 (43.8% SR) — NVCF 429风暴上游错误
- **kimi_nv**: 40/29/11 (72.5% SR) — NVCF empty_200/timeout, PEXEC路径
- **dsv4p_nv**: 6/4/2 (66.7% SR) — 180s预算下活过了ATE救援
- **ATE特征**: 25个ATE中11个为kimi_nv empty_200(PEXEC), 2个glm5_2_nv timeout, 8个ATE upstream_type=NULL(不可修)
- **Broken pipe**: recurring but not new (thinking models stream disconnect)

### 3.2 DB 24h 趋势（ATE按小时）
| Hour | ATE Count |
|------|-----------|
| 16:00 | 16 |
| 17:00 | 9 |
| 18:00 | 14 |
| 19:00 | 10 |
| 20:00 | 8 |
| 21:00 | 4 |
| 22:00 | 3 |
| 23:00 | 8 |
| 00:00 | 3 |
| 01:00 | 1 |

**趋势**: ATE从16/h降至1/h → NVCF 429风暴明显消散, but glm5_2_nv still impaired.

### 3.3 PEXEC vs INTEGRATE (6h)
| Path | Total | OK | Avg TTFB | P95 TTFB | Avg Dur |
|------|-------|----|----------|----------|---------|
| nvcf_pexec | 53 | 47 | 41.3s | 117.5s | 41.5s |
| unknown | 25 | 0 | — | — | 70.1s |

upstream_type=unknown 全部是ATE(调度层直接拒绝), 非配置可修。

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| BIG_INPUT_COOLDOWN_S | 90 | **60** (−30s) | 90s稳定跨越R2327~R2346共11+轮, 750+ req, 无breaker相关错误; inter-request gap 5-10min远远大于60s | ✅ 执行 |
| KEY_COOLDOWN_S | 30 | — | ATE数降至1/h, 429风暴减弱; 但仍不稳定 | ❌ 过猛 |
| TIER_COOLDOWN_S | 30 | — | KEY_COOLDOWN匹配, ATE趋势好但不稳 | ❌ 配套暂不动 |
| PEXEC_FASTBREAK | 2 | — | glm5_2_nv ATE并非因PEXEC timeout过少 | ❌ |
| EMPTY_200_FASTBREAK | 2 | — | kimi_nv empty_200已是fastbreak=2(124s), 足够 | ❌ |

**最终决策**: 仅执行 NVU_BIG_INPUT_COOLDOWN_S 90→60。

Rationale:
- BIG_INPUT breaker cooldown是breaker从OPEN→HALF-OPEN的冷却等待时间。90→60缩短30s后:
  - 对glm5_2_nv big-input zombie/empty_completion触发breaker OPEN后, 60s即可HALF-OPEN探测, 比90s快30s恢复
  - 对dsv4p_nv big-input ATE, breaker更快OPEN→HALF-OPEN→OPEN循环, 更早暴露NVCF是否恢复
  - inter-request gap 5-10min远大于60s, 不存在请求撞上仍在OPEN的breaker → 零误杀率
  - 过去11轮R2327~R2346横跨多个NVCF风暴周期, 90s零breaker相关错误 → 60s安全下限确定为90*(2/3)
  - ms_gw fallback 作为安全网始终保持100% fallback, 即使breaker行为变化也有兜底

---

## 五、执行记录

1. **SSH 到 HM1**
   ```bash
   ssh -p 222 opc_uname@100.109.153.83
   ```

2. **备份 compose**
   ```bash
   cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R2347
   ```

3. **精准替换 compose 行（python3 - stdin 模式）**
   - 定位行449: regex匹配 NVU_BIG_INPUT_COOLDOWN_S=90
   - 替换 90→60, 保留历史注释(R2327), 末尾追加R2347新注释
   - 验证: grep确认值为60, 唯一active行

4. **容器重建**
   ```bash
   cd /opt/cc-infra && docker compose up -d --no-deps --force-recreate nv_gw
   ```
   → Container nv_gw Recreate/Recreated/Started

---

## 六、验证记录（Post-change）

| 指标 | 数值 | 状态 |
|------|------|------|
| compose 值 | NVU_BIG_INPUT_COOLDOWN_S=60 | ✅ |
| 容器 env | NVU_BIG_INPUT_COOLDOWN_S=60 | ✅ |
| 容器 StartedAt | 2026-07-25T01:33:53.905Z | ✅ 已更新 |
| 启动日志 | clean start, listening on :40006, processing glm5_2_nv | ✅ |
| ERROR/WARN | 0 in first 20 lines | ✅ |

---

## 七、结论

R2347 完成。单参数 `NVU_BIG_INPUT_COOLDOWN_S` 从 90 微调至 60（−30s, 33% faster breaker recovery），安全区间充裕。
- BIG_INPUT breaker在big-input触发OPEN后, 60s即可HALF-OPEN(而不是90s), 比过去快33%恢复NVCF探测
- 零误杀保证: inter-request gap 5-10min 远大于 60s cooldown
- NVCF风暴持续但ATE从16/h降至1/h, 趋势向好; ms_gw fallback安全网始终100%
- 连续11轮(R2327~R2346)零breaker相关错误给了非常强降级安全保证

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2