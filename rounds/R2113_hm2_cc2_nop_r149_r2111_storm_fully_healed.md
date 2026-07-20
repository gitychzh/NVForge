# R2113 (hm2_cc2): NOP R149 — 连续第 85 轮冻结, R2111 风暴完全自愈确认

> 日期: 2026-07-21 (本 session CST ~03:38)
> 模式: nv 直连 (cc4101→nv_gw), 指数退避+ms 双层方案半成品仍冻结 (NVU_GLM52_EXP_BACKOFF 不在 env)
> HM2 only, 0 改动 0 restart

## 数据 (30min 窗口, 本 session 拉取, CST ~03:35)

### nv_gw 30min 成功率 + 错误分类
- 30min SR = 103/114 = **90.4%** ✅ (vs R2112 拉时 30min 70.4% +20pp; R2111 风暴已完全滚出 30min 大窗, 稳态恢复)
- 200=103 / 502=11 (vs R2112 502=38 -27 大幅回落)
- 502 分类: all_tiers_exhausted×10 + zombie_empty_completion×1 (全 NVCF 上游已知类, 0 新可配置类; vs R2112 all_tiers×37+zombie×4)

### 小窗确认 (排除风暴尾部污染)
- 15min SR = 50/57 = 87.7% (含 19:20/19:25/19:30 每桶 1-2 个 502 残留; vs R2112 15min 90.6%, 区间内波动)

### 502 5min 桶分布 (近 40min)
- 18:55 UTC (02:55 CST) 风暴尾部残留: 200×2 / 502×4
- 19:00 UTC (03:00 CST) 残留: 200×17 / 502×11 (R2111 风暴高峰尾部最后一桶)
- 19:05-19:35 UTC (03:05-03:35 CST) 明显稳态: 200 占比 85-90%, 502 每桶 1-3 个
  (19:05 16/3 / 19:10 19/1 / 19:15 18/3 / 19:20 17/1 / 19:25 20/2 / 19:30 13/2 / 19:35 14/2)

### tier 30min (R2111 恶化完全缓解)
- pexec_success×28 / NVCFPexecRemoteDisconnected×10 / pexec_conn_RemoteDisconnected×4 / 500_nv_error×1
- **429_nv_rate_limit = 0** ✅ (vs R2112 tier 429×1 → 0; NVCF 上游 429 rate limit 风暴完全平息)
- **pexec_SSLEOFError = 0** ✅ (vs R2112 SSLEOFError×3 → 0; NVCF 上游 SSL 抖动平息)
- 剩余 NVCFPexecRemoteDisconnected×10 是 NVCF 上游连接抖动 (NVCF 侧问题, 非网关旋钮可解)

### 6h (供记录, 仍含远古风暴期失真不采信)
- 6h 502=1252 / 200=385 / 429=102 (含 peer R2107 重启前远古风暴 + R2111 本轮 02:45-03:00 风暴污染, 失真不采信, 等 CST 08:10 后 6h 窗口完全滚出风暴期才采信)

### abs_cap
- 30min = 0 ✅ (连续多轮归零, R1918 方案 0 失效)
- 6h = 0 ✅ (vs R2112 记录 6h=2, 远古偶发已滚出窗口)

## 未恶化指标 (全部持平或改善)

### fallback (cc4101 30min)
- fallback = 7 FALLBACK-OK (vs R2112 6 条 +1 区间内波动; 全兜住)
- 全 7 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb timeout 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
- **0 条 120s 跑满类** (持平 R2112, b4db8071 已滚出窗口)
- req 样本: 4577a244 / 9822be90 / 49d26ff6 / 12703db4 / 0b5871ca
- cc4101 `both failed` / `UPSTREAM-ERROR-SEEN` 30min = **0** → 确认 0 真中断

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = 0
- nv_gw 30min `BREAKER-FAIL|BREAKER.*OPEN|NV-ANTH-BREAKER-FAIL` = **0**
- **state CLOSED count 仍 2 非 OPEN 切流 = 连续第 20 轮验证未恶化机制正常吸收非恶化** (符合 CLAUDE.md "recorded 但 CLOSED 是机制正常吸收, 不是恶化"; nv_breaker recorded failure 计数仍 2 未累积到 3, 仍 CLOSED)

### BUG-A 修复 (R1913) 生效确认
- 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次** (vs R2112 4 次 +1, 持续复活触发中, 机制真实生效)

## 健康与参数快照

- nv_gw /health = ok (proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=dsv4p_nv, port=40006)
- nv_gw StartedAt = **2026-07-20T18:10:28Z** (UTC, CST 02:10:28; R2107 首次记录 05:57→18:10 漂移后未再变, **连续第 6 轮核实未漂移**)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart 未变)

### env (peer R2108 改后值, cc2 不碰)
```
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=180
MIN_OUTBOUND_INTERVAL_S=10
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_BIG_INPUT_FAIL_N=1
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_TIER_BUDGET_GLM5_2_NV=120
```
(NVU_GLM52_EXP_BACKOFF 不在 env 中 = 关, 半成品冻结中. chain_budget 仍 120s 未升 420. 本轮 0 改动, env 与 R2112 完全一致. KEY60/TIER180/MIN_OUTBOUND10 是 peer R2108 改的, cc2 不碰.)

## 状态变化 (cc2 视角)

无 (cc2 0 改动 0 restart). 本轮需记录的变化:
1. **R2111 风暴完全自愈确认** — 30min SR 70.4%→90.4% (+20pp, 风暴完全滚出 30min 大窗); 502 38→11 (−27); tier 429_nv_rate_limit 1→0 + SSLEOFError 3→0 (NVCF 上游 429/SSL 风暴完全平息).
2. nv_gw StartedAt 仍 18:10:28Z (连续第 6 轮核实未漂移), env 仍 peer R2108 改后值.
3. abs_cap 6h 2→0 (远古偶发已滚出窗口).
4. fallback 6→7 (区间内波动, 全兜住 0 真中断 0 失败 0 条 120s 跑满 持平).
5. breaker/BUG-A 全部未恶化持平 (breaker recorded 0 连续第 20 轮; BUG-A 4→5 持续触发).

## 冻结理由 (连续第 85 轮) 仍成立

半成品未经 in-vivo 验证 (env 开关从未激活, NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等 (当前 30min SR 90.4% 0 真中断, abs_cap 30min/6h 双归零, BUG-A 修复真实生效, 边际收益小; R2111 瞬态风暴已完全自愈, 非逻辑缺陷). tier 剩余 NVCFPexecRemoteDisconnected×10 是 NVCF 上游连接抖动, 延长 chain_budget 反而拖 SR, 解冻不对症.

## 下一轮建议

- 继续NOP 巡检 (R150, 连续第 86 轮冻结): 数据全部满足稳态.
- 拉数据确认持续稳态: 重点看 30min SR 是否回到 94-96% 稳态区间 (当前 90.4% 仍在上行恢复, 6h 窗口需 CST 08:10 后完全滚出风暴期才采信).
- 关注 tier NVCFPexecRemoteDisconnected 是否持续 (本轮 10, NVCF 上游连接抖动): 若上浮到 502 (tier 上浮探测 >0 rows) 且 30min SR 持续 <90% (非风暴污染) 才考虑动.
- 关注 120s 跑满类 fallback 是否再现增多 (本轮 0 条): 若持续增多逼近 fallback 失败才考虑动 chain_budget; 当前 0 条不需动.
- nv_gw 30min BREAKER-FAIL recorded 本轮 0 (连续第 20 轮): 下一轮重点看仍 0 (偏好) 或新 NV-ANTH-BREAKER-FAIL 累积到 OPEN 阈值真切流才算恶化.
- 关注 nv_gw StartedAt 是否再次漂移 (本轮 18:10:28Z 连续第 6 轮核实稳定).
- 关注 peer 是否又改 env (本轮 peer R2108 改后值, cc2 不碰).
- 轮号: 下一轮 git pull 看最新, cc2 用 R2114 或更大 hm2_cc2 前缀避撞号.
- 若未来要解冻: 需先 in-vivo 验证 NVU_GLM52_EXP_BACKOFF (env 激活 + chain_budget 120→420 + cc4101 PRIMARY_HEADER_TIMEOUT 60→450 同步) + 实现 post-200 软挂换 key + 24h 观测. 当前不动.

HM2 only. 0 改动 0 restart.
