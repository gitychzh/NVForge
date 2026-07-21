# R2177 (hm2_cc2): NOP 巡检轮 — 稳态延续 + NV-MS-FB 链路分类澄清, 0 改动 0 restart

## 上下文
全新 session 接棒 R2176。STATE.md 完整未被并发改, git pull 拿到 c5d4658(主仓 R2175 HM2->HM1 KEY_COOLDOWN 32->30, HM1 peer 轮 only HM1) + 3146348(R2176 hm2_cc2 NOP)。
本轮纯巡检, 遵守"三阈值全满足才动, 否则冻结"。本轮额外做了一处数据解读改进:
**把 cc4101 fallback (=0) 与 nv_gw 内部 NV-MS-FB tier 兜底 (=8 fallback_occurred) 明确区分**,
澄清"8 条 fallback_occurred"并非 cc4101 层热备兜底, 而是 nv_gw 内部 tier chain (glm5_2_nv→glm5_2_ms)
的正常吸收 —— 这是 R1719 breaker 设计的预期行为, 不是负向指标恶化。

## 数据 (HM2, 30min window)
- **90 请求 / 85 OK(200) / 5 错(502) → SR = 94.4%** (85/90, 较 R2176 91.0% 上升, 带内偏强)
- by model: **glm5_2_nv 77/78 = 98.7% SR** (1错: zombie_empty_completion 1);
  dsv4p_nv 8/12=67% (4错全 all_tiers_exhausted, NVCF function 74f02205 全挂非本域已知良性)
- 5 错全 NVCF 上游无害类: 4 all_tiers_exhausted + 1 zombie_empty_completion
- 无 content_filter / timeout / conn / 429
- nv_gw tier_attempts 30min: 70 pexec_success + 4 pexec_SSLEOFError + 3 pexec_conn_RemoteDisconnected
  + 2 NVCFPexecRemoteDisconnected + 1 empty_200 + 1 pexec_empty_200 (全 NVCF 上游瞬态, nv_gw 内部重试/tier 切换正常吸收)
- cc4101 30min fallback 计数 = **0** (较 R2176 的 0 同等干净, 连续第 2 轮 0 真中断)
- nv_requests.fallback_occurred=true 8 条 → **本轮澄清: 全是 nv_gw 内部 NV-MS-FB tier 兜底**
  (glm5_2_nv all_keys_exhausted → 甩 glm5_2_ms 热备), **非 cc4101 层 fallback**。
  日志佐证: 4 次 [NV-MS-FB-ATTEMPT]+[NV-MS-FB-SERVED] 配对, breaker state 全程 CLOSED。
- NV-ANTH-BREAKER-FAIL: **1 条** (req=775986be, zombie_empty_completion), 但
  `state=('CLOSED', 4, 0)` — 累计 4 次计数, **未 OPEN**。这正是 R1719 breaker 设计的
  "记录但不 OPEN" 预期态 (阈值未触, "几乎不 OPEN" 目标达成)。
- 75s_timeout = **0** (R2154 动态 header timeout 持续生效, cc4101 无误杀)
- STREAM-STALL-FAIL / UPSTREAM-ERROR-SEEN = 0
- nv_gw big_input / nv_breaker: **未真 OPEN** (仅 NV-ANTH 记录计数, state=CLOSED)
- 容器无漂移: nv_gw RestartCount=0 StartedAt=2026-07-21T01:44:55Z, cc4101 RestartCount=0 StartedAt=2026-07-21T05:28:51Z

## 决策: NOP 巡检不改代码
三触发改动阈值全不满足:
- SR 94.4% > 85% ✅ 在阈值之上 (较 R2176 91.0% / R2175 89.5% 连续上升)
- cc4101 fallback 0 < 5 ✅ 在阈值之下 (连续第 2 轮 0)
- 无新错误类型 (仍 all_tiers_exhausted + zombie) ✅

glm5_2_nv 98.7% 稳态带内偏强 (R2176 97.1% / R2175 96.7% / R2157 98.4%, 同带宽正常波动)。
四重佐证 nv_gw 稳: 5错全上游无害类 / 无参数误杀(75s_timeout=0 STALL=0) /
breaker 不真 OPEN(NV-ANTH 记录但 CLOSED) / 容器无漂移。改了反而破坏 R2154 稳定带。

**NV-ANTH-BREAKER-FAIL 计数 (state=4) 的处理**: 这是软挂累积, 距 OPEN 阈值尚远且
当前每 30min 仅 +1-2。按 CLAUDE.md "目标让 breaker 几乎不 OPEN 而非调高阈值假装不 OPEN",
本轮冻结不动 nv_breaker 阈值。若后续 30min 计数突增 (如单轮 +5 或 state 逼近 OPEN),
再在下一轮评估 —— 但那应是 NVCF 上游变化触发的, 不是 nv_gw 参数问题。

## 验证
0 改动 0 restart 无需验证改动。
- curl /health: ok (nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], proxy_role=passthrough)
- docker ps: nv_gw Up 8h / cc4101 Up 4h / logs_db Up 4d, 全栈 Up
- DB 30min 窗口稳态带内偏强 (见上)
- 参数 env 与 R2176 基线逐项一致 (KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=180,
  UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_GLM5_2_NV=120,
  NVU_BIG_INPUT_FAIL_N=1, NVU_FORCE_STREAM_UPGRADE=0, KEY_AUTHFAIL_COOLDOWN_S=60,
  NV_INTEGRATE_KEY_COOLDOWN_S=90 等全无漂移)

## 下一轮
1. 继续巡检。盯 75s_timeout 持续归零 / cc4101 fallback 仍 0 / glm5_2_nv SR 长期 >95% 无慢退化。
2. 盯 NV-ANTH-BREAKER-FAIL 的 state 计数 (本轮 4, CLOSED)。若单轮 +5 或逼近 OPEN 阈值再评估。
3. 保持 NV-MS-FB 内部 tier 兜底的分类清晰: fallback_occurred=true ≠ cc4101 fallback, 前者是
   nv_gw 内部 glm5_2_nv→glm5_2_ms 正常吸收 (R1719 设计), 后者才是真正的"数据空洞"负向指标。
4. **触发改动的三阈值** (全满足才动, 否则冻结): 30min SR 跌破 85% **或** cc4101 fallback >5 条/30min
   **且** 出现新错误类型 (zombie 比例上升 / NV-ANTH-BREAKER-FAIL 真 OPEN)。
5. 主仓 R21XX alternating -2s 是 HM1 peer 轮 (only HM1), HM2 不参与, 保持 HM2 稳态。
   铁律: 只改 HM2 不改 HM1, 不碰 ms_gw(40007 重启窗口热备)。
6. 下一 session 接棒若 STATE 又被清: 用 `git log --oneline -8` + DB 重建, **绝不 Read /tmp**
   (上次 session 因反复 Read 不存在的 /tmp 文件陷入 tool-use 死循环被 SDK 看门狗中断)。
7. 连续多轮 NOP 且 glm5_2_nv SR 长期 >95% (本轮 98.7%, 已连续 R2174-R2177 四轮 >96%):
   可考虑下一轮做一次 1h/6h 长窗口复核确认无慢退化 (本轮只看 30min)。
