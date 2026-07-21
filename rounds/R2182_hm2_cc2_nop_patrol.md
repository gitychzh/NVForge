# R2182 — hm2_cc2 NOP 巡检轮

> 0 改动 0 restart. 三阈值全不满足→冻结. 但出现 **cc4101 PRIMARY-FAIL+FALLBACK-FAIL 双 timeout (没救回)** 恶化信号, 写进趋势警告盯紧。

## 基线
- 上一轮 hm2_cc2: R2180 (commit 3bcb223, R2179后首条cc4101 FALLBACK-OK瞬时救回, 0改动)
- 主仓最新: d8f496a R2078 (hm2_oc2 peer 轮, 非本域) / 028ecb1 R2181 (HM2→HM1 peer 轮, only HM1, 非本域)
- 本轮: R2182 hm2_cc2 NOP 巡检

## 数据 (HM2, 30min window, ~18:50 时点)

### nv_requests 30min
- 97 请求 / 91 OK(200) / 6 错(502) → **SR = 93.8%** (较 R2180 96.2% 降, 较 R2179 94.8% 微降, 仍在稳态带但触下沿)
- by mapped_model:
  - **glm5_2_nv 69/72 = 95.8% SR** (3错全 all_tiers_exhausted; 较 R2180 100% / R2179 98.6% 明显回落)
  - dsv4p_nv 22/25 = 88% (3错全 all_tiers_exhausted, NVCF function 上游瞬态, 非本域已知良性)
- 6 错全 NVCF 上游无害类: 6 all_tiers_exhausted (无 zombie/content_filter/timeout/conn/429 入口侧)
- glm5_2_nv 3 个 502 异常点: `tiers_tried_count=0`, duration ~240s (240119/240090/235542ms) →
  nv_gw 把所有 key 都试过(NV-GLM52-TIMEOUT mode→advance), tier budget 耗尽→all_tiers_exhausted
- fallback_occurred=true 5 条 glm5_2_nv → **全 nv_gw 内部 NV-MS-FB tier 兜底**
  (glm5_2_nv → glm5_2_ms, status=200 OK 救回, ttfb 117-185s), **非 cc4101 层 fallback**
  (fallback_actually_attempted 全 f = cc4101 层没参与甩 ms)

### cc4101 30min fallback 事件 (负向核心指标)
- **req=6cee1777** [18:18:15] FALLBACK-OK — glm5_2_nv timeout → ms_gw OK 救回 (= R2180 已记那条, 滑入本轮30min窗口)
- **req=90b853ae** [18:33:37] **PRIMARY-FAIL** (glm5_2_nv header/ttfb timeout 120s) → [18:35:37] **FALLBACK-FAIL**
  (ms_gw 也 header/ttfb timeout 120s) → **真中断, CC will retry** ← **本轮核心负事件, 没救回**
- 30min cc4101 fallback 计数 = 2 个请求 attempted (1 救回 + 1 双失败) — **<5 阈值未触发**, 但出现没救回的=恶化

### nv_gw tier_attempts 30min
- glm5_2_nv tier: 69 pexec_success + 8 pexec_conn_RemoteDisconnected + 1 pexec_SSLEOFError + 1 pexec_empty_200
  = 79 次尝试, ~87% 成功 — NVCF 上游 glm5_2_nv 有 conn/SSL 瞬态, nv_gw 内部 key 切换重试吸收大部分
- dsv4p_nv tier: 2 NVCFPexecRemoteDisconnected (dsv4p 上游不稳, 跟它 3 个 502 一致)
- **无 pexec_429** (R2179 有 4 条, 本轮 key 无 rate-limit 压力)
- 无 75s_timeout / STREAM-STALL-FAIL / big_input / FORCE-STREAM-UPGRADE 事件 → **非参数误杀**

### nv_gw NV-GLM52-TIMEOUT 事件 (mode→advance, tier 切换正常工作)
- 18:28:11 k1 timeout 7142ms / 18:28:56 k2 11104ms / 18:31:52 k3 46589ms / 18:33:37 k5 26701ms / 18:50:11 k5 8394ms
- 说明 18:28-18:50 这段 NVCF glm5_2_nv 整 tier 持续慢/超时, nv_gw 在 5 key 间切换重试

## 决策: NOP 冻结, 不改代码

STATE 三触发改动阈值全不满足:
1. 30min SR = 93.8% > 85% ✅ 仍远在阈值之上
2. cc4101 fallback = 2 个请求 (1 FALLBACK-OK + 1 PRIMARY+FALLBACK 双失败) < 5 ✅ 在阈值之下
3. 无新错误类型 (仍 all_tiers_exhausted) ✅

根因分析 (为何不该动 nv_gw 参数):
- 双 timeout 根因 = **NVCF 上游 glm5_2_nv 整 tier 真慢** (tier_attempts 8 RemoteDisconnected + 连续
  NV-GLM52-TIMEOUT mode→advance), **不是 nv_gw 参数误杀** (无 75s_timeout/STALL/big_input 事件, 参数无漂移)
- cc4101 层 120s header/ttfb timeout 是 cc4101 自己的判定 (比 nv_gw TIER_TIMEOUT_BUDGET_S=180s 短,
  cc4101 先判 nv timeout → 甩 ms) — cc4101 不是 cc2 管的 (只改 HM2 nv_gw)
- 调高 nv_gw 任何参数都不会让 NVCF 上游变快, 也不会改 cc4101 的 120s 判定
- NV-MS-FB 内部兜底链路 (glm5_2_nv→glm5_2_ms) 已正常工作 (5 条 fallback 全救回 200)
- 改了反而破坏 R2154 稳定带, 且治不了根因

## ⚠ 趋势警告 (写进 STATE 给下个 session)
R2177-R2179 cc4101 fallback=0 (连续3轮) → R2180 出现 1 条 FALLBACK-OK (救回) →
R2182 出现 PRIMARY-FAIL+FALLBACK-FAIL (没救回)。**glm5_2_nv 上游连续2轮在恶化**。
虽未触发改动阈值, 但若下一轮再出现双 timeout 或 cc4101 fallback 升到 >5/30min,
需评估(但动也治不了 NVCF 上游慢, 顶多让 nv_gw 更快放弃 glm5_2_nv 甩 ms — NV-MS-FB 已在跑)。

## 验证
0 改动 0 restart 无需验证改动。curl /health ok (nv_num_keys=5, passthrough,
nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv]) + docker ps 全栈 Up
(nv_gw Up 9h / cc4101 Up 5h / logs_db Up 4d) + 容器 RC=0 无漂移
(nv_gw SA=2026-07-21T01:44:55Z, cc4101 SA=2026-07-21T05:28:51Z, 同 R2179) +
env 关键参数与 R2179 快照逐项一致 (UPSTREAM_TIMEOUT=90/TIER_TIMEOUT_BUDGET_S=180/KEY_COOLDOWN_S=60/
TIER_COOLDOWN_S=180/NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, 无漂移)。

## commit
R2182 hm2_cc2 NOP 巡检: 0 改动 0 restart. 30min 97req/93.8% SR. glm5_2_nv 95.8%(3错ATE, 回落).
cc4101 fallback=2请求(1救回+1双timeout没救回=本轮核心负事件, 恶化趋势). 6错全上游类.
NV-MS-FB内部兜底5条全救回200. 无75s_timeout/STALL/big_input非参数误杀. 容器无漂移参数无漂移.
STATE三阈值全不满足→冻结. 根因NVCF上游glm5_2_nv整tier真慢非nv_gw参数能治.
