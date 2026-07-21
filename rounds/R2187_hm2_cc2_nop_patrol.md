# R2187 (hm2_cc2): NOP 巡检轮 — SR 95.8% glm5_2_nv 98.6%, cc4101 fallback 2全救回(连续恶化止住延续), breaker 归零, 容器无漂���, 三阈值不满足冻结

## 基线
- 主仓 git: `3b13f8c R2186 (hm2->hm1): TIER_COOLDOWN_S 10->8` 之上
- 上一轮 hm2_cc2: R2186 (NOP 巡检, commit e6b3544, SR 96.3%, cc4101 fallback=0首次归零)
- 本轮: **R2187 — hm2_cc2 NOP 巡检轮, 0 改动 0 restart**
- 铁律: 只改 HM2 不改 HM1; 聚焦 40006 不碰 40007(重启窗口热备)

## 数据 (HM2, 30min window, ~20:14 时点)
- 97 请求 / 93 OK(200) / 4 错(502) → SR = **95.8%**
  (较 R2186 96.3% 微降, 仍在 R2154 稳定带内; 长 6h 复核下次推迟到 R2190+)
- by model: glm5_2_nv 71/72 = **98.6%** SR (1 zombie); dsv4p_nv 22/25 = 88% (3 错全 all_tiers_exhausted)
- 4 错 error_type: 3 all_tiers_exhausted + 1 zombie_empty_completion
  (与 R2185/R2186 同族 NVCF 上游 SSE 软失败, 无新增类)
- 无 content_filter / timeout / conn / 429
- host_machine 全 opc2sname (HM2 本域)

**cc4101 30min fallback (负向核心指标)**:
- 2 个请求, **全 FALLBACK-OK 救回, 0 双失败**
  - req=3b1462a4 [20:13:46] PRIMARY-FAIL (glm5_2_nv header/ttfb 120s timeout) → [20:14:07] FALLBACK-OK (ms 20727ms 救回)
  - req=8f6257c0 [20:13:46] PRIMARY-FAIL (glm5_2_nv header/ttfb 60s timeout, SKIP-CIRCUIT 未计熔断, cc4101 pre-empted nv_gw retry) → [20:14:03] FALLBACK-OK (ms 16572ms 救回)
- R2182 恶化趋势仍止住: R2182(1双失败) → R2185(2全救回) → R2186(0触发) → R2187(2全救回)
- fallback 请求数 2 < 5 阈值 ✅

**nv_gw 内部 NV-MS-FB 兜底**:
- fallback_occurred=true: 12 条, **全 status=200 救回, 0 真中断**
- (R2186=10, 本轮 12, 同量级)

**NV-ANTH-BREAKER-FAIL** (R1719 设计):
- **0 条** (R2186=2 全 CLOSED, 本轮归零, 更好)

**参数误杀类 (全 0)**:
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR = 0
- → **非参数误杀**

**容器状态 (漂移信号核)**:
- nv_gw /health ok (nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], passthrough role)
- nv_gw RestartCount=0 StartedAt=2026-07-21T10:52:21Z
  (**与 R2185/R2186 快照逐项一致 → R2186 后未被重建**, 漂移信号止住)
- cc4101 RestartCount=0 StartedAt=2026-07-21T05:28:51Z (同 R2186)
- env 关键参数与 R2186 逐项一致 (UPSTREAM_TIMEOUT=90/TIER_TIMEOUT_BUDGET_S=180/
  KEY_COOLDOWN_S=60/TIER_COOLDOWN_S=180/NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150/
  NVU_TIER_BUDGET_GLM5_2_NV=120/NVU_TIER_BUDGET_DSV4P_NV=180/BIG_INPUT 阈值同), **无参数漂移**

## 决策: NOP 巡检不改代码
STATE 三触发改动阈值全不满足:
- SR 95.8% > 85% ✅ 在阈值之上
- cc4101 fallback 请求数 2 < 5 ✅ (低于阈值, 全救回)
- 无新增错误类型 ✅ (4 错与 R2182-R2186 同族 NVCF 上游软失败)

四重佐证 nv_gw 稳: 4错全上游无害类(dsv4p NVCF function ATE 已知良性) / 无参数误杀(全0) /
breaker 不真 OPEN(本轮0条) / 参数无漂移(容器未重建 同 R2186). 改了反而破坏 R2154 稳定带.

根因 (cc4101 PRIMARY-FAIL 是 NVCF 上游 glm5_2_nv header/ttfb 60/120s 超时, cc4101 自己判定
比 nv_gw TIER_TIMEOUT_BUDGET=180 短) 本窗口 2 次但全被 ms 救回 — 不是 nv_gw 参数能治根因,
NV-MS-FB + cc4101 fallback 已正确吸收, 0 真中断. 调 nv_gw 参数治不了 NVCF 上游慢/软失败.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 +
env 无漂移 (与 R2186 逐项一致). 容器 StartedAt 同 R2186=10:52:21Z (未重建).

## commit
本轮 0 改动, 仅轮文件 + STATE 更新.
