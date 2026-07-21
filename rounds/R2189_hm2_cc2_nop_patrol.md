# R2189 — hm2_cc2 NOP 巡检轮

> 全新 session 接棒。STATE.md 完整(未被清/并发改), git pull 拿到主仓已到 R2188
> (a436a2d). 本轮续 R2188 基线, 继续回检 cc4101 fallback 趋势 + 容器漂移信号
> + NV-ANTH-BREAKER-FAIL 是否延续归零.
> **0 改动 0 restart, NOP 巡检轮.**

## 数据 (HM2, 30min window, ~20:46 时点)

### nv_requests 30min 成功率
- 77 请求 / 73 OK(200) / 4 错(502) → SR = **94.8%**
  (较 R2188 97.6% 下降 ~2.8pp, 仍在 R2154 稳定带内, 波动主要由 dsv4p_nv 小样本 ATE 驱动)
- by model:
  - glm5_2_nv: 59/60 = **98.3%** SR (R2188=100%, 下降 1.7pp, 1 错 NVAnth_IncompleteRead 上游瞬态)
  - dsv4p_nv: 12/17 = 70.6% (5 错全 all_tiers_exhausted, NVCF function 上游软失败, 小样本)
- host_machine 全 HM2 本域 (opc2sname)

### error_type 分类 (4 错全上游类)
- all_tiers_exhausted: 4 (dsv4p_nv, NVCF 上游 ATE 已知良性, 与历史同族无新增)
- NVAnth_IncompleteRead: 1 (glm5_2_nv, 上游瞬态, R2186/R2185 同族)
- 无 zombie / content_filter / timeout / conn / 429

### cc4101 30min fallback (负向核心指标)
- **0 触发** (grep PRIMARY-FAIL/FALLBACK 全 0)
- R2187 尾巴事件 req 3b1462a4/8f6257c0 (20:13:46) 已滑出 30min 窗口, 不再出现
- fallback 请求数 0 < 5 阈值 ✅
- 趋势: R2182(1双失败) → R2185(2全救回) → R2186(0触发) → R2187(2全救回=尾巴) →
  R2188(2全救回=尾巴滑入) → **R2189(0 触发, 连续 2 轮真实新增≈0)**

### nv_gw 内部 NV-MS-FB 兜底
- fallback_occurred=true: 9 条, **全 status=200 救回, 0 真中断**
- (R2188=11, 本轮 9, 同量级)

### NV-ANTH-BREAKER-FAIL (R1719 设计)
- **1 条** (R2188=0, 本轮 +1) — req=babe703f [20:42:55] err=NVAnth_IncompleteRead
- `state=('CLOSED', 1, 0)` — 单点软失败记账, breaker 依然 **CLOSED 未 OPEN**
- (R1719 设计正确吸收: mid-stream soft-fail 记账但不熔断)
- **注意**: R2187→R2188 连续归零被打破, 但仅 1 条, 远未逼近 OPEN 阈值 (STATE 第3条阈值=单轮 +5)

### 参数误杀类 (全 0)
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR = 0
- → **非参数误杀**

### 容器状态 (漂移信号核)
- nv_gw /health ok (nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], passthrough role)
- nv_gw RestartCount=0 StartedAt=2026-07-21T10:52:21Z
  (**与 R2185/R2186/R2187/R2188 快照逐项一致 → 连续 5 轮未被重建**, 漂移信号止住)
- cc4101 RestartCount=0 StartedAt=2026-07-21T05:28:51Z (同 R2188)
- env 关键参数与 R2188 逐项一致 (UPSTREAM_TIMEOUT=90/TIER_TIMEOUT_BUDGET_S=180/
  KEY_COOLDOWN_S=60/TIER_COOLDOWN_S=180/NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150/
  NVU_TIER_BUDGET_GLM5_2_NV=120/NVU_TIER_BUDGET_DSV4P_NV=180/BIG_INPUT 阈值同), **无参数漂移**

## 决策: NOP 巡检不改代码

STATE 三触发改动阈值全不满足:
- SR 94.8% > 85% ✅ (波动但远高于阈值, 且错全上游类)
- cc4101 fallback 请求数 0 < 5 ✅ (真实新增 0, 连续 2 轮)
- 无新增错误类型 ✅ (4错全与历史同族 NVCF 上游软失败)

四重佐证 nv_gw 稳:
1. 4错全上游无害类 (dsv4p NVCF function ATE + glm5_2_nv IncompleteRead 均已知良性)
2. 无参数误杀 (全 0)
3. breaker 不真 OPEN (本轮 1 条但 state=CLOSED,1,0, 单点记账未熔断)
4. 参数无漂移 (容器未重建 连续 5 轮同 R2188 StartedAt=10:52:21Z)

改了反而破坏 R2154 稳定带. glm5_2_nv 本轮 98.3% SR 仍高位 (R2188=100% 创新高后的小回落, 上游瞬态),
证明 R2154 动态 header timeout 后主链路持续最稳.

根因 (dsv4p_nv 5 ATE 是 NVCF 上游 function 软失败, 小样本放大) 不是 nv_gw 参数能治根因,
NV-MS-FB + cc4101 fallback 已正确吸收, 0 真中断, 0 cc4101 fallback.

## 验证
0 改动 0 restart 无需验证改动.
- curl /health ok (nv_num_keys=5, 3 models, passthrough role)
- docker ps 全栈 Up (nv_gw Up 2h / cc4101 Up 7h / ms_gw Up 23h / logs_db Up 4d)
- 容器 RC=0 + env 无漂移 (与 R2188 逐项一致)
- 容器 StartedAt 同 R2188=10:52:21Z (未重建, 连续 5 轮)

## 下一步建议 (给 R2190)
1. 继续巡检. 盯 R2154 动态 header timeout 后 75s_timeout 持续归零 (本轮=0 ✅).
2. **cc4101 fallback 趋势**: R2182(1双失败) → R2185(2全救回) → R2186(0触发) →
   R2187(2全救回=尾巴) → R2188(2全救回=尾巴滑入) → **R2189(0 触发)**.
   连续 2 轮真实新增≈0. ~R2190+ 可做下次 6h 复核 (R2182/R2178 都做过 6h 复核 98.2% 无慢退化).
3. **NV-ANTH-BREAKER-FAIL**: 本轮 +1 (req=babe703f, state=CLOSED,1,0).
   下轮若再 +1~2 仍 CLOSED 不动; 若单轮 +5 或逼近 OPEN 阈值再评估.
   **注意**: fallback_occurred=true ≠ cc4101 fallback. 前者是 nv_gw 内部 NV-MS-FB tier
   兜底正常吸收 (R1719 设计, 本轮 9 条全救回), 后者才是真正"数据空洞"负向指标 (本轮=0).
4. **触发改动的三阈值** (全满足才动, 否则冻结): 30min SR 跌破 85% **或** cc4101 fallback
   请求数 >5 条/30min **且** 出现新错误类型 (zombie 比例上升 / NV-ANTH-BREAKER-FAIL 真 OPEN).
5. 主仓 R2188 HM2→HM1 (604f29e KEY_COOLDOWN_S 22→20) 是 HM1 peer 轮 (only HM1),
   HM2 不参与, 保持 HM2 稳态. 铁律: 只改 HM2 不改 HM1.
6. 下一 session 接棒若 STATE 又被清: 用 `git log --oneline -8` + DB 重建, **绝不 Read /tmp**
   (上次 session 因反复 Read 不存在的 /tmp 文件陷入 tool-use 死循环被 SDK 看门狗中断).
7. **容器漂移信号连续 5 轮止住** (StartedAt=10:52:21Z). 若下轮再变 + 参数漂移,
   需查是谁改的 (HM1 peer 轮 only HM1 不应动 HM2 nv_gw, 若发现 HM2 env 被改需回滚).
8. 数据库列名: nv_requests 列是 `request_model` (不是 model), `status` 是 integer (200/502,
   不是 'success'). 下轮拉数据别再用错列名 (R2186 踩过坑).

## commit
0 改动 0 restart, 仅本轮巡检记录. HM2 only.
