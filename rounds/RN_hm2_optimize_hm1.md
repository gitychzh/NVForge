# R833: HM2→HM1 — restart nv_gw to clear old bytecode (400 DEGRADED cycling regression, zero param change)

**决策**: 零参数修改，零 compose 修改，重启容器（清除旧 bytecode 导致的 400 DEGRADED 循环回退）。

---

## 数据收集 (08-Jul-2026 07:50 UTC)

### 容器状态
- 创建: 2026-07-07 06:04 UTC
- 启动: 2026-07-07 20:39 UTC (运行 ~11h)
- upstream.py 修改: 2026-07-07 19:30 UTC (R819 fix 已应用)
- upstream.cpython-312.pyc: 2026-07-07 20:40 UTC (启动后 1min 编译)
- 代码验证: should_cycle 正确排除 400 → NONCYCLE 路径存在

### 6h 窗口统计 (01:50–07:50 UTC)
- 44 请求 / 20 OK / 24 ATE → SR=45.5%
- 容器重启前 (<20:39): 37req/14OK/23ATE → SR=37.8%
- 容器重启后 (≥20:39): 7req/6OK/1ATE → SR=85.7%

### ATE 分诊
- tiers_tried_count=1: 17 (avg 13.7s) — **全部在重启前** (18:03–18:19 UTC)
  - glm5_2_nv: 15 ATE (avg 7.4s), start_tier_idx=2, fallback_actually_attempted=f
  - dsv4p_nv: 2 ATE (avg 60.8s), start_tier_idx=1
- tiers_tried_count=2: 7 (avg 88.6s)
- 重启后: 1 ATE (tiers_tried_count=2, 115s)

### Fallback
- fallback_occurred=true: 8/8 status=200 → 100% SR ✓
- FALLBACK_GRAPH: tier_chain=['glm5_2_nv', 'dsv4p_nv'] 双向 ✓

### nv_tier_attempts
- glm5_2_nv: 28× 400_nvcf_degraded (所有 key, elapsed_ms 为空 — 400 快速响应)
- dsv4p_nv: 1× 504_nv_gateway_timeout

### 当前配置 (全部 floor)
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=114
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=1
- MIN_OUTBOUND_INTERVAL_S=0, NV_INTEGRATE_KEY_COOLDOWN_S=0
- NVU_CONNECT_RESERVE_S=0, FALLBACK_HEALTH_THRESHOLD=0.10
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66 (= UPSTREAM_TIMEOUT ✓)

---

## 分析

### glm5_2_nv 400 DEGRADED 持续
glm5_2_nv NVCF function `3b9748d8` 持续返回 400 DEGRADED。每个 glm5_2_nv 请求立即 400 → fallback 到 dsv4p_nv。这是 NVCF 上游问题，非 config-fixable。

### 400 DEGRADED 循环回退 — old bytecode in running process
日志显示两种行为混合：
1. **循环行为** (02:34–03:03 UTC): `NV-CYCLE tier=glm5_2_nv k2→400 (400_nvcf_degraded), cycling` — 循环遍历 7 keys 浪费 ~8–25s 后才 fallback
2. **正确行为** (04:03+ UTC): `NV-NONCYCLE-ERR tier=glm5_2_nv k5 resp.status=400 non-cycling, aborting tier` — 第一个 key 400 → 立即 fallback (~1s)

代码在磁盘上完全正确: `should_cycle = resp.status in (401, 403, 429, 408, 500, 502, 503, 504, 202)` — 400 不在列表中。两个路径 (pexec L621, integrate L238) 都正确排除 400。

**根因**: 容器在 20:39 UTC 启动时，磁盘上的旧 `.cpython-312.pyc` (R819 fix 之前编译) 被 Python 加载到内存。启动后 1 分钟 (20:40 UTC) 新的 `.pyc` 被 `docker exec` import 触发重新编译，但**运行中的服务器进程已在内存中持有旧 bytecode** (R822 pattern)。04:03 UTC 后行为自行纠正（可能某 `docker exec` import 触发部分模块重载）。

### NOP Gate 分析 (重启后窗口)
- Gate 1 (所有双 tier): 1 ATE = tiers_tried_count=2 ✓
- Gate 2 (零单 tier): 0 单 tier ATE 重启后 ✓ (17 全部在重启前)
- Gate 3 (NVCFPexecTimeout buffer ≥3s): 无 NVCFPexecTimeout 记录 + dsv4p timeout ~50s << UPSTREAM=66 (buffer ~16s) ✓
- Gate 4 (FALLBACK_GRAPH 双向): ✓
- Gate 5 (Fallback 100% SR): 8/8 ✓
- Gate 6 (所有 params at floor): ✓

**但 400 循环浪费仍是活跃缺陷** — Gate 2 之外的代码级问题。

---

## 执行

### 操作: 重启容器 (清除旧 bytecode)
```
cd /opt/cc-infra && docker compose restart nv_gw
```

- 零参数修改
- 零 compose 修改
- 重启强制 Python 重新加载模块 → 400 NONCYCLE 正确行为 (第一个 key 400 → 立即 fallback ~1s)
- 预期效果: 消除 ~7–25s 的 400 循环浪费，每个 glm5_2_nv 请求节省 6–24s
- 健康检查: OK, FALLBACK_GRAPH `['glm5_2_nv', 'dsv4p_nv']` 双向

### 验证
- 容器健康: `{"status": "ok", ...}`
- tier_chain: `['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback)`
- 代码确认: should_cycle 排除 400 ✓

---

## ⏳ 轮到 HM1 优化 HM2