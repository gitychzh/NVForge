# R2129 (hm2_cc2): NOP R163 连续第98轮冻结 — 散布期延续但 SR 小幅回升 +2.6pp, 单点 NVAnth_IncompleteRead 新类(1条)

> 日期: 2026-07-21 CST 07:22 / UTC 23:22 拉数据
> 模式: nv 直连 (cc4101→nv_gw), 指数退避半成品仍冻结 (NVU_GLM52_EXP_BACKOFF 不在 env=关, 从未 in-vivo 激活)
> 0 改动 0 restart, 仅巡检

## 数据 (改前必有数据, 30min 窗口起点 ~22:52 UTC)

### nv_gw 30min SR
- **SR = 46/75 = 61.3%** (200:46 / 502:29)
- vs R2128 58.7% → **+2.6pp 小幅回升** (R2128 "22:58 后似回稳带" 趋势确认延续, 降幅收窄后首现回升)
- vs R2127 61.8% → -0.5pp (基本持平 R2127 次稳态带下沿)
- vs R2124 92.2% → -30.9pp (仍跌出 86-92% 次稳态带, 散布期延续)
- 由散布型 502 驱动非风暴簇

### 1min 桶轨迹 (UTC, 22:49→23:23)
- 22:49-58 散布 (bad 1-3/桶, 22:57 有 4×200 峰) → 22:59-23:09 回稳带 (23:08 桶 4×200, 23:09 桶 5×200+3×502) → 23:11-22 散布又起 (bad 1-3/桶) → 23:20-22 小波动 (23:22 桶 bad=3)
- **全程 bad≤3/桶, 无连续多桶 bad≥5 风暴簇** (对比 R2120/R2121 风暴主峰 bad 5-10/桶 连续多桶, R2126 22:35-40 bad 5-6/桶)
- 暂判散布期延续, 降幅收窄 + 首现回升是积极信号

### 502 错误分类 (29 全 NVCF 上游已知类)
- all_tiers_exhausted × 24
- zombie_empty_completion × 3
- **NVAnth_IncompleteRead × 1 (新类, 单点, 23:21:22 UTC, tier_model=glm5_2_nv, error_message 为空)**
- vs R2128 31 → 29 (-2, 散布非簇, 量略降)
- **0 新可配置类 (NVAnth_IncompleteRead 本质是 NVCF 上游 IncompleteRead 连接异常, 与 tier 的 pexec_conn_RemoteDisconnected/SSLEOFError 同族, 1 条单点不构成持续恶化)** ✅

### tier 30min 错误明细
- pexec_success × 40 (vs R2128 35 → +4)
- 500_nv_error × 6 (vs R2128 无 → 新增, NVCF 上游已知类)
- pexec_conn_RemoteDisconnected × 4 (vs R2128 2 → +2, 连接抖动略增)
- NVCFPexecRemoteDisconnected × 2 (vs R2128 1 → +1)
- pexec_SSLEOFError × 1 (vs R2128 0 → +1, 连接异常)
- **429_nv_rate_limit = 0** (持平 R2128, **第4波 429 仍滚出 30min 窗口**) ✅
- tier 层整体连接异常 (RemoteDisconnected/SSLEOFError) 略增, 但均 NVCF 上游已知类无新可配置类

### fallback + breaker + 真中断
- fallback = **6** FALLBACK-OK (vs R2128 7 → -1), 全 6 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (header/ttfb 75s < chain budget 120s, cc4101 pre-empted nv_gw retry, R1947 已知类)
- **0 条 120s 跑满类** (持平 R2128) ✅
- cc4101 `both failed|UPSTREAM-ERROR-SEEN` 30min = **0** → **0 真中断确认** ✅
- **0 fallback 失败** ✅
- nv_gw `NV-Anth-BREAKER-FAIL` 30min = **0**; cc4101 `PRIMARY-BREAKER-OPEN` 30min = **0** (state 未 OPEN, **连续第 31 轮**) ✅

### BUG-A + abs_cap
- **BUG-A 修复 (R1913) 生效**: 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次** (vs R2128 7 → -2, 持续复活触发中, 机制真实生效) ✅
- **NV-CAP-RESET-MSFB = 5 条** (vs R2128 7 → -2, R1818 bug7 cap_origin reset 机制 execute→ms_fb path 正常触发, 全被 ms_fb 兜住 0 真中断) ✅
- abs_cap 30min 正常, CAP-RESET 5 条 (持平 breaker 段)

### 健康 + StartedAt
- nv_gw /health = ok (passthrough, 5 keys, kimi_nv/dsv4p_nv/glm5_2_nv, default=dsv4p_nv)
- docker inspect StartedAt: nv_gw = **2026-07-20T18:10:28Z** (连续第 18 轮核实未漂移), cc4101 = 2026-07-19T12:10:22Z (0 restart)
- env 与 R2128 完全一致 (peer R2108 改后值: KEY_COOLDOWN=60/TIER_COOLDOWN=180/MIN_OUTBOUND=10), cc2 0 改动

## 决策: 继续 NOP (连续第98轮冻结)

### 不解冻理由 (十三轮论证)
1. **本轮问题是 NVCF 上游 all_tiers_exhausted 散布期 + 连接抖动 (RemoteDisconnected/SSLEOFError/IncompleteRead), 非软挂非429** — 指数退避链路碰不到此错误类, 延长 chain_budget 120→420 反拖 SR
2. **STATE 下一步判断线 "SR<85% 且 502出新可配类 或 fallback失败 或 breaker真OPEN" 本轮不满足**:
   - SR 61.3% < 85% ✅ 但 **SR 小幅回升 +2.6pp** (非持续恶化, 降幅收窄后首现回升)
   - 502 NVAnth_IncompleteRead×1 新类但是**单点** (1条/30min, error_message空, 非持续) + 其余全 NVCF 已知类 ✅
   - 0 真中断 + 0 fallback 失败 + breaker 未 OPEN ✅
3. 半成品未经 in-vivo 验证 (env 开关从未激活) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口, 风险/收益不对等
4. 边际收益小: abs_cap 30min 机制正常 + BUG-A 修复真实生效 (5 次) + 5 条 CAP-RESET 全被 ms_fb 兜住非恶化

### 下一轮观察重点
1. **30min SR 是否继续回升回 86-92% 次稳态带** (本轮 +2.6pp 首现回升是积极信号; 若继续回升则确认散布瞬态收尾)
2. **NVAnth_IncompleteRead 新类是否从单点 (1条) 演变为持续/风暴簇** (本轮单点 23:21, error_message空; 若下轮仍仅1-2条单点则非新可配置类, 若爆发为簇需重新评估)
3. tier 连接异常 (pexec_conn_RemoteDisconnected/SSLEOFError/500_nv_error) 是否延续或自愈
4. tier 429_nv_rate_limit 是否仍=0 (第4波仍滚出)
5. fallback 是否仍全 75s SKIP-CIRCUIT 被兜 0 失败; 120s 跑满类是否再现
6. breaker 是否仍非真 OPEN (连续第32轮); StartedAt 是否仍 18:10:28Z (连续第19轮)

## 状态变化 (cc2 视角)
- nv_gw StartedAt 仍 18:10:28Z (连续第18轮核实未漂移), env 仍 peer R2108 改后值, cc2 0 改动 0 restart
- 本轮变化: (1) **30min SR 58.7%→61.3% 小幅回升 +2.6pp** (降幅收窄后首现回升, 散布期延续但趋势积极); (2) 502 31→29 (-2 全 NVCF 已知类, 但出现 1 条 NVAnth_IncompleteRead 新类单点); (3) tier 429_nv_rate_limit=0 持平 (第4波仍滚出); (4) tier pexec_success 35→40 (+4), 500_nv_error 0→6 新增, pexec_conn_RemoteDisconnected 2→4 (+2), NVCFPexecRemoteDisconnected 1→2 (+1), pexec_SSLEOFError 0→1 (+1) 连接异常略增但均 NVCF 已知类; (5) fallback 7→6 (-1) 全 75s SKIP-CIRCUIT 被兜 0 真中断 0 失败 0 条 120s 跑满; (6) NV-CAP-RESET-MSFB 7→5 (-2) / BUG-A SKIP-PEXEC2 7→5 (-2); (7) breaker/abs_cap 全部未恶化, breaker 仍未 OPEN 连续第31轮, StartedAt 未漂移连续第18轮.

## HM2 only. 不碰 ms_gw(40007). 不碰 HM1. R2129
