# R818: HM2→HM1 — func_health threshold 0.80→0.10, 恢复 glm5_2→dsv4p cross-model fallback

**时间**: 2026-07-08 02:30 UTC
**作者**: opc2_uname (HM2)
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）
**分析窗口**: 6h (20:30–02:30 UTC)

---

## TL;DR

glm5_2_nv 的 NVCF function `3b9748d8-1d85` 处于 DEGRADING 状态，所有 5 key 均返回 `400_nvcf_degraded`。FALLBACK_GRAPH 配置了 `glm5_2_nv → dsv4p_nv` 跨模型 fallback，但 `func_health.py` 硬编码 `HEALTH_THRESHOLD = 0.80`，而 dsv4p function `74f02205` 健康度仅 ~0.25，被判定为 unhealthy，导致 fallback 链条被阻断。glm5_2 请求全部 ~7s 内 5 key 耗尽后直接 502（无 fallback 尝试），SR 崩至 10%。

**修复**: 将 `func_health.py` 的 `HEALTH_THRESHOLD` 从 `0.80` 硬编码改为 `float(os.environ.get("NVU_FALLBACK_HEALTH_THRESHOLD", "0.10"))`，与 `FALLBACK_HEALTH_THRESHOLD=0.10` 对齐。修复后 tier_chain 从 `['glm5_2_nv']` 恢复为 `['glm5_2_nv', 'dsv4p_nv']`，cross-model fallback 重新生效。

**单参数少改多轮。铁律：只改HM1不改HM2。**

---

## 一、问题诊断

### 1.1 glm5_2_nv — NVCF function DEGRADING

```
docker logs nv_gw --tail 200 | grep glm5_2
```

所有 glm5_2_nv 请求均快速失败（~7s），全部 5 key 返回 `400_nvcf_degraded`：

```
[NV-CYCLE] tier=glm5_2_nv k1 → 400 (400_nvcf_degraded), cycling to next key
[NV-CYCLE] tier=glm5_2_nv k2 → 400 (400_nvcf_degraded), cycling to next key
... (all 5 keys, ~1s each)
[NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=0, timeout=0, other=7, elapsed=7829ms
```

### 1.2 FALLBACK_GRAPH 被 func_health 阻断

FALLBACK_GRAPH 正确配置了双向 fallback：
```python
FALLBACK_GRAPH = {
    "dsv4p_nv": ["glm5_2_nv"],
    "glm5_2_nv": ["dsv4p_nv"],
}
```

但 `upstream.py` 的 fallback 构建逻辑检查 `func_health.is_healthy(alt_primary)`：
```python
if alt_primary and func_health.is_healthy(alt_primary):
    tier_order.append(alt)
```

`func_health.py` 硬编码 `HEALTH_THRESHOLD = 0.80`，而 dsv4p function `74f02205` 健康度仅 ~0.25（R796 报告），远低于阈值 → fallback 被阻断。

日志证据：
```
[NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True tier_chain=['glm5_2_nv'] (no fallback, 3model)
```

`tier_chain` 只有单元素，无 dsv4p_nv fallback。

### 1.3 Peer fallback 也被阻断

`NVU_PEER_FB_SKIP_MODELS=glm5_2_nv`（R797 设置）阻止了 peer-fb，因为 HM2 同样使用 `3b9748d8`，peer 同样坏。这是正确的。

---

## 二、DB 数据（6h，修复前）

### 2.1 总体

| 指标 | 值 |
|------|-----|
| Total | 51 |
| OK (200) | 12 |
| ATE (502) | 39 |
| **SR** | **23.5%** |

### 2.2 按模型

| request_model | cnt | ok | ate | SR% | avg_ms | max_ms |
|---------------|-----|-----|-----|------|--------|--------|
| dsv4p_nv | 11 | 8 | 3 | 72.7 | 48,233 | 68,217 |
| glm5_2_nv | 40 | 4 | 36 | **10.0** | 25,638 | 125,593 |

### 2.3 按 tiers_tried

| model | status | tiers_tried | cnt |
|-------|--------|-------------|-----|
| glm5_2_nv | 502 | 1 | 30 | ← 单 tier 耗尽，无 fallback
| glm5_2_nv | 502 | 2 | 6 | ← 双 tier 也失败（dsv4p surge 时段）
| glm5_2_nv | 200 | 2 | 4 | ← dsv4p fallback 成功
| dsv4p_nv | 200 | 1 | 7 |
| dsv4p_nv | 200 | 2 | 1 |
| dsv4p_nv | 502 | 1 | 2 |
| dsv4p_nv | 502 | 2 | 1 |

**关键**: glm5_2_nv 的 30/36 ATE 是单 tier（tiers_tried_count=1），说明 fallback 链从未被构建。仅 6 次双 tier 502（dsv4p 也 surge 时），4 次双 tier 200（dsv4p fallback 成功）。

### 2.4 CASCADE 效应

glm5_2_nv 失败后，caller（ms_gw）重试 3 次，每次 ~7s，3 次重试 ~21s，然后 ms_gw 投给 glm5_2_ms 变体。但 ms_gw 的 ms_uni 变体也有空字节问题，导致整体请求延迟极高（max=125,593ms）。

---

## 三、修复执行

### 3.1 代码变更

**文件**: `/opt/cc-infra/proxy/nv-gw/gateway/func_health.py`（bind mount，修改即生效）

**变更 1**: 添加 `import os`
```python
import os
```

**变更 2**: 硬编码阈值 → env 可配置
```diff
- HEALTH_THRESHOLD = 0.80
+ HEALTH_THRESHOLD = float(os.environ.get("NVU_FALLBACK_HEALTH_THRESHOLD", "0.10"))
```

**变更 3**: 重启容器加载新代码
```bash
docker restart nv_gw
```

### 3.2 验证

修复后立即验证：
```python
>>> func_health.HEALTH_THRESHOLD
0.1
>>> func_health.is_healthy("74f02205-c7ba-438f-b81a-2537955bd7ec")
True
>>> func_health.is_healthy("3b9748d8-1d85-40e8-8573-0eeaa63a4b63")
True
```

日志验证 — tier_chain 恢复双向：
```
[NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True
         tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback, health={...})
```

FALLBACK_GRAPH 跨模型 fallback 已恢复。

---

## 四、为什么 0.10 是安全的

1. **所有 3 模型均只有 1 个 function_id**（单候选列表），`select_healthy_function()` 在全部 unhealthy 时仍返回 `candidates[0]`（首选）。阈值只影响 FALLBACK_GRAPH 的跨模型 fallback 决策，不影响 pexec 选 function。
2. **FALLBACK_HEALTH_THRESHOLD=0.10** 已在 env 存在（R708），语义一致。
3. **func_health 冷启动**（容器重启）时所有 function 健康度=1.0，阈值 0.10 或 0.80 无差异。运行时健康度下降后，0.10 确保 fallback 链不被过早切断。
4. **fallback 已有 TIER_TIMEOUT_BUDGET_S=114 保护**，即使 fallback 目标 function 也坏，不会无限等待。

---

## 五、HM1 当前参数（本次仅代码变更，无 env 变更）

| 参数 | 值 | 来源 |
|------|-----|------|
| **func_health HEALTH_THRESHOLD** | **0.10** (env: NVU_FALLBACK_HEALTH_THRESHOLD) | **R818 新** |
| UPSTREAM_TIMEOUT | 66 | R754 |
| TIER_TIMEOUT_BUDGET_S | 114 | R737 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R768 floor |
| NVU_EMPTY_200_FASTBREAK | 1 | R774 floor |
| NVU_CONNECT_RESERVE_S | 0 | R657 floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | R638 floor |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | R708 floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | R692 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R755 aligned |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | R631 floor |
| KEY_COOLDOWN_S | 25 | R162 |
| TIER_COOLDOWN_S | 25 | R492 |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | R697 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | R543 |
| NV_INTEGRATE_MODELS | "" (空) | R693 |

---

## 六、遗留观察

1. **glm5_2_nv function 3b9748d8 持续 DEGRADING** — 所有 5 key 400_nvcf_degraded。这是 NVCF 上游问题，非配置可修复。cross-model fallback 恢复后，glm5_2 请求将 fallback 到 dsv4p_nv。
2. **dsv4p_nv function 74f02205 也有间歇 surge** — 日志中 empty_200 和 504 仍存在，但频率较低。
3. **NVU_PEER_FB_SKIP_MODELS=glm5_2_nv** 仍正确 — NVCF 同 function 坏时 peer-fb 无意义，跳过避免 ~180s 卡死。
4. **env 无需变更** — NVU_FALLBACK_HEALTH_THRESHOLD 默认值 0.10 已足够，无需显式设置 env。

---

## 七、结论

R818 修复了 `func_health.HEALTH_THRESHOLD` 硬编码 0.80 导致的 cross-model fallback 阻断问题。修复后：

- glm5_2_nv 请求在 5 key 耗尽后自动 fallback 到 dsv4p_nv（tier_chain=['glm5_2_nv', 'dsv4p_nv']）
- 阈值降至 0.10 与 FALLBACK_HEALTH_THRESHOLD 对齐，且现为 env 可配置
- 无 env 变量变更，代码变更仅 3 行（+import os, +0.80→env）

**NOP streak 终结**: R788→R796 连续 9 轮 NOP 后，本轮为首次非 NOP 变更。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2