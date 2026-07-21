# R2180 — hm2_cc2 巡检轮 (R2179 后首条 cc4101 fallback 瞬时, 三阈值仍不满足 → 冻结)

## 当前轮号基线
- 主仓 git: `cf7e037 R2179` (上一轮 hm2_cc2 NOP, 已 push)
- 本轮: **R2180 — hm2_cc2 NOP 巡检轮, 0 改动 0 restart**
- 接棒: 全新 session, STATE.md 完整未被并发改 (cat 确认)

## 数据 (HM2, 30min window, ~18:20 时点)
- 106 req / 102 OK(200) / 4 错(502) → SR = **96.2%** (102/106, 较 R2179 94.8% 升, 稳态带)
- by request_model: glm5_2_nv 72/72 = **100%** SR ✅; dsv4p_nv 30/34 = 88% (4错全 all_tiers_exhausted)
- 4 错全 NVCF 上游无害类: 4 all_tiers_exhausted (dsv4p_nv NVCF function 74f02205 全挂, 同 R2177-R2179 已知良性)
- nv_gw 入口侧无 content_filter / timeout(conn) / 429
- nv_gw tier_attempts 30min: 68 pexec_success + 11 pexec_conn_RemoteDisconnected + 4 pexec_429
  + 2 NVCFPexecRemoteDisconnected + 2 pexec_500 (全 NVCF 上游瞬态, nv_gw 内部重试/tier 切换正常吸收)
- **cc4101 30min fallback 真中断 = 1** (R2177-R2179 连续 3 轮 0 后首条):
  - req=6cee1777 glm5_2_nv **header/ttfb timeout after 160s** (ttfb=160104ms) → PRIMARY-FAIL
  → 摔 ms_gw glm5_2_ms FALLBACK-OK 7308ms 救回
  - 该条未进 nv_requests 502 列 (cc4101 层 fallback 吞掉), 故 glm5_2_nv DB 仍 72/72
- nv_requests.fallback_occurred=true 9 条 → 全是 nv_gw 内部 NV-MS-FB tier 兜底 (R1719 设计), 非 cc4101 层
- **另两条 glm5_2_nv 慢上游被 nv_gw 内 peek 机制正确吸收 (R1918 BUG-B 方案0)**:
  - req=a43a87c4 ttfb=161387ms → NV-PEEK-CAP-RESET (ttfb>150s abs_cap 主动 reset 防秒触发 abs_cap)
  - req=162a933e ttfb=155456ms → NV-PEEK-CAP-RESET 同样分支
  - 这俩没让 cc4101 到 160s timeout, 是 nv_gw 自己先 cap-RESET 切走了
- NV-ANTH-BREAKER-FAIL / 75s_timeout / STREAM-STALL-FAIL / UPSTREAM-ERROR-SEEN = **0** (breaker 全程 CLOSED)
- 容器无漂移: nv_gw RestartCount=0 StartedAt=2026-07-21T01:44:55Z, cc4101 RestartCount=0 StartedAt=2026-07-21T05:28:51Z

## 决策: NOP 冻结 (三阈值全不满足)
- SR 96.2% > 85% ✅ 在阈值之上 (还较 R2179 升)
- cc4101 fallback = 1 < 5 ✅ 在阈值之下 (单条瞬时, 没破 5 阈值)
- 无新错误类型 ✅ (仍 all_tiers_exhausted, glm5_2_nv 失败是 ttfb 慢上游非分类变更)

**为何不改**: 这条 cc4101 fallback 是 glm5_2_nv 上游 NVCF 单 IP (134.195.101.x) ttfb 160s 瞬时慢,
不是 nv_gw 代码问题。证据链:
1. 同窗口另两条 glm5_2_nv 慢 (ttfb 161s/155s) 被 nv_gw peek cap-RESET 正确吸收 (R1918 BUG-B 方案0 设计内);
2. cc4101 自己 160s header timeout 摔开是它自己的链路保护, 摔 ms_gw OK 救回 = 设计内兜底;
3. breaker 全程 CLOSED, 75s_timeout=0, STALL=0 — nv_gw 内部所有阈值机制没误触;
4. env 参数与 R2179 快照逐项一致, 容器无漂移。
改 nv_gw 参数 (如 UPSTREAM_TIMEOUT) 反而会破坏 R2154 稳定带 + R1918 cap-RESET 机制, 风险>收益。
glm5_2_nv 100% SR (DB 侧) + peek cap-RESET 持续生效 = 上游瞬时慢被设计内吸收, 没有趋势性恶化。

## 验证
0 改动 0 restart 无需验证改动。
- `curl /health` ok: nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], proxy_role=passthrough
- docker ps 全栈 Up: nv_gw Up 9h / cc4101 Up 5h / logs_db Up 4d
- env 关键参数与 R2179 快照逐项一致 (MIN_OUTBOUND=10, KEY_COOLDOWN=60, UPSTREAM_TIMEOUT=90, TIER_*_BUDGET/COOLDOWN=180)
- 容器 RestartCount 全 0, StartedAt 与 R2179 一致 (01:44:55Z / 05:28:51Z)

## 下一轮该做什么
1. 继续巡检。盯 cc4101 fallback 是否仍为单条瞬时 (本轮=1) 还是开始累积趋势:
   若连续 2 轮 >1 或单轮破 5 → 才评估调 nv_gw peek cap 阈值或 UPSTREAM_TIMEOUT。
2. 盯 glm5_2_nv ttfb 慢 (>150s) 触发 NV-PEEK-CAP-RESET 的频率:
   本轮 2 条 (req=a43a87c4 161s, req=162a933e 155s)。若下次 >4 条/30min → 上游慢在加剧, 需评估。
3. NV-ANTH-BREAKER-FAIL / 75s_timeout / STALL 仍 0 (本轮 ✅)。
4. **触发改动的三阈值** (全满足才动, 否则冻结): 30min SR 跌破 85% **或**
   cc4101 fallback >5 条/30min **且** 出现新错误类型 (zombie 比例上升 / NV-ANTH-BREAKER-FAIL 真 OPEN)。
5. 主仓 R21XX alternating -2s 是 HM1 peer 轮 (only HM1), HM2 不参与, 保持 HM2 稳态。铁律: 只改 HM2 不改 HM1。
6. 下一 session 接棒若 STATE 又被清: 用 `git log --oneline -8` + DB 重建, **绝不 Read /tmp**。
7. R2178 已做 6h 复核。下次 6h 复核放 ~R2185+ (约 5 轮 30min NOP 后)。

## commit
本轮 0 改动 0 restart, 仅本巡检记录文件 commit。
