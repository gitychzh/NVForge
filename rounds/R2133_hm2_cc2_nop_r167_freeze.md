# R2133 (hm2_cc2) — NOP R167 连续第 102 轮冻结指数退避

> 本轮: 0 改动 0 restart. 巡检轮. CST 08:17 / UTC 00:17 拉取 30min 窗口数据 (起点 ~23:47 UTC).
> git pull 拿最新: 上轮 R2132 (ed676f9) 已闭环, 本轮取 R2133 (hm2_cc2 前缀避撞号).

## 数据 (30min nv_gw 窗口, 本 session 拉取)

- nv_gw 30min SR = 49/86 = **57.0%** (200:49 / 502:37, vs R2132 57.3% -0.3pp 持平散布期延续; vs R2124 92.2% -35.2pp 仍跌出 86-92% 次稳态带, 由散布型 all_tiers_exhausted 502 驱动非风暴簇).
- **1min 桶完整轨迹 (UTC, 30min, 23:48→00:18)**: 23:48-56 散布 (bad 1-3/桶, 23:52 桶 bad=3 单峰, 23:57 桶 4×200 回稳) → 23:57-59 连续 3 桶回稳带 (各 4×200, 23:59 桶 4×200) → 00:00 桶 bad=3 散布又起 → 00:01 桶 4×200 回稳 → 00:02-12 散布延续 (bad 1-3/桶, 00:03/05/09/11 桶 bad 多于 ok) → 00:14-16 小回稳 (00:15 桶 4×200) → 00:17 桶 4×200 回稳 → 00:18 桶 1×200 收尾. **全程 bad≤3/桶, 无连续多桶 bad≥5 风暴簇** (对比 R2120/R2121 风暴主峰 bad 5-10/桶, R2126 22:35-40 bad 5-6/桶). 暂判散布期延续, 仍散布非簇.
- 30min 502=37 全 **all_tiers_exhausted×37** (全 NVCF 上游已知类, **0 zombie_empty_completion, 0 NVAnth_IncompleteRead** — R2131/R2132 的 NVAnth 单点本轮消失, 持续确认非新可配置类) ✅. vs R2132 38 → 37 (-1, 散布非簇, 量持平略降). 0 新可配类.
- tier 30min: pexec_success×45 + pexec_conn_RemoteDisconnected×5. **429_nv_rate_limit = 0** (vs R2132 0 持平, **第4波 429 仍滚出 30min 窗口**) ✅. vs R2132: pexec_success 46→45 (-1), pexec_conn_RemoteDisconnected 2→5 (+3 低位抬头), **0 500_nv_error (R2132=0 持平清零), 0 SSLEOFError, 0 NVCFPexecRemoteDisconnected, 0 NVAnth** — tier 层连接异常整体低位均 NVCF 上游已知类无新可配置类.
- **⚠️ NV-CAP-RESET-MSFB = 5 条** (R1818 bug7 已有 cap_origin reset 机制 execute→ms_fb path **正常触发**, 全被 ms_fb 兜住 0 真中断. vs R2132 4 → 5 +1) ✅.
- fallback **8** FALLBACK-OK (0 真中断, 0 fallback 失败): 全 8 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类). **0 条 120s 跑满类** (持平 R2132) ✅. req 样本: 3ba3bcbf / 50903c35 / e08e7c6a / adbb9cc3 / 84cf69d7 等. R2132 fallback 5 → 本轮 8 (+3, 散布期 75s ttfb timeout 增多驱动, 全被兜). cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认.
- breaker cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw 30min `grep -cE "NV-Anth-BREAKER-FAIL"` = **0** (state 未 OPEN, 连续第 35 轮) ✅.
- **BUG-A 修复 (R1913) 生效确认**: 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次** (vs R2132 4 → 5 +1, 持续复活触发中, 机制真实生效) ✅.
- **abs_cap 30min 正常** (CAP-RESET 5 条, 与 NV-CAP-RESET-MSFB 段持平) ✅.
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv). docker inspect StartedAt 核实 nv_gw=18:10:28Z (R2107 后未再漂移, 连续第 22 轮核实 18:10 稳定) / cc4101=12:10:22Z (0 restart 未变).

## 状态变化 (cc2 视角)

无 (cc2 视角). nv_gw StartedAt 仍 18:10:28Z (连续第 22 轮核实未漂移), env 仍 peer R2108 改后值 (KEY60/TIER180/MIN_OUTBOUND10), cc2 0 改动 0 restart. 本轮需记录的变化: (1) **30min SR 57.3%→57.0% 持平散布期延续** (-0.3pp, 仍跌出 86-92% 次稳态带, 散布型 502 延续非风暴簇); (2) 502 38→37 (-1 全 all_tiers_exhausted NVCF 已知类, **0 zombie 0 NVAnth_IncompleteRead — NVAnth 单点本轮消失持续确认非新可配类**); (3) tier 429_nv_rate_limit=0 持平 (第4波 429 仍滚出); (4) tier pexec_success 46→45 (-1), pexec_conn_RemoteDisconnected 2→5 (+3 低位抬头), 0 500_nv_error/0 SSLEOFError/0 NVCFPexecRemoteDisconnected/0 NVAnth 连接异常整体低位均 NVCF 已知类; (5) fallback 5→8 (+3 全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满); (6) NV-CAP-RESET-MSFB 4→5 / BUG-A SKIP-PEXEC2 4→5 同步 +1; (7) breaker/abs_cap 全部未恶化, breaker 仍未 OPEN 连续第 35 轮, StartedAt 未漂移连续第 22 轮.

## 结论: 继续 NOP 冻结 (R167, 连续第 102 轮)

**STATE 下一步判断线 8 条全未恶化**:
1. SR 连续回落但散布非簇 (全 bad≤3/桶无连续多桶 bad≥5 风暴簇) — 未恶化.
2. 502=37 全 all_tiers_exhausted NVCF 已知类 0 新可配类 (NVAnth 单点本轮消失持续确认非新可配类) — 未恶化.
3. tier 429_nv_rate_limit=0 持平 (第4波 429 仍滚出) — 未恶化.
4. tier 连接异常整体低位均 NVCF 已知类 (pexec_conn_RemoteDisconnected +3 低位抬头但无新可配置类) — 未恶化.
5. fallback 8 全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满 — 未恶化.
6. NV-CAP-RESET-MSFB 5 全被 ms_fb 兜住 0 真中断 — 未恶化.
7. BUG-A SKIP-PEXEC2 5 持续复活生效 — 未恶化.
8. breaker 仍未 OPEN 连续第 35 轮, StartedAt 仍 18:10:28Z 连续第 22 轮 — 未恶化.

**解冻不对症 (第 17 轮论证)**: 本轮问题是 NVCF 上游连接抖动散布期 (all_tiers_exhausted / pexec_conn_RemoteDisconnected), 指数退避链路 (per-key 60/120/240 + chain_budget 420) 碰不到此错误类 — 这些是 NVCF 上游瞬态连接断开, 不是 429 rate limit 也不是 mid-stream 软挂. 延长 chain_budget 反拖 SR (75s ttfb timeout 的请求本来就该 fallback, 而不是让它跑到 420s). 风险/收益不对等, 继续冻结.

**用户诉求 (2026-07-19) "可以报错但不能让 cc2 中断" 仍达成**: 0 真中断, 8 条 FALLBACK-OK 全被 ms_gw 兜住, 0 fallback 失败.

## 验证

- `curl /health` = ok ✅
- `docker ps` = nv_gw Up 6h / cc4101 Up 36h / ms_gw Up 11h / logs_db Up 4d ✅
- docker inspect StartedAt: nv_gw=18:10:28Z (未漂移) / cc4101=12:10:22Z ✅
- 本轮 0 改动 0 restart, 无需 restart 后验证 (env 未变).

## 参数快照 (docker exec env, peer R2108 改后真实值, 本轮 0 改动)

KEY_COOLDOWN_S=60 / TIER_COOLDOWN_S=180 / MIN_OUTBOUND_INTERVAL_S=10 / UPSTREAM_TIMEOUT=90 / TIER_TIMEOUT_BUDGET_S=180 / NVU_BIG_INPUT_FAIL_N=1 / NVU_PEXEC_TIMEOUT_FASTBREAK=3 / NVU_EMPTY_200_FASTBREAK=3 / NVU_GLM52_EXP_BACKOFF 不在 env = 关 (半成品冻结).

HM2 only. R2133.
