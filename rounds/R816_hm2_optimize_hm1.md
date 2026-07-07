# R816: HM2→HM1 — glm5_2_nv 停 inject thinking + ms_gw [DONE] 关连接 (R813 同步)

**时间**: 2026-07-08 01:40 UTC
**决策**: 应用 R813 共享源码修复到 HM1 — config.py glm5_2_nv inject 改空 + ms_gw handlers.py [DONE] break
**作者**: opc2_uname (HM2→HM1)

## 数据采集

### 容器状态
- Container: `nv_gw`, Up 5h (healthy), 重启: 2026-07-07T12:38:55Z
- Container: `ms_gw`, Up 17h (healthy)
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=114, FASTBREAK=1
- FALLBACK_HEALTH_THRESHOLD=0.10, FORCE_STREAM_UPGRADE_TIMEOUT=66 ✅

### 6h 总体统计 (19:40-01:40 UTC)

| 指标 | 值 |
|------|---|
| 总请求 | 26 |
| OK (200) | 2 |
| ATE (502) | 24 |
| **6h SR** | **7.7%** |

### 6h ATE 分解

| tier_model | status | cnt | SR |
|------------|--------|-----|-----|
| glm5_2_nv | 200 | 0 | **0%** |
| glm5_2_nv | 502 | 24 | — |
| dsv4p_nv | 200 | 2 | 100% |
| dsv4p_nv | 502 | 0 | — |

### 6h ATE tiers_tried_count

| tiers_tried_count | cnt | avg_dur |
|---|---|---|
| 1 (单tier) | 21 | 10,802ms |
| 2 (双tier) | 3 | 123,428ms |

全部 21 单tier ATE 为 start_tier_idx=2 (glm5_2_nv), fallback 未尝试。

### nv_tier_attempts (6h)

| tier | error_type | cnt |
|------|-----------|-----|
| glm5_2_nv | 400_nvcf_degraded | 14 |
| dsv4p_nv | 504_nv_gateway_timeout | 1 |

### Fallback SR

| fallback_occurred | total | ok | SR |
|---|---|---|---|
| f (direct) | 24 | 0 | 0% |
| t (fallback) | 2 | 2 | **100%** ✅ |

### tier_chain 动态 (docker logs)

```
14:xx UTC: tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback) ✅
15:04 UTC: tier_chain=['dsv4p_nv'] (no fallback, 3model) ← FALLBACK_GRAPH transient消失
15:33 UTC: tier_chain=['glm5_2_nv'] (no fallback, 3model)
17:33 UTC: tier_chain=['glm5_2_nv'] (no fallback, 3model) — 持续至采集时刻
```

FALLBACK_GRAPH transient消失持续 ~3h+ (R815 pattern: 17:00-20:00 CST 消失 → self-recovery).
但即使 FALLBACK_GRAPH 存在时, glm5_2_nv tier 100% 失败 (400_nvcf_degraded),
fallback 到 dsv4p_nv 的 2/2 OK — fallback 路径健康。

### 6h hourly SR

| hour (UTC) | total | ok | ate | SR |
|---|---|---|---|---|
| 12:00 | 6 | 0 | 6 | 0% |
| 13:00 | 2 | 1 | 1 | 50% |
| 14:00 | 2 | 1 | 1 | 50% |
| 15:00 | 4 | 0 | 4 | 0% |
| 16:00 | 6 | 0 | 6 | 0% |
| 17:00 | 6 | 0 | 6 | 0% |

## 根因

### R1: config.py glm5_2_nv inject enable_thinking=True

`/opt/cc-infra/proxy/nv-gw/gateway/config.py` 第 102 行:
```python
"inject": {"chat_template_kwargs": {"enable_thinking": True}},
```

R813 在 HM2 已通过 NVCF 直连实测确认: 3b9748d8 (ai-glm-5_2) thinking 路径 504 退化,
非 thinking 路径 5/5 200 <4s。HM1 一直未同步此修复, 所有 glm5_2_nv 请求
被打到 thinking 路径 → 400_nvcf_degraded → 100% 失败。

### R2: ms_gw handlers.py _relay_stream 无 [DONE] break

ModelScope 上游在 `data: [DONE]` 后不关连接, `resp.read(8192)` 阻塞到
UPSTREAM_TIMEOUT (300s)。R813 HM2 已加 [DONE] break, HM1 未同步。

## 修复方案

### 改动 1: config.py glm5_2_nv inject 改空 (修 R1)

```python
# 改前:
"inject": {"chat_template_kwargs": {"enable_thinking": True}},
# 改后:
"inject": {},
```

strip_params 不变 (`["thinking_budget", "reasoning_effort", "thinking"]`)。
影响: 仅 glm5_2_nv, dsv4p_nv/kimi_nv 不变。

### 改动 2: ms_gw handlers.py _relay_stream [DONE] 后 break (修 R2)

`while True` → `while not done_seen`, 转发完 `[DONE]` 后主动 break,
让下游 (agent collect_stream) 立即收尾, 不再等上游 EOF。

### 不改的项

- 所有 compose 参数不变 (UPSTREAM=66, BUDGET=114, FASTBREAK=1, FALLBACK_HEALTH=0.10 等均已在 floor)
- dsv4p_nv/kimi_nv config 不变
- 本机 (HM2) 配置不变

## 实施步骤

1. 改 config.py 第 102 行 glm5_2_nv inject → `{}` (Python 精确替换). ✅
2. 改 ms_gw handlers.py _relay_stream 加 [DONE] break. ✅
3. `docker restart nv_gw` + `docker restart ms_gw`. ✅
4. 健康检查: nv_gw/health OK, ms_gw/health OK. ✅

## 验证

### V1: config 生效
```bash
sed -n '102p' /opt/cc-infra/proxy/nv-gw/gateway/config.py
# → "inject": {},
```
✅ inject 已清空。

### V2: ms_gw [DONE] break 代码生效
```bash
grep 'MS-STREAM-DONE' /opt/cc-infra/proxy/ms-gw/gateway/handlers.py
# → _log("MS-STREAM-DONE", ...)
```
✅ 代码已部署。

### V3: 容器健康
- `docker ps --filter name=nv_gw` → Up (healthy) ✅
- `docker ps --filter name=ms_gw` → Up (healthy) ✅
- `curl http://localhost:40006/health` → `{"status":"ok"}` ✅

### V4: 预期效果
- glm5_2_nv 走非 thinking 普通模式 → NVCF 恢复 ACTIVE 后 SR 应回升至 ~90% (同 HM2 R813 验证)
- NVCF 当前 DEGRADED 期: 400_nvcf_degraded 是 NVCF 上游故障, 零配置可修
- FALLBACK_GRAPH transient 消失: 重启后应恢复双向 dynamic fallback (R710 pattern)

## 局限与后续

- NVCF 3b9748d8 当前 DEGRADED → 即使 inject 改空, 400_nvcf_degraded 仍会持续 (NVCF 上游)
- FALLBACK_GRAPH transient 消失 (no fallback, 3model) 是 R710 已知模式, 重启后 self-recovery
- 下一轮应验证: FALLBACK_GRAPH 是否恢复双向, glm5_2_nv SR 是否回升

## 提交

- 源码快照: `deploy_artifacts/R816/{config_nv.py,handlers_ms.py}`
- round: `rounds/R816_hm2_optimize_hm1.md`
- 铁律: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2