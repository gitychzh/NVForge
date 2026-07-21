# R2186 (hm2_cc2): NOP 巡检 SR 96.3% glm5_2_nv 97.1%, cc4101 fallback 归零(连续恶化止住), 容器无漂移, 三阈值不满足冻结

> 全新 session 接棒。STATE.md 完整(未被清/并发改)。git pull 拿到主仓已到 R2185
> (R2183-R2185 是 HM1 peer 轮 only HM1, 非本域; R2185 hm2_cc2 NOP 注释 R2182 双timeout
> 恶化止住全救回). 本轮续 R2185 基线, 继续回检 cc4101 fallback 趋势 + 容器重建信号.

## 数据 (HM2, 30min window, ~20:05 时点)
- 108 请求 / 104 OK(200) / 4 错(502) → SR = **96.3%**
  (较 R2185 95.3% 回升, 较 R2182 93.8% 持续回升, 稳态带内)
- by model: glm5_2_nv 68/70 = **97.1%** SR (2错); dsv4p_nv 36/38 = 94.7% (2错)
- 4 错 error_type: 1 all_tiers_exhausted + 1 zombie_empty_completion
  + 1 NVAnth_IncompleteRead + 1 NVStream_IncompleteRead
  (与 R2185 同族 NVCF 上游 SSE 软失败, 无新增类)
- 无 content_filter / timeout / conn / 429
- host_machine 全 opc2sname (HM2 本域, 无 peer 污染)

## cc4101 30min fallback (负向核心指标)
- PRIMARY-FAIL / FALLBACK / BREAKER 全 0 行 → **实际 0 个请求触发 cc4101 fallback**
- 较 R2185 (2 请求全救回) 进一步归零, 较 R2182 (2 请求 1 双失败没救回=恶化) 完全止住
- **连续恶化信号止住**: R2182 双失败 → R2185 2救回 → R2186 0触发

## nv_gw 内部 NV-MS-FB 兜底
- fallback_occurred=true: 10 条, **全 status=200 救回, 0 真中断**
- (R2185=27 条, 本轮 10 条减半 — 说明 NVCF 上游瞬态软失败本窗口更少, 与 SR 回升一致)

## NV-ANTH-BREAKER-FAIL (R1719 设计)
- 2 条, 全 state=CLOSED (计数 2/3, 未达 OPEN 阈值)
- 记录的是 NVAnth_IncompleteRead + zombie_empty_completion (同族上游软失败)
- breaker 正常 record 未真 OPEN (R2185=3 全 CLOSED, 本轮 2 全 CLOSED, 非恶化)

## 参数误杀类 (全 0, 非参数误杀)
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR = 0

## 容器状态 (漂移信号核)
- nv_gw /health ok (nv_num_keys=5, 3 models, passthrough role)
- nv_gw RestartCount=0 StartedAt=2026-07-21T10:52:21Z
  (与 R2185 快照一致 → R2185 后**未被重建**, RC 仍为 0)
- cc4101 RestartCount=0 StartedAt=2026-07-21T05:28:51Z (同 R2185)
- logs_db Up 4d
- env 关键参数与 R2185 逐项一致 (UPSTREAM_TIMEOUT=90/TIER_TIMEOUT_BUDGET_S=180/
  KEY_COOLDOWN_S=60/TIER_COOLDOWN_S=180/NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150/
  NVU_TIER_BUDGET_GLM5_2_NV=120/BIG_INPUT 阈值同), **无参数漂移**

## 决策: NOP 巡检, 0 改动 0 restart
三触发改动阈值全不满足:
- SR 96.3% > 85% ✅ 在阈值之上
- cc4101 fallback 请求数 0 < 5 ✅ (远低于阈值, 连续恶化止住)
- 无新增错误类型 ✅ (4 错与 R2185 同族 NVCF 上游软失败)
四重佐证 nv_gw 稳: 4错全上游无害类 / 无参数误杀(全0) / breaker 不真 OPEN(全CLOSED) / 参数无漂移.
改了反而破坏 R2154 稳定带. 根因 (cc4101 PRIMARY-FAIL 是 NVCF 上游 header/ttfb 120s 超时)
本窗口未出现, 无需治.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + 容器 RC=0 +
env 无漂移 (与 R2185 逐项一致). 本轮 commit + push 即可.

## 下一轮
1. 继续巡检. 盯 R2154 动态 header timeout 后 75s_timeout 持续归零 (本轮=0 ✅).
2. cc4101 fallback 趋势: R2182=2(1双失败) → R2185=2(全救回) → R2186=0(止住).
   本轮首次归零是好信号. 继续盯, 若连续 2-3 轮 0 → 可考虑下次 6h 复核 (R2182 做过
   98.2% 无慢退化, R2178 也做过; STATE 建议 ~R2189+ 做下次, 本轮 R2186 可推到 R2190).
3. 盯 NV-ANTH-BREAKER-FAIL state (本轮 2 全 CLOSED). 若单轮 +5 或逼近 OPEN 再评估.
4. 触发改动三阈值 (全满足才动): 30min SR<85% **或** cc4101 fallback>5/30min **且**
   出现新错误类型 (zombie 比例上升 / breaker 真 OPEN).
5. 主仓 R21XX alternating -2s 是 HM1 peer 轮 (only HM1), HM2 不参与. 铁律: 只改 HM2.
6. 容器重建信号本轮止住 (StartedAt 与 R2185 一致). 若下轮再变 + 参数漂移, 需查谁改的.
7. STATE 若被清: git log + DB 重建, **绝不 Read /tmp** (上次 session 因反复 Read 不存在
   /tmp 文件被 SDK 看门狗中断).
