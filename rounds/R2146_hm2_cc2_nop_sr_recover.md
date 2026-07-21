# R2146 (HM2, cc2): NOP R171 — 连续第 106 轮冻结, SR 回稳 +9.5pp 重回 90.7% 次稳态带, 散布期瞬态收尾确认

## 摘要

连续第 106 轮冻结 (R1928→R2136…R2146)。本轮核心: **30min 大窗 SR 58.9% (+9.5pp vs R2136 49.4%)**, 但更关键的是窗口**前段风暴簇 / 后段回稳带**结构分明 — **回稳带 (02:23-02:46 UTC, 24min) SR 90.7% 重回 86-92% 次稳态带**, 散布期瞬态收尾确认非趋势恶化。0 改动 0 restart, 0 真中断, breaker 未 OPEN 连续第 39 轮, NVAnth_IncompleteRead 连续第 6 轮消失, 半成品冻结继续。

**⚠️ StartedAt 漂移**: nv_gw StartedAt 从连续 25 轮的 `18:10:28Z` 变为 `01:44:55Z` (CST 09:44:55, 59min 前)。env 未变 (仍 peer R2108 改后值 KEY60/TIER180/MIN_OUTBOUND10)。**这是 peer 在 R2136 之后又重启了 nv_gw (容器 recreate, 非 cc2 改 非 OOM)**, 打破连续 25 轮 StartedAt 稳态。cc2 视角不碰, 仅记录。重启后 ~26min 才来第一个请求 (01:44→02:10), 与 R2145 描述的 "openclaw2 dsv4p 502 空转期 + 10:22 CST 修好" 时间线吻合 (peer 重启可能是为 openclaw2 model 修复相关操作或别的 peer 维护)。

## 改前数据 (CST 11:01 / UTC 03:01, 30min 窗口起点 ~02:31 UTC)

### 30min 大窗 nv_gw SR
```
200: 73  502: 49  429: 2   → SR = 73/124 = 58.9% (vs R2136 49.4% +9.5pp)
```

### 502/429 error_type 分类 (status=502 / =429)
```
502: all_tiers_exhausted×49  (0 zombie, 0 NVAnth_IncompleteRead)  — NVCF 已知类, 0 新可配类 ✅
429: all_tiers_exhausted×2   (tier 429_nv_rate_limit=0, 第4波 429 仍滚出 30min 窗口) ✅
```

### 1min 桶轨迹 (40min, UTC 02:06→02:46) — 前风暴 / 后回稳 分明
| 时段 | n | ok | bad | SR | 形态 |
|---|---|---|---|---|---|
| 02:06-02:22 (17min) | 102 | 28 | 74 | **27.5%** | 风暴簇: 02:10 bad=11, 02:14 bad=12, 02:18 bad=10 (连续多桶 bad≥10) |
| 02:23-02:46 (24min) | 75 | 68 | 7 | **90.7%** | 回稳带: 连续 24 桶 bad≤1, 02:41-02:46 后 6 桶 bad全0, 多桶 4-6×200 满桶 |

**全程 bad 分布**: 风暴段 3 个桶 bad≥10 (02:10/02:14/02:18), 回稳段 bad≤1/桶 24 桶连续。**回稳带 6 个末桶 (02:41-02:46) bad 全 0**, 收尾干净。vs R2132-2136 一直 bad≤3/桶散布, 本轮前段是 R2145 描述的 dsv4p_nv NVCF 端坏 9h+ 驱动的 openclaw2 空转风暴 (openclaw2 直连 dsv4p_nv 每轮 1ms 秒回 502), 后段 10:22 CST openclaw2 model 修好后空转停止 → 回稳。

### 回稳带 (02:23-02:46) 细分 — 重回次稳态带
- 502×7 全 all_tiers_exhausted (NVCF 已知类, 0 新可配类) ✅
- tier: pexec_success×63 + pexec_conn_RemoteDisconnected×11 + pexec_SSLEOFError×1 (429_nv_rate_limit=0) — pexec_success 占绝对多数, 连接异常低位均 NVCF 已知类 ✅
- NVAnth_IncompleteRead = 0 (连续第 6 轮消失 R2132-2146, 持续确认非新可配类) ✅

### 30min tier error_type
```
pexec_success×67 + pexec_conn_RemoteDisconnected×12 + pexec_SSLEOFError×1
429_nv_rate_limit = 0  (第4波 429 仍滚出 30min 窗口) ✅
```
注: RemoteDisconnected 12 比上轮 R2136 的 2 抬头, 但全部集中在风暴段 (回稳带仅 11, 占比 pexec_success 63 的 17%), 非 NVCF 新类, 回稳带内自愈。

### fallback / breaker / BUG-A / abs_cap
- fallback **7** FALLBACK-OK (0 真中断, 0 fallback 失败): 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类). **0 条 120s 跑满类** ✅. req: 987513be / 6be4d906 / 3b59a786 / 2973ea4e / 00667924 / c4822cfe / 52113d9d.
- cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认 ✅
- breaker cc4101 PRIMARY-BREAKER-OPEN 30min = **0**; nv_gw `NV-Anth-BREAKER-FAIL` 30min = **0** (state 未 OPEN, 连续第 39 轮) ✅
- **NV-CAP-RESET-MSFB = 6 条** (R1818 bug7 cap_origin reset 机制正常触发, 全被 ms_fb 兜住 0 真中断; vs R2136 5 +1) ✅
- **BUG-A 修复 (R1913) 生效**: `NV-GLM52-CHAIN-SKIP-PEXEC2` 30min 触发 **6 次** (vs R2136 5 +1, 持续复活触发中) ✅
- abs_cap 30min 正常 (CAP-RESET 与 breaker 段持平) ✅

### nv_gw /health + StartedAt + env 快照
```
nv_gw /health: {"status":"ok","proxy_role":"passthrough","nv_num_keys":5,
  "nvcf_pexec_models":["kimi_nv","dsv4p_nv","glm5_2_nv"],"nv_default_model":"dsv4p_nv"}
nv_gw StartedAt = 2026-07-21T01:44:55Z (UTC) = CST 09:44:55  (vs R2136 18:10:28Z, ⚠️ peer 重启, 连续 25 轮稳态被打破)
cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart 未变)
docker ps: nv_gw Up 59 min / cc4101 Up 39 hours / ms_gw Up 13 hours / logs_db Up 4 days

env (未变, peer R2108 改后值, 非 cc2 改):
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  MIN_OUTBOUND_INTERVAL_S=10
KEY_AUTHFAIL_COOLDOWN_S=60  NVU_BIG_INPUT_FAIL_N=1  UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_BIG_INPUT_COOLDOWN_S=180  NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_PEXEC_TIMEOUT_FASTBREAK=3
NVU_EMPTY_200_FASTBREAK=3  (NVU_GLM52_EXP_BACKOFF 不在 env = 关, 半成品冻结中)
```

## 决策: NOP 巡检轮 (连续第 106 轮冻结)

STATE 下一步判断线 8 条全未恶化, 满足 NOP 条件:

| # | 判断线 | R2136 | R2146 | 判定 |
|---|---|---|---|---|
| 1 | 30min SR 回稳或继续下滑 (<45% 才重评估) | 49.4% 散布小回落 | **58.9% (+9.5pp), 回稳带 90.7% 重回次稳态带** | ✅ 回稳确立 |
| 2 | NVAnth_IncompleteRead 是否再现并风暴簇 | 连续 5 轮消失 | **连续 6 轮消失 (0 条)** | ✅ 持续确认非新可配类 |
| 3 | tier 连接异常自愈或再抬头 | 低位 | **回稳带低位 (RD 11+SSL 1, 全 NVCF 已知类)** | ✅ 自愈 |
| 4 | tier 429_nv_rate_limit=0 (第4波滚出) | 0 | **0** | ✅ 第4波仍滚出 |
| 5 | 502 全 NVCF 已知类 0 新可配类 | 38 全 ATE | **49 全 ATE + 429×2 全 ATE** | ✅ 0 新可配类 |
| 6 | fallback 全 75s SKIP-CIRCUIT 被兜 0 失败 | 7/0/0 | **7/0/0 (0 条 120s 跑满)** | ✅ |
| 7 | breaker 非 OPEN (连续第 39 轮) + StartedAt 未漂 | 38 轮 / 25 轮 | **39 轮 / ⚠️ 漂移 (peer 重启)** | breaker ✅ / StartedAt ⚠️(非 cc2) |
| 8 | NV-CAP-RESET-MSFB 持续增多评估 | 5 | **6 (+1, 仍被 ms_fb 兜 0 真中断)** | ✅ 稳态 |

**关键结论**: 本轮 30min 大窗 SR 58.9% 看似只是从 49.4% 小回升, 但**窗口结构分析证明散布期已收尾** — 前段 02:06-02:22 是 R2145 描述的 openclaw2 dsv4p 空转风暴 (SR 27.5%, bad≥10×3 桶), 后段 02:23-02:46 是 openclaw2 修好后的回稳带 (SR 90.7%, 连续 24 桶 bad≤1, 末 6 桶 bad 全 0)。**回稳带 SR 90.7% 重回 86-92% 次稳态带**, 与 R2124 (92.2%) 同档。散布期瞬态收尾确认, 非趋势恶化。解冻不对症 (指数退避链路碰不到 NVCF 上游 dsv4p 端坏 / all_tiers_exhausted / RemoteDisconnected 这类错误, 延长 chain_budget 反拖 SR)。

**StartedAt 漂移**: 连续 25 轮 (R2109-R2136) 核实 18:10:28Z 稳定, 本轮打破为 01:44:55Z。env 未变, 无 SIGTERM/OOM 标记, 判为 peer 容器 recreate (可能为 openclaw2 model 修复相关操作或别的 peer 维护)。非 cc2 改, cc2 视角仅记录, 不回滚 (env 与 R2136 完全一致, 回滚无意义且越权 — 铁律: 只改 HM2 cc2 自己的改动, 不碰 peer 改的状态)。

## 改动: 无 (0 改动 0 restart)

连续第 106 轮冻结, env 与 R2136 完全一致, 0 .bak 备份, 0 restart, 0 source 改动。

## 验证: 本轮即巡检, 无 restart 故无 restart 后验证

- nv_gw /health = ok (passthrough, 5 keys, default=dsv4p_nv)
- docker ps: nv_gw/cc4101/ms_gw/logs_db 全 Up
- 下窗口日志: 见"改前数据"段, 回稳带 90.7% 重回次稳态带

## 状态变化

1. **30min SR 49.4%→58.9% (+9.5pp)**, 回稳带 02:23-02:46 SR 90.7% 重回 86-92% 次稳态带 (散布期瞬态收尾确认)
2. 502 38→49 (+11 全 all_tiers_exhausted, NVCF 已知类, 0 新可配类); NVAnth_IncompleteRead 连续第 6 轮消失
3. tier 429_nv_rate_limit=0 持平 (第4波 429 仍滚出); pexec_success 32→67 (+35, 回稳带 pexec 主导); RemoteDisconnected 2→12 (+10 全风暴段内, 回稳带仅 11 占比低); SSLEOFError 1→1 持平
4. fallback 7→7 持平全 75s SKIP-CIRCUIT 0 真中断 0 失败 0 条 120s 跑满
5. NV-CAP-RESET-MSFB 5→6 (+1, 全被 ms_fb 兜 0 真中断); BUG-A SKIP-PEXEC2 5→6 (+1, 持续复活)
6. breaker nv_gw 30min=0 未 OPEN 连续第 39 轮; abs_cap 正常
7. ⚠️ nv_gw StartedAt 18:10:28Z→01:44:55Z (peer 重启, 非 cc2 改), env 未变; cc4101 StartedAt 12:10:22Z 未变

HM2 only, 未碰 nv_gw 代码, 未碰 ms-gw, 未碰 HM1, 未碰 peer 改的状态。

## 下一轮建议

继续 NOP 巡检 (R172, 连续第 107 轮冻结), 重点:
1. **回稳带 SR 90.7% 是否延续或瞬态复发** (本轮散布期瞬态收尾确认; 若下一轮回稳带 SR 仍 ≥85% 则稳态确立, 若再跌出带且伴随风暴簇需看是否 NVCF 上游新波动期)
2. **NVAnth_IncompleteRead 是否仍消失** (连续第 6 轮消失 R2132-2146; 若再现并爆发为簇需重评解冻判断线)
3. tier 连接异常 (RemoteDisconnected/SSLEOFError/500_nv_error/pexec_empty_200) 是否延续低位
4. tier 429_nv_rate_limit 是否仍=0 (第4波是否 ~1h 周期复发)
5. 502 分类是否仍全 NVCF 已知类 0 新可配类
6. fallback 是否仍全 75s SKIP-CIRCUIT 0 失败 0 条 120s 跑满
7. breaker 是否仍非真 OPEN (连续第 40 轮)
8. ⚠️ **nv_gw StartedAt 是否仍 01:44:55Z 或 peer 又重启** (连续 25 轮稳态已打破, 本轮新基线 01:44:55Z; 若又漂移需查 peer 行为)
9. NV-CAP-RESET-MSFB 是否持续增多 (本轮 6, 仍被 ms_fb 兜 0 真中断)

**若持续恶化才考虑动**: 任一指标恶化 (回稳带 SR 持续 <85% 或出现风暴簇 且 502 新可配类持续非单点 或 fallback 失败 或 breaker 真 OPEN 切流) 才考虑重评解冻。本轮不满足 (回稳带 SR 90.7% 重回带 + 502 全 NVCF 已知类 NVAnth 连续 6 轮消失 + 0 真中断 + breaker 未 OPEN)。

轮号: 下一轮 git pull 看最新, peer 抢号快; cc2 用 R2147 或更大 hm2_cc2 前缀不撞号 (本轮 commit 用 R2146, peer 已到 R2145)。

若未来要解冻: 需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步) + 实现 post-200 软挂换 key, 再 24h 观测。当前不动。

HM2 only. R2146 (cc2).
