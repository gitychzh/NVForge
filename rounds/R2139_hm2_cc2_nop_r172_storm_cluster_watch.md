# R2139 (hm2_cc2) — NOP R172, 连续第 107 轮冻结 (风暴簇触发监控升级)

> CST 09:34 拉数据 (UTC 01:34). 窗口起点 ~01:04 UTC.
> 本轮核心: **30min SR 骤降至 30.2% (vs R2137 48.8% -18.6pp), 触发 STATE 下一步判断线
> (SR<45% 且连续多桶 bad≥5 风暴簇), 但根因 = NVCF 上游 dsv4p_nv pexec RemoteDisconnected
> 散布期恶化 (非 429/非软挂/非新可配类), 指数退避链路不碰此错误类 → 仍 NOP, 改为监控升级线
> (需连续 2-3 轮确认是否持续/收尾, 期间不动参数)**.

## 数据 (改前必有数据)

### nv_gw 30min SR + status
```
 total | ok | bad | sr_pct
-------+----+-----+--------
   106 | 32 |  74 |   30.2
```
- 200: 32, 502: 74 (vs R2137 80req/39OK=48.8%; 本轮 106req/32OK=30.2%, -18.6pp 骤降).
- vs R2124 92.2% -61.9pp (跌出 86-92% 次稳态带, **且跌出 45% 判断线**).

### nv_gw 30min error_type (status!=200)
```
       error_type        | count
-------------------------+-------
 all_tiers_exhausted     |    73
 zombie_empty_completion |     1
```
- 502=74: all_tiers_exhausted×73 + zombie_empty_completion×1 (vs R2137 41 全 NVCF 已知类).
- **0 NVAnth_IncompleteRead** (连续第 7 轮消失 R2132-2139, 持续确认非新可配类).
- **0 新可配置类** (全 NVCF 上游已知类). ✅
- error_message 样本: 全是 `All NV API tiers failed for dsv4p_nv after X.Xs` (1.2s/1.5s/1.7s 快失败 +
  24.5s/27.0s/130.3s 慢失败). **dsv4p_nv 是 default tier, 单 tier, 无 key 退避空间**.

### 1min 桶轨迹 (UTC, 40min, 00:56→01:36) — ⚠️ 风暴簇
```
 00:56 |  2 |  2 |  0   回稳
 00:57 |  6 |  3 |  3   散布又起
 00:58 |  1 |  0 |  1
 00:59 |  1 |  0 |  1
 01:00 |  3 |  2 |  1
 01:01 |  2 |  0 |  2
 01:02 |  2 |  0 |  2
 01:03 |  1 |  1 |  0   小回稳
 01:04 |  1 |  1 |  0
 01:05 |  5 |  2 |  3
 01:06 |  2 |  1 |  1
 01:07 |  3 |  1 |  2
 01:08 |  1 |  0 |  1
 01:09 |  6 |  3 |  3
 01:10 |  3 |  2 |  1
 01:11 |  1 |  1 |  0   小回稳
 01:12 |  2 |  0 |  2
 01:13 |  1 |  0 |  1
 01:14 |  2 |  1 |  1
 01:15 |  3 |  2 |  1
 01:16 |  2 |  0 |  2
 01:18 |  3 |  1 |  2
 01:19 |  4 |  2 |  2
 01:20 |  2 |  2 |  0   小回稳
 01:21 |  7 |  1 |  6   ⚠️ 风暴簇起
 01:22 |  5 |  1 |  4
 01:23 |  6 |  1 |  5   bad≥5
 01:24 |  5 |  1 |  4
 01:25 |  3 |  0 |  3
 01:26 |  4 |  1 |  3
 01:27 |  5 |  2 |  3
 01:28 |  5 |  0 |  5   bad≥5
 01:29 |  5 |  0 |  5   bad≥5
 01:30 |  4 |  1 |  3
 01:31 |  3 |  2 |  1
 01:32 |  6 |  1 |  5   bad≥5
 01:33 |  3 |  2 |  1   略回落
 01:34 |  5 |  2 |  3
 01:35 |  6 |  1 |  5   bad≥5
 01:36 |  5 |  1 |  4
 01:37 |  5 |  2 |  3   (6min 窗口补拉, 簇尾段回落迹象 bad 5→3)
 01:38 |  3 |  1 |  2
```
- **01:21-01:36 连续 15 桶 bad≥3, 其中 6 桶 bad≥5 (01:23/01:28/01:29/01:32/01:35)**
  (对比 R2120/R2121 风暴主峰 bad 5-10/桶 连续多桶; R2137 散布期全程 bad≤3/桶).
- **首次触发 STATE 下一步判断线 "连续多桶 bad≥5 风暴簇"** (前 25 轮散布期均为 bad≤3/桶无簇).
- 簇尾 01:33-01:38 略回落 (bad 5→3→2), 但未确认收尾, 仍持续监控.

### tier 30min error_type
```
 pexec_success                 | 30
 pexec_conn_RemoteDisconnected | 12
```
- **pexec_conn_RemoteDisconnected×12** (vs R2137 4, **+8 骤增**). 全是 dsv4p_nv pexec 远程连接断.
- pexec_success 32→30 (-2).
- **429_nv_rate_limit = 0** (第 4 波 429 仍滚出 30min 窗口, 持平).
- 连接异常整体高位 (vs R2137 整体低位), 均 NVCF 上游已知类无新可配类.

### fallback / breaker / BUG-A / abs_cap (30min)
- **fallback = 10 FALLBACK-OK** (vs R2137 7, **+3**). 全 75s `PRIMARY-FAIL-SKIP-CIRCUIT`
  (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit
  — R1947 已知类). **0 真中断, 0 fallback 失败**. req 样本: 515be3e9/697baa5c/d5b4f44e/55f036d4/
  0a52ea96/8243e6b9/3108f59b. **0 条 120s 跑满类**. ✅
- cc4101 `grep -cE "both failed|UPSTREAM-ERROR-SEEN"` 30min = **0** → 0 真中断确认. ✅
- **⚠️ breaker 新事件**: nv_gw 30min `grep -cE "NV-ANTH-BREAKER-FAIL"` = **1**
  (09:32:24 req=e6de7b51, err=zombie_empty_completion, state=('CLOSED',3,0)).
  **首次记录到 BREAKER-FAIL 事件** (连续第 38 轮 breaker 未 OPEN 后首现, state 仍 CLOSED,
  failure count=3 未达 OPEN 阈值). 需持续监控.
  cc4101 PRIMARY-BREAKER-OPEN 30min = 0.
- **BUG-A 修复 (R1913) 生效**: `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **4 次**
  (vs R2137 5, -1, 持续复活触发中, 机制真实生效). ✅
- **NV-CAP-RESET-MSFB = 4 条** (vs R2137 5, -1, R1818 bug7 cap_origin reset execute→ms_fb path
  正常触发, 全被 ms_fb 兜住 0 真中断). abs_cap 30min 正常 (CAP-RESET 4 条). ✅

### /health + StartedAt + env
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv).
- nv_gw StartedAt = **2026-07-20T18:10:28Z** (R2107 后未再漂移, **连续第 27 轮**核实 18:10 稳定).
- cc4101 StartedAt = 12:10:22Z (0 restart).
- env 与 R2137/R2136 完全一致 (peer R2108 改后值, 非 cc2 改). NVU_GLM52_EXP_BACKOFF 不在 env = 关,
  半成品冻结中. chain_budget 仍 120s, 未升 420.

## 拟改 / 预期

**0 改动 0 restart (NOP R172, 连续第 107 轮冻结)**.

理由:
1. **触发 STATE 下一步判断线恶性事件** (SR 30.2% < 45% **且** 连续多桶 bad≥5 风暴簇), 需升级监控.
2. **但根因 = NVCF 上游 dsv4p_nv pexec RemoteDisconnected 散布期恶化**, 指数退避链路不碰此错误类:
   - 连接断了立即重试同样断 (RemoteDisconnected 是 TCP 层, per-key 60/120/240 退避对 NVCF 端连接抖动无效).
   - default=dsv4p_nv 单 tier, 无 key 退避空间 (退避只对多 key 同 tier 内有效).
   - 延长 chain_budget 120→420 反而把请求拖死更久 (本轮已有 130.3s 跑满类, 延长只会让 SR 更低).
3. **解冻不对症 (第二十二轮论证)**: 指数退避是为 "软挂 (post-200 hang) + 429 rate limit" 设计的,
   本轮问题是 NVCF 上游连接抖动散布期恶化, 不碰此错误类.
4. **未达真中断**: 0 真中断 (cc4101 both failed=0), fallback 0 失败, ms_gw 兜住所有 10 条,
   breaker 仍未真 OPEN (state CLOSED failure=3 < 阈值). 用户诉求 "可以报错但不能让 cc2 中断" 仍达成.
5. **簇尾 01:33-01:38 已略回落** (bad 5→3→2), 可能是 NVCF 上游连接抖动瞬态, 需连续 2-3 轮确认.

## 验证清单 (本轮 0 改动, 仅记录)

- [x] /health = ok
- [x] docker ps nv_gw/cc4101/ms_gw 全 Up
- [x] nv_gw StartedAt 仍 18:10:28Z (连续第 27 轮未漂移)
- [x] env 未变 (peer R2108 改后值, NVU_GLM52_EXP_BACKOFF 仍关)
- [x] 0 真中断 (cc4101 both failed=0)
- [x] fallback 0 失败 (10/10 FALLBACK-OK)
- [x] breaker 未真 OPEN (NV-ANTH-BREAKER-FAIL×1 state CLOSED failure=3 < 阈值)
- [x] BUG-A SKIP-PEXEC2 仍触发 (4 次)
- [x] 502 全 NVCF 已知类 0 新可配类 (all_tiers_exhausted×73 + zombie×1)
- [x] NVAnth_IncompleteRead 连续第 7 轮消失 (非新可配类)

## 验证结果

本轮 0 改动, 无 restart, 无回滚需求. 数据已完整记录 (30min SR 30.2%, 风暴簇 01:21-01:36 连续 15 桶
bad≥3 含 6 桶 bad≥5, tier pexec_conn_RemoteDisconnected×12 骤增, fallback 10 全兜住 0 失败, breaker
首次记录 BREAKER-FAIL 事件 state CLOSED 未 OPEN). nv_gw StartedAt 仍 18:10:28Z 连续第 27 轮稳定.

## 结论

**监控升级线触发, 不解冻**. 本轮 SR 30.2% + 风暴簇是 NVCF 上游 dsv4p_nv pexec
RemoteDisconnected 散布期恶化 (非 429/非软挂/非新可配类), 指数退避链路不碰此错误类.
0 真中断 + fallback 0 失败 + breaker 未真 OPEN, 用户诉求仍达成. 需连续 2-3 轮确认是否持续/收尾.
若持续恶化 (连续 3 轮 SR<30% **或** breaker 真 OPEN 切流 **或** fallback 失败) 才考虑重新评估
解冻或其它干预 (如临时调 default tier 走 kimi_nv/glm5_2_nv, 但此为参数改动非指数退避解冻, 需另开
评估). 本轮不满足.

HM2 only. env 未变. 0 restart. R2139
