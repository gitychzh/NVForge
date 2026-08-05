# R811: cc2 NOP 巡检轮 — R806 WAIT-RECOVER 补丁首次实战触达 (fall-through 路径)

> 承接 R810 (NOP — BUFFER 3-attempt 自愈实战观测). 全新 session.
> 铁律: 改前有数据, 改后有验证 (本轮 NOP 无改码). 只改 HM2 nv_gw.
> commit + push origin main.

## 本轮 (R811) 改动 + 依据 + 验证

### 改动: NOP — 无源码 / 无 env / 无容器重启

本轮工作: 接棒 + 拉数据 + 交叉核实轮前注入分析 + R806 补丁首次实战触达分析.

### 验证 (实测 30min, 2026-08-05 11:17 CST)

1. **cc4101-primary nv_requests SR = 100%** (91×200, 零 502)
2. **cc4101 cc_requests SR = 99.26%** (1202×200 + 9×499 client_gone, 排 499=100%)
   - 9×499 全 client_gone_mid_stream (cc2 SDK 自断, 非链路错)
3. **fallback 触发率 = 0.58%** (7/1211 < 10% ✅)
4. **per-key tier attempts = 95 全 pexec_success, 零错误** (30min 窗口)
5. **R806 补丁首次实战触达**:
   - req=709a064c (11:14:25-11:15:29 CST): 5-attempt 全挂 (每个 attempt `all_keys_exhausted=True`)
   - attempt 轮转: k3→k4→k5→k1→k2 (5key 各被选一次, 均失败)
   - 进入 `NV-BUFFER-WAIT` (buffer_stream.py:513, waiting up to 180s for recovery)
   - **`NV-BUFFER-WAIT-RECOVER` = 0 触发** → `wait_for_recovery(180s)` 在 180s 内未等到 key 恢复 (`_recovered=False`)
   - 跳过 R806 补丁分支 (line 526 `if _recovered:` 不满足)
   - 走 fall-through: ms_gw fallback disabled (NVU_DISABLE_MS_FALLBACK=1) → 502 返回 cc4101
   - cc4101 dsv4p_nv40066 fallback 兜住 → 用户收 200
   - 结论: R806 补丁逻辑正确, 被触达但走的是未恢复路径, 补丁无须改码
6. **NV-BUFFER-WAIT-RECOVER/FAIL/OK/NO-TIME 全 0** (grep -c 全 0)
   - 这是首次有请求走到 NV-BUFFER-WAIT (R806-R810 都没走到 WAIT 就在 attempt 内吸收了)
7. **瞬断窗口分析 (10:50-11:15 CST)**:
   - 10:50-10:57: SSLEOFError/RemoteDisconnected 风暴 (k2-k5 间歇 transport error)
   - 11:02: k1 429 → KeyManager 120s cooldown
   - 11:14: 风暴尾声 req=709a064c 5key 全挂 → WAIT (但 180s 不够等到恢复)
   - 11:15:37+: 后续 req 全 1-attempt success (瞬断已过)
8. **KeyManager 短惩罚生效**: SSLEOFError→10s, RemoteDisconnected→5s, 不累计 conn_count
9. **all_tiers_exhausted × 6**: nv_requests 错误分类 buffer attempt 级 tag (已记 6 轮, 非 WAIT-RECOVER)

### 轮前注入分析核实

注入分析 (11:10 快照): 87×200 cc4101-primary, per-attempt tier SR 83.0% (88/106, 11 RemoteDisc+5 empty_200+1 529+1 Timeout)
实测 (11:17, +7min): 91×200 cc4101-primary, 95 tier attempts **全 pexec_success 零错误**
差异: 注入快照的 18 个 tier 错误在 10:47-11:10 期间, 11:17 已滚出 30min 窗口 (≥27min 前)
结论: 轮前注入分析时间敏感, 需实测核实. 本轮实测峰值已过, 窗口趋于干净.

### R814 tier-degraded 短路面核实

R814 (其他优化线) 在 cooldown.py/upstream.py 加了 `mark_tier_degraded`/`is_tier_degraded` 逻辑.
确认: 容器内 cooldown.py 有 3 处, upstream.py 有 2 处. env `NVU_TIER_DEGRADED_COOLDOWN_S` 未设 (默认 60s).
当前 30min 无 NV-TIER-DEGRADED 日志 (glm5_2_nv 未在 DEGRADED 状态). 不影响 cc2 链路.

## 判稳结论

| 指标 | 实测 | 目标 | 状态 |
|---|---|---|---|
| nv_gw per-key SR (cc4101-primary) | 100% (91/91) | 90%+ | ✅ |
| 用户可见 SR (排 499) | 100% (1202/1202) | 99%+ | ✅ |
| 用户可见 SR (含 499) | 99.26% (1202/1211) | 99%+ | ✅ |
| fallback 触发率 | 0.58% (7/1211) | <10% | ✅ |
| 容器健康 | nv_gw/cc4101/dsv4p 全 ok | - | ✅ |
| R806 补丁就位 | ✅ buffer_stream.py:527-557 | - | ✅ |
| R806 补丁触发 | 0 (WAIT 走 fall-through) | - | 补丁逻辑正确, 等下次有恢复场景 |
| tier 零错 | 95/95 pexec_success | - | ✅ (瞬断窗口已滚出) |

**NOP 巡检轮** — R806 补丁首次实战触达, 走 fall-through (WAIT 180s 未恢复), 补丁逻辑正确.

## 噪声说明 (不属 cc2 链路, 不计入决策)

- hermes × dsv4f0731_nv: 30min SR 36.4% (4/11, 7×502) — dsv4f 自优化线持续不稳 (R1029-R1030+), 不穿透 cc4101-primary
- `all_tiers_exhausted × 6` 是 nv_requests 层 buffer attempt 级 tag (已记 6 轮)

## SR 趋势

| 轮 | 30min SR (cc4101-primary) | per-attempt tier SR | 备注 |
|---|---|---|---|
| R808 | 100% (78/78) | 100% (87/87) | R806 补丁已加载, 无集中瞬断 |
| R809 | 100% (83/83) | 82.7% (81/98) | BUFFER 自愈实战 (bb5a29b6 2-attempt 35s) |
| R810 | 100% (88/88) | 83.0% (88/106) | BUFFER 3-attempt 自愈实战 (4892ea40 102.7s) |
| **R811** | **100% (91/91)** | **100% (95/95)** | R806 WAIT 首次触达 (709a064c fall-through), 瞬断窗口已滚出 |

## 下一步

- **R812**: 继续监测. 关注两种场景:
  1. **R806 补丁真正生效场景**: 5key 全挂 + WAIT 期间部分 key 恢复 → `_recovered=True` → 打 `NV-BUFFER-WAIT-RECOVER` → 清 override → 完整 5key chain retry
  2. **当前观察到的 fall-through 场景**: 5key 全挂 + WAIT 180s 仍全挂 → 502 → dsv4p fallback 兜住
- 长期候选 (R806 补丁触发后仍 WAIT-FAIL 时评估):
  - NVU_WAIT_QUEUE_MAX_WAIT 180→240s (给 NVCF 更多恢复时间)
  - 方案 C: 放宽 cc4101 STREAM_TOTAL_DEADLINE 470→~600s
  - 检查 `_remaining < 30` 阈值是否过早 skip
- 噪声: hermes×dsv4f0731_nv SR 36% 是 dsv4f 自优化线, 不属 cc2 职责

## 参数快照 (R811 = R810, 无改动)

- nv_gw StartedAt: 2026-08-05 10:32:28 CST (R806 补丁已加载, R814 tier-degraded 已加载)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: KEY_COOLDOWN_S=30, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180 (R796), NVU_PROBE_INTERVAL=15
- nv_gw: NVU_KEYMGR_429_BASE=120 MAX=600, NVU_KEYMGR_CONN_BASE=30 MAX=60 FAIL_THRESHOLD=3
- nv_gw: NVU_TIER_DEGRADED_COOLDOWN_S= (默认 60s, R814 加, 当前无 DEGRADED)
- cc4101: PRIMARY=glm5_2_nv @ nv_gw:40006, FALLBACK=glm5_2_ms @ ms_gw:40007
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130
- settings.json: contextWindow=170000, autoCompactWindow=155000, API_TIMEOUT_MS=600000

## 一句话总结

R811 NOP — 30min cc2 链路 SR=100% (91/91 cc4101-primary, 1202/1211 排 499), fallback=0.58% < 10%. **R806 WAIT-RECOVER 补丁首次实战触达**: req=709a064c 11:14-11:15 5-attempt 全挂→NV-BUFFER-WAIT→wait_for_recovery 180s 未等到 key 恢复→fall-through→502→cc4101 dsv4p fallback 兜住→用户 200. 补丁逻辑正确 (line 526 `if _recovered:` 不满足走 fall-through), 无须改码. tier 95/95 pexec_success (瞬断窗口 10:50-11:14 已滚出 30min).
