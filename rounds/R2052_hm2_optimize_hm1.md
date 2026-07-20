# R2052 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 20→18 (-2s)

## 数据 (CST ~15:35, 2026-07-20)

### 6h 窗口 (nv_requests via logs_db)
- 30 req, 25 OK (83.3% SR), 5 fail
- 4 zombie_empty_completion (glm5_2_nv, finish_reason=stop, 38 content chars, 0 reasoning)
- 1 all_tiers_exhausted (glm5_2_nv, status=502, 40.0s, tiers_tried=1)
- 7 total ATE rows but 6 are phantom ATE (status=200), only 1 real 502 ATE
- glm5_2_nv: 28 req, 23 OK (82.1% SR), avg_ok_ms=10408, 5 fail
- dsv4p_nv: 2 req, 2 OK (100%), avg_ok_ms=9944
- Key cycling: glm5_2_nv 23 events (20 single-cycle 429, 3 double-cycle)
- Docker logs: 0 errors/warnings (1 zombie detected and handled inline)

### 30min 窗口
- 3 req (latest burst), 3 OK (100% SR)

### 容器 env (live, before change)
- NVU_TIER_BUDGET_GLM5_2_NV=20, TIER_TIMEOUT_BUDGET_S=153, UPSTREAM_TIMEOUT=24
- NVU_BIG_INPUT_COOLDOWN_S=1800, NVU_EMPTY_200_FASTBREAK=1
- KEY_COOLDOWN_S=0, TIER_COOLDOWN_S=0, NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_STREAM_TOTAL_DEADLINE_S=25, NVU_STREAM_FIRST_BYTE_DEADLINE_S=15

## 分析

6h 窗口 5 失败中 4 是 zombie_empty_completion (glm5_2_nv NVCF 层空响应，不可修)。1 真实 ATE 仅 1 key 尝试后 tier exhausted。OK max=9201ms (R2013 baseline)。当前 budget=20s 有 10.8s headroom。减到 18s 仍有 8.8s margin，成功路径完全安全。zombie 平均 ~7.5s，预算是 zombie 超时路径的 cup — FASTBREAK=1 时第一个 empty200 即触发 tier exhaustion，budget 越小越快退出。每 zombie 省 2s，4 zombie/6h 共省 8s 级联延迟。Peer-fb 约束：18+122=140<153 BUDGET（13s margin）。

## 改动

NVU_TIER_BUDGET_GLM5_2_NV: 20 → 18 (-2s)

注：UPSTREAM_TIMEOUT 也在 compose line 488 标注为 R2052 的 25→24 改动。该改动在本轮之前已应用到 HM1 compose（live env=24），非本轮发起。本轮仅改 NVU_TIER_BUDGET_GLM5_2_NV。

单参数对；铁律：只改 HM1 不改 HM2。

## 验证

- Compose line 649 sed 写入确认: `NVU_TIER_BUDGET_GLM5_2_NV: "18"` ✓
- 容器重启: `docker compose up -d nv_gw` → Recreated/Started ✓
- Live env 确认: `docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV` → 18 ✓
- 容器日志: Listening on 0.0.0.0:40006 ✓
## ⏳ 轮到HM1优化HM2
