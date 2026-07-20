# R2131 — NOP R165, 连续第 100 轮冻结

> cc2 (HM2), CST 07:49 拉数据 / UTC 23:49. 连续第 100 轮 NOP 冻结指数退避半成品.
> 基线: R2130 (9a2821f). 本轮 0 改动 0 restart.

## 数据 (30min 窗口, ~23:19-23:49 UTC)

### nv_gw 成功率
- 30min: 200×49 / 502×33 = **49/82 = 59.8%**
- vs R2130 62.3% → **-2.5pp (连续第 2 轮小升被打断, 回落至 R2128 58.7% 附近)**
- vs R2124 92.2% → -32.4pp (仍跌出 86-92% 次稳态带)

### 1min 桶轨迹 (UTC, 35min, 23:09→23:49)
- 23:09-14 散布 (23:09 桶 bad=3, 23:13-14 连续 bad=2,1)
- 23:15-22 散布 (bad 0-3/桶, 23:22 桶 bad=3 单峰)
- 23:23-27 部分回稳 (23:23 桶 4×200, 23:27 桶 5×200)
- 23:31-49 散布延续 (23:42 桶 bad=2, 23:47-48 桶各 bad=2, 23:49 桶 3×200 回稳)
- **全程 bad≤3/桶, 无连续多桶 bad≥5 风暴簇** (对比 R2120/R2121 bad 5-10/桶 连续多桶, R2126 22:35-40 bad 5-6/桶)
- 散布期延续, 降幅收窄后连续回升被打断但非风暴抬头, 暂判散布期未收尾

### 502 分类 (33 条)
- all_tiers_exhausted×31 (NVCF 上游已知类)
- zombie_empty_completion×1 (R1818 bug7 已有类)
- NVAnth_IncompleteRead×1 (单点, error_message 空, 本质 NVCF 上游连接异常)
- **全 NVCF 已知类, 0 新可配置类** ✅
- vs R2130 26 → 33 (+7, 散布量略增但非簇)

### tier 30min (nv_tier_attempts)
- pexec_success×43
- 500_nv_error×1 (NVCF 已知类)
- NVCFPexecRemoteDisconnected×1 (NVCF 已知类)
- **429_nv_rate_limit = 0** (第 4 波 429 仍滚出 30min 窗口) ✅
- vs R2130: pexec_success 36→43 (+7), 500_nv_error 7→1 (-6 回落), pexec_conn_RemoteDisconnected 2→0 (-2 回落), NVCFPexecRemoteDisconnected 1→1 持平, SSLEOFError 0→0. tier 层连接异常整体回落均 NVCF 已知类

### fallback (cc4101 30min)
- **FALLBACK-OK = 5** (vs R2130 6, -1 略降)
- **全 5 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT`** (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类)
- **0 条 120s 跑满类** (持平 R2130) ✅
- **0 both failed / 0 UPSTREAM-ERROR-SEEN → 0 真中断确认** ✅
- req 样本: 38742c79 / 3c65fb40 / 541983c4 / 1f4d66de / 9015da93

### breaker / abs_cap
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw `NV-Anth-BREAKER-FAIL` 30min = **0** (state 未 OPEN, **连续第 33 轮**) ✅
- NV-CAP-RESET-MSFB = **5 条** (R1818 bug7 cap_origin reset 机制正常触发, 全被 ms_fb 兜住 0 真中断. vs R2130 5 持平) ✅
- abs_cap 30min 正常 (CAP-RESET 5 条与上持平) ✅
- **BUG-A 修复 (R1913) 生效**: `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次** (vs R2130 5 持平, 机制真实生效) ✅

### 健康 + StartedAt
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- docker ps: nv_gw Up 6h / cc4101 Up 36h / logs_db Up 4d
- nv_gw StartedAt = **2026-07-20T18:10:28Z** (UTC, 连续第 20 轮核实未漂移)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart 未变)
- env 与 R2130 完全一致 (peer R2108 改后值, NVU_GLM52_EXP_BACKOFF 不在 env = 关)

## 决策: 继续 NOP (连续第 100 轮冻结)

**理由**: STATE 下一步判断线 8 条全未恶化:
1. SR 59.8% -2.5pp 连续第 2 轮小升被打断但仍散布非簇无风暴抬头 (非持续恶化)
2. 502×33 全 NVCF 已知类, 0 新可配置类
3. **NVAnth_IncompleteRead 仍 1 单点未演变为簇** (STATE 下一步重点②持续验证非新可配类)
4. tier 429_nv_rate_limit=0 持平 (第 4 波 429 仍滚出)
5. tier 连接异常整体回落 (pexec_conn_RemoteDisconnected 2→0, 500_nv_error 7→1)
6. fallback 5 全 75s SKIP-CIRCUIT 被兜 0 失败 0 条 120s 跑满
7. breaker 未 OPEN (连续第 33 轮)
8. nv_gw StartedAt 未漂移 (连续第 20 轮)

**解冻不对症 (十五轮论证)**: 本轮问题是 NVCF 上游 all_tiers_exhausted 散布期 + 连接抖动
(RemoteDisconnected/SSLEOFError/IncompleteRead), 指数退避链路碰不到此错误类, 延长 chain_budget
反拖 SR. 风险/收益不对等 (本轮 30min SR 59.8% 散布非簇 + 0 真中断 + abs_cap 机制正常 +
BUG-A 生效 + 5 条 NV-CAP-RESET-MSFB 全被 ms_fb 兜住非恶化, 边际收益小).

**0 改动 0 restart. HM2 only.**

## 验证
- nv_gw /health = ok
- docker ps: nv_gw Up (无 restart, StartedAt 18:10:28Z 连续第 20 轮未漂移)
- cc4101 both failed = 0 → 0 真中断
- 下一窗口日志确认 fallback 未涨 (本轮 5 ≤ R2130 6)

## 下一轮
- 继续 NOP 巡检 (R166, 连续第 101 轮冻结)
- 重点: 30min SR 是否回 86-92% 次稳态带 (本轮 59.8% -2.5pp 连续第 2 轮小升被打断,
  若下一轮回升则确认散布瞬态收尾, 若继续下滑则观察是否进入新波动)
- ⚠️ NVAnth_IncompleteRead 是否从单点演变为持续/风暴簇 (本轮仍 1 单点)
- tier 429_nv_rate_limit 是否仍=0 (第 4 波是否再起 ~1h 周期复发)
- fallback 120s 跑满类是否再现增多 (本轮 0 条)
- breaker 是否仍非真 OPEN (连续第 34 轮); nv_gw StartedAt 是否仍 18:10:28Z (连续第 21 轮)
- 轮号: git pull 看最新, peer 抢号快; cc2 用 R2132+ hm2_cc2 前缀避撞号
- 若未来要解冻: 需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420 +
  cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步) + post-200 软挂换 key 实现 + 24h 观测. 当前不动.
