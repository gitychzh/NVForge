# R2188 — hm2_cc2 NOP 巡检轮 (0 改动 0 restart)

## 基线
- 接棒 STATE.md (R2187 完整未被并发改). git pull 已最新 (820cfa6 R2187).
- 本轮 = R2188, 续 R2187 基线.

## 数据 (HM2, 30min window, ~20:27 时点)
- 85 请求 / 83 OK(200) / 2 错(502) → **SR = 97.6%**
  (较 R2187 95.8% 上升 1.8pp, 仍在 R2154 稳定带内且走高)
- by model: glm5_2_nv 66/66 = **100%** SR (本轮新高, R2187=98.6%); dsv4p_nv 18/20 = 90% (2 错全 all_tiers_exhausted)
- 2 错 error_type: 2 all_tiers_exhausted (NVCF function ATE 已知良性, 与历史同族无新增)
- 无 zombie / content_filter / timeout / conn / 429

## cc4101 30min fallback (负向核心指标)
- 2 个请求, **全 FALLBACK-OK 救回, 0 双失败**
  - req=3b1462a4 [20:13:46] PRIMARY-FAIL (glm5_2_nv header/ttfb 120s timeout) → [20:14:07] FALLBACK-OK (ms 20727ms)
  - req=8f6257c0 [20:13:46] PRIMARY-FAIL (glm5_2_nv header/ttfb 60s timeout, SKIP-CIRCUIT 未计熔断) → [20:14:03] FALLBACK-OK (ms 16572ms)
- **重要细节**: 这 2 个 req id + 时点(20:13:46) 与 R2187 记录完全一致 → 是 R2187 窗口的尾巴事件滑进 R2188 的 30min 窗口, **非本窗口新发生**的 fallback. 即本窗口"真实新增"fallback ≈ 0.
- 趋势: R2182(1双失败) → R2185(2全救回) → R2186(0触发) → R2187(2全救回) → R2188(2全救回=R2187尾巴滑入) — 连续恶化止住延续, 未出现双失败.
- fallback 请求数 2 < 5 阈值 ✅

## nv_gw 内部 NV-MS-FB 兜底
- fallback_occurred=true: 11 条, **全 status=200 救回, 0 真中断**
- (R2187=12, 本轮 11, 同量级)

## NV-ANTH-BREAKER-FAIL (R1719 设计)
- **0 条** (R2187=0, 连续归零)

## 参数误杀类 (全 0)
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR = 0
- → **非参数误杀**

## 容器状态 (漂移信号核)
- nv_gw /health ok (nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], passthrough role)
- nv_gw RestartCount=0 StartedAt=2026-07-21T10:52:21Z
  (**与 R2185/R2186/R2187 快照逐项一致 → 未被重建**, 漂移信号连续 4 轮止住)
- cc4101 RestartCount=0 StartedAt=2026-07-21T05:28:51Z (同 R2187)
- env 关键参数与 R2187 逐项一致 (UPSTREAM_TIMEOUT=90/TIER_TIMEOUT_BUDGET_S=180/
  KEY_COOLDOWN_S=60/TIER_COOLDOWN_S=180/NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150/
  NVU_TIER_BUDGET_GLM5_2_NV=120/NVU_TIER_BUDGET_DSV4P_NV=180/BIG_INPUT 阈值同), **无参数漂移**

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值全不满足:
- SR 97.6% > 85% ✅ 在阈值之上 (且较 R2187 上升)
- cc4101 fallback 请求数 2 < 5 ✅ (低于阈值, 全救回; 且实为 R2187 尾巴滑入)
- 无新增错误类型 ✅ (2 错与历史同族 NVCF 上游软失败)
四重佐证 nv_gw 稳: 2错全上游无害类(dsv4p NVCF function ATE 已知良性) / 无参数误杀(全0) /
breaker 不真 OPEN(本轮0条连续归零) / 参数无漂移(容器未重建 同 R2187). 改了反而破坏 R2154 稳定带.
glm5_2_nv 本轮 100% SR 创新高, 证明 R2154 动态 header timeout 后主链路最稳.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 +
env 无漂移 (与 R2187 逐项一致). 容器 StartedAt 同 R2187=10:52:21Z (未重建).

## HM2 only, 不碰 ms_gw/HM1
