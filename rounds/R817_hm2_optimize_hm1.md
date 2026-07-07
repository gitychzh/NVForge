# R817: HM2→HM1 — FALLBACK_GRAPH self-recovery restart (no config change)

**时间**: 2026-07-08 02:22 UTC
**决策**: NOP重启 — 仅重启容器触发 FALLBACK_GRAPH self-recovery, 零参数变更
**作者**: opc2_uname (HM2→HM1)

## 数据采集

### 容器状态
- Container: `nv_gw`, Up 15min (R816 restart at 17:55 UTC), 本回合重启 at 18:22 UTC
- Container: `ms_gw`, Up 10min (healthy)
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=114, FASTBREAK=1
- FALLBACK_HEALTH_THRESHOLD=0.10, FORCE_STREAM_UPGRADE_TIMEOUT=66 ✅
- 所有 compose 参数在 floor 值

### 6h 总体统计 (12:22-18:22 UTC)

| 指标 | 值 |
|------|---|
| 总请求 | 51 |
| OK (200) | 14 |
| ATE (502) | 37 |
| **6h SR** | **27.5%** |

### 6h ATE tiers_tried_count

| tiers_tried_count | cnt | 
|---|---|
| 1 (单tier) | 32 |
| 2 (双tier) | 5 |

32/37 ATE (86.5%) 为单tier — FALLBACK_GRAPH 缺失导致 fallback 未触发。

### 6h 错误类型

| error_type | cnt |
|---|---|
| all_tiers_exhausted | 37 |

### nv_tier_attempts (6h)

| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| dsv4p_nv | 504_nv_gateway_timeout | 2 | — | — |
| dsv4p_nv | NVCFPexecTimeout | 1 | 51,165 | 51,165 |
| glm5_2_nv | 400_nvcf_degraded | 28 | — | — |

### Fallback SR

| fallback_occurred | total | ok | SR |
|---|---|---|---|
| f (direct) | 46 | 9 | 19.6% |
| t (fallback) | 5 | 5 | **100%** ✅ |

### tier_chain 动态 (docker logs)

```
02:06-02:12 UTC: tier_chain=['dsv4p_nv'] (no fallback, 3model) — dsv4p_nv 无 fallback
02:10-02:19 UTC: tier_chain=['glm5_2_nv'] (no fallback, 3model) — glm5_2_nv 无 fallback
```

**两个模型同时 (no fallback, 3model)** → R710 pattern: FALLBACK_GRAPH transient disappearance (Python runtime module-reload/import-order race)。

### 最近30min请求 (17:30-18:22 UTC)

- 全部 20 条请求: 10 条 dsv4p_nv (5 OK, 5 ATE), 10 条 glm5_2_nv (0 OK, 10 ATE)
- 全部 fallback_occurred=f, tiers_tried_count=1
- glm5_2_nv: 5 key 全 400_nvcf_degraded (NVCF 3b9748d8 DEGRADED)
- dsv4p_nv: empty_200 主导失败 (NVCF 74f02205 上游问题)

### config.py FALLBACK_GRAPH 验证

```
docker exec nv_gw grep -n 'FALLBACK_GRAPH' /app/gateway/config.py
→ 196: FALLBACK_GRAPH = {
→ dsv4p_nv → [glm5_2_nv], glm5_2_nv → [dsv4p_nv], glm5_1_nv → [dsv4p_nv]
```

config.py 中 FALLBACK_GRAPH 配置正确，但运行时未能加载 → R710 已知 Python runtime 竞态。

## 根因诊断

### R1: FALLBACK_GRAPH transient disappearance (R710 pattern)

R816 重启后 FALLBACK_GRAPH 未恢复 — 两个模型同时 (no fallback, 3model)。
这是 R710 已知的 Python runtime module-reload/import-order race。
在 R816 修复中，`config_nv.py` 仅作为 deploy artifact 写入，未通过 `docker compose up -d` 重新构建镜像。
`docker compose restart` 重启容器但挂载的 config.py 已正确，FALLBACK_GRAPH 在源码中存在但运行时未加载。

**R710 signature confirmed**: BOTH models show (no fallback, 3model) simultaneously,
NOT just one model (排除 HEALTH_THRESHOLD kill) → FALLBACK_GRAPH loading race.

### R2: glm5_2_nv NVCF DEGRADED (400_nvcf_degraded)

NVCF function 3b9748d8 (ai-glm-5_2) 对所有 5 个 key 返回 400 DEGRADED。
28 次 tier_attempt 全部 400_nvcf_degraded，零配置可修。
R816 已清空 inject (走非 thinking 路径)，但 NVCF function 本身 DEGRADED → 无法修复。

### R3: dsv4p_nv empty_200

NVCF 74f02205 偶尔返回 Content-Length:0 stream 空响应。
empty_200=1 (FASTBREAK=1 立即 break)，NVCF 上游问题。

## NOP 决策 (6 Gates)

### Gate 1: All ATEs double-tier? ❌
32 single-tier, 5 double-tier — FALLBACK_GRAPH 缺失导致。

### Gate 2: Zero single-tier ATEs? ❌
32 single-tier，全部 fallback_actually_attempted=f → FALLBACK_GRAPH 未加载。

### Gate 3: NVCFPexecTimeout buffer ≥3s?
dsv4p_nv max=51,165ms @ UPSTREAM=66 → buffer=14.8s ✅ (non-binding)
glm5_2_nv: 零 NVCFPexecTimeout (全部 400_nvcf_degraded) → N/A

### Gate 4: FALLBACK_GRAPH bidirectional? ❌
(no fallback, 3model) on both models → FALLBACK_GRAPH 未加载。

### Gate 5: Fallback SR = 100%? ✅
5/5 fallback 100% SR — fallback 路径健康。

### Gate 6: All params at floor? ✅
UPSTREAM=66, BUDGET=114, FASTBREAK=1, EMPTY_200_FASTBREAK=1,
FALLBACK_HEALTH=0.10, CONNECT_RESERVE=0, MIN_OUTBOUND=0,
INTEGRATE_COOLDOWN=0, FORCE_STREAM=0, FORCE_STREAM_UPGRADE_TIMEOUT=66 ✅

**Decision**: 不是 NOP — Gate 1/2/4 失败 (FALLBACK_GRAPH 缺失)。
但也不是参数变更 — 根因是 R710 FALLBACK_GRAPH transient 消失 + NVCF glm5_2 DEGRADED。
唯一可行修复: 重启容器触发 FALLBACK_GRAPH self-recovery。

## 修复方案

### 操作: docker compose restart nv_gw

**不改任何参数** — 所有 compose 参数已在 floor 值。
仅重启容器以触发 FALLBACK_GRAPH 重新加载 (R710 self-recovery pattern)。

```bash
cd /opt/cc-infra && docker compose restart nv_gw
```

### 不改的项

- 所有 compose 参数不变 (UPSTREAM=66, BUDGET=114, FASTBREAK=1, 等均已在 floor)
- config.py 不变 (R816 已修复 glm5_2 inject)
- handlers_ms.py 不变 (R816 已修复 [DONE] break)
- 本机 (HM2) 配置不变
- 铁律: 只改 HM1 不改 HM2

## 实施步骤

1. `docker compose restart nv_gw` ✅ (18:22 UTC)
2. 健康检查: container healthy ✅
3. 等待流量验证 FALLBACK_GRAPH 恢复

## 验证

### V1: 容器健康
- `docker ps --filter name=nv_gw` → Up (healthy) ✅
- `curl http://localhost:40006/health` → `{"status":"ok"}` ✅
- 重启时间: 2026-07-07T18:22:04Z

### V2: 预期效果
- FALLBACK_GRAPH 恢复 → tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback)
- glm5_2_nv 走非 thinking 路径 (R816 inject 清空) → 当 NVCF 3b9748d8 恢复 ACTIVE 时 SR 应回升
- 当前 NVCF DEGRADED 期: 400_nvcf_degraded 是 NVCF 上游故障，零配置可修
- dsv4p_nv empty_200 是 NVCF 上游，零配置可修

## 局限与后续

- NVCF 3b9748d8 当前 DEGRADED → 即使 FALLBACK_GRAPH 恢复，glm5_2_nv 仍 100% 失败
- FALLBACK_GRAPH self-recovery 需等待流量验证 (当前无新请求)
- 下一轮应验证: tier_chain 是否恢复双向 dynamic fallback
- 如果 FALLBACK_GRAPH 持续不恢复 → 需要 `docker compose up -d nv_gw` (重新构建镜像) 替代 restart

## 提交

- round: `rounds/R817_hm2_optimize_hm1.md`
- 铁律: 只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2