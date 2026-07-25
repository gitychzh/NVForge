# R2326 (hm2_cc2): NOP 巡检 — glm5_2_nv 429 storm 持续, NVCF 账户配额非旋钮治, 三阈值全不满足冻结

**Timestamp**: 2026-07-24 12:05 UTC (20:05 CST)
**Round type**: NOP observation (self-cycle, hm2_cc2 long-session)
**Author**: cc2 (opc2_uname, HM2)
**Container restart**: No (0 改动 0 restart)

## 1. 触发 (接棒)

长驻 session 自循环, 从 STATE R2322 接棒. cat STATE.md 后 git pull, 发现 rounds/ 已有 R2323/2324/2325 (全是 HM2→HM1 桥接轮, 作者 opc2_uname 但改的是 **HM1** compose 非 HM2). 我的 self-cycle 轮号 = R2326.

## 2. 桥接轮上下文 (HM1 侧改动, 不影响 HM2 — 铁律6)

- **R2323** (HM2→HM1): NVU_PEER_FB_SKIP_MODELS +kimi_nv. HM1 数据: kimi_nv peer-fb 0% 成功率 (24h 0/45, 同 NVCF cluster). → 跳过 peer-fb 省 60s/次.
- **R2324** (HM2→HM1): TIER_COOLDOWN_S 15→10 (HM1), 消除 KEY_COOLDOWN=10 < TIER_COOLDOWN=15 的 5s dead zone.
- **R2325** (HM2→HM1): NVU_BIG_INPUT_COOLDOWN_S 900→300 (HM1). **关键发现**: big_input_breaker 在 OPEN 期每个 7ms instant-reject 会 **re-arm cooldown** (代码级 feedback loop), COOLDOWN=900 下只要请求持续到来 breaker 永不 HALF-OPEN. 900→300 让 5min quiet 期可 probe.

**HM2 env 实测 (本机, 桥接轮未污染 — 铁律6 守住)**:
- TIER_COOLDOWN_S=180 (HM2 真理源, 非 HM1 的 10)
- NVU_BIG_INPUT_COOLDOWN_S=180 (HM2 真理源, 非 HM1 的 300, 更激进)
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv (无 kimi_nv, 与 HM1 不同)
- NVU_BIG_INPUT_FAIL_N=1 (HM2 真理源, 非 HM1 的 2)

## 3. HM2 数据采集 (12:05 UTC 拉取)

### 3.1 30min 窗口 (11:35-12:05 UTC)

| metric | value |
|---|---|
| nv_requests total | 43 |
| status 200 | 41 |
| status 502 | 2 |
| SR (cc4101 视角) | 95.3% |
| **内部 fallback (fallback_occurred=t)** | **34/43 = 79.1%** |
| error_type | stream_absolute_cap ×3 |

### 3.2 2h 窗口 (10:05-12:05 UTC)

| metric | value |
|---|---|
| total | 229 |
| ok (200) | 221 |
| SR | 96.5% |
| **fb_pct** | **207/229 = 90.4%** |
| errors | stream_absolute_cap ×16 + zombie_empty_completion ×1 |
| fallback_to | glm5_2_ms ×207 (全 {glm5_2_nv,glm5_2_ms}) |

**vs R2322 (54.4% fb) → R2326 (90.4% fb)**: storm 恶化, 但 cc4101 SR 稳 (96.5%, ms_gw 兜底好).

### 3.3 tier_attempts 2h

| error_type | count |
|---|---|
| pexec_success | 42 |
| pexec_429 | 40 |
| pexec_conn_RemoteDisconnected | 7 |
| pexec_SSLEOFError | 5 |

**glm5.2 NV 非全死**: 2h 有 42× pexec_success (24× distinct minutes, 最新 09:16/09:36/09:40 各1). NVCF 账户配额**间歇性**恢复非彻底耗尽. 但 breaker OPEN 持续 → 大多数 req 走 ms_gw.

### 3.4 429 分布 (2h, per key)

| key_idx | count |
|---|---|
| k0 | 10 |
| k1 | 2 |
| k2 | 5 |
| k3 | 8 |
| k4 | 15 |

全 5 key 都中 429 (配额限制非单 key 故障). 无 retry-after header 日志 (key cooling 模式 k1/k2/k3/k4/k5 轮中).

## 4. Breaker 行为核证 (R2325 发现的 self-rearm bug 不存在于我的 breaker)

R2325 发现 **big_input_breaker** 有 self-rearm feedback loop (OPEN 期 instant-reject 重置 cooldown). 本轮核证我的 **NVU_MS_FALLBACK breaker** (glm5.2 全 key 429 → OPEN → ms_gw) **无此 bug**:

log 实测 (OPEN 期持续来请求):
```
('OPEN', 5, 25) → ('OPEN', 5, 19) [5.5s 后] → ('OPEN', 5, 16) → ('OPEN', 5, 10) → ('OPEN', 5, 0) → HALF_OPEN probe
```
skip countdown 实时递减, 到 0 触发 HALF_OPEN probe. 无 re-arm. **breaker 工作正确**, fb 高是 NVCF 配额真实症状非 breaker 卡死.

参数: NVU_MS_FALLBACK_FAIL_THRESHOLD=5 (5min 内 5 次失败 OPEN), NVU_MS_FALLBACK_SKIP_S=30 (30s 后 HALF_OPEN probe).

## 5. 三阈值判定 → 冻结 (NOP)

| 阈值 | 条件 | 实测 | 触发 |
|---|---|---|---|
| 1 | 30min SR<85% | 95.3% | 否 |
| 2 | cc4101 real fb>5 且新错误类型 | 30min real fb=1, 无新类型 | 否 |
| 3 | 新错误类型 | 全 known (stream_absolute_cap/zombie) | 否 |

**结论**: 冻结. 429 storm = NVCF 账户配额 (间歇性, 非 gateway-tunable). breaker + ms_gw 兜底正确, cc4101 SR 96.5% 无中断. **无 config-tunable 改动能降 fb 而不引风险** (历���改大 KEY_COOLDOWN 反恶化; 降 FAIL_N=5 只影响 CLOSED→OPEN 转换延迟不影响 fb count; dsv4p 未配置为 NV-tier fallback).

## 6. 未来潜在杠杆 (需先验证数据, 非本轮改)

**候选: dsv4p_nv 作为 glm5.2 storm 期 NV-tier fallback (替代 ms_gw 直跳)**

- 现状: fallback ring 只 glm5_2_nv tier (log "ring tiers tried: ['glm5_2_nv']"). glm5.2 全 key 429 → breaker OPEN → 直跳 ms_gw. dsv4p_nv 不在 ring.
- 架构想法: glm5.2 tier 全挂时, 先试 dsv4p_nv NV tier (若有独立配额) → 仍走 NV 少 fallback. 符合 "尽量多走 NV 少 fallback".
- **前置: 验证 dsv4p_nv 配额**. 2-3h 内 0 dsv4p 流量 (无数据). R2320 STATE: dsv4p 1req/0ok 170s ATE (质量差). 需 probe 确认 dsv4p 当前是否有独立配额能 service.
- 风险: 代码改 (handlers.py tier chain), 非单 param env. 需 spec + 骨架 + R-guard (py_compile+restart+health). 非小步.
- **本轮不动**, 留作数据驱动后续轮.

## 7. 验证 (本轮 NOP, 无改动, 基线核证)

- `curl localhost:40006/health` → 200 ok, default=glm5_2_nv, nv_num_keys=5, tiers=[kimi_nv,dsv4p_nv,glm5_2_nv] ✅
- `docker ps` → nv_gw Up 3h (StartedAt 06:32:14Z RC=0), cc4101 Up 26h, ms_gw Up 2d, logs_db Up 7d ✅
- 无漂移 (env 实测 = STATE R2322 快照)
- breaker 行为正确 (countdown 递减, HALF_OPEN probe 触发)

## 8. 下一轮

1. 继续巡检. 盯 429 storm 周期: 若 storm 自愈 (pexec_success 上升, fb_pct 降), 记录恢复. 若持续 >90% fb 多窗口, 评估 dsv4p NV-tier fallback 前置 (先 probe dsv4p 配额).
2. 盯 zombie: 若连续多轮 ≥5 zombie, 推进 R2192 任务3 (cat specs/ 三文件, grep -n 核实行号).
3. dsv4p 配额 probe (数据收集, 非改码): 设计安全 curl 到 40006 测 dsv4p_nv 可用性. 若有配额 → 后续轮做 NV-tier fallback 代码改.
4. 长驻机制: 每 30min touch heartbeat; 每子任务刷 STATE; 改 .py 触发 R-guard.
5. 铁律: 改前数据, 改后验证, 聚焦 40006, 不碰 40007 (重启热备), 只改 HM2, 写入仓库, 尽量多走 glm5_2_nv 少 fallback.

## 9. R2192 三任务进度

- 任务1 (cc4101 透传 cache_control): ✅ 持续生效.
- 任务2 (nv_gw zombie body dump probe): ✅ ACTIVE, 本轮窗口仅 1 zombie (素材不足).
- 任务3 (路径B zombie 内部 key 重试): ⏳ 未动. spec+骨架在 ~/cc_ps/cc2_repair_self/specs/.

Co-Authored-By: Claude <noreply@anthropic.com>
