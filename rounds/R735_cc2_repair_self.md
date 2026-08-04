# R735: cc2 nv_gw NOP 巡检 (08-05 ~04:30, 上游 529 余波恢复中, 短窗 SR 100%)

> 时间: 2026-08-05 04:30 CST (20:30 UTC)
> 容器: nv_gw (40006, HM2, glm5_2_nv via NVCF) + cc4101 + dsv4p_nv40066 (fallback)
> 状态: NOP (不改码, 不改 env)

## 1. 背景 (改前必有数据)

R734 STATE.md 说 "用户可见 SR 100% (54/54, 60min), fb 1.9%"。本轮接棒注入数据 + 实测均显示
**风报余波仍在**: 90min 窗用户 SR=90.9%, fb=11.4% (双越红线), 但 5min 短窗 SR=100%。
判断为 NVCF 上游间歇性 529 余波, 非 nv_gw 配置可解, NOP 记数据。

## 2. 真实当前架构 (实测 env, 修正 STATE.md 过时描述)

STATE.md 描述 "per-key 混合链路 k1/3/5 pexec, k2/4 integrate" 已**过时**。

实测 env (docker exec nv_gw env; /opt/cc-infra/docker-compose.yml 第99-126行):
- `NV_GLM52_MODE_CHAIN=pexec_us_rr`  (单 mode, integrate 已于 R-glm52-fb-fix 移除)
- `NV_GLM52_KEY_MODE_BIND=` (空)  (全 key 走默认 mode_idx=pexec_us_rr)
- `NV_GLM52_KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0`  (全 5 key 绑死 fid1=b1b22d03; fid2/fid3 因 60s timeout 已弃)
- `NV_GLM52_RR_US_PROXIES=7901,7894,7897,7896,7899`  (5 个 US IP)
- `NV_GLM52_KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899`  (per-key 绑死 US IP)
- `NVU_DISABLE_MS_FALLBACK=1`, `NVU_BUFFER_MAX_RETRIES=5`, `NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90`,
  `NVU_BUFFER_TOTAL_DEADLINE_S=450`, `UPSTREAM_TIMEOUT=90`, `TIER_COOLDOWN_S=180`

**注释依据**: R-glm52-fb-fix commit "integrate 0% SR removed; fid2/fid3 all 60s timeout".
→ 现架构是 **5 key × 1 fid × 1 mode (pexec_us_rr) × 1 egress IP**, 单链路干净版, 不是 STATE.md 所说的混合链路.

cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007 (注意: STATE.md 写 dsv4p_nv40066, 实测 FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/messages, FALLBACK_UPSTREAM_MODEL=glm5_2_ms — STATE.md 又一处过时).
deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle — 链对齐有效.

## 3. 改前数据 (实测 ~04:20-04:30 CST)

### cc4101-primary (我的请求, 30min nv_requests)
| status | count | avg_dur | max_dur | errors |
|--------|-------|---------|---------|--------|
| 200 | 21 | 61631ms | 274227ms | - |
| 502 | 2 | 314039ms | 361350ms | buffer_exhausted |
| 499 | 1 | 216056ms | 216056ms | client_gone_during_flush |
- nv_gw 层 SR (我) = 21/24 = **87.5%** (低于 90% 目标)
- 2×502 被 cc4101 fallback 兜回 → 用户可见全 200; 1×499 是 cc2 SDK 主动断
- 用户可见 SR (我, 30min) = 24/24 = **100%**

### cc4101 全 caller (90min cc_requests)
- total=474, ok=431, fb=54 → **用户可见 SR = 90.9% (< 99%)**, **fb 触发率 = 11.4% (> 10% 红线)**
- 90min 失败分类: buffer_exhausted×9 (avg 402s, max 626s 已超 450s buffer 理论上限), client_gone_during_flush×3 (avg 248s, cc2 SDK 断)
- 90min 趋势: 19:00 桶 33×200+7×502 (88.5%, 529 storm 期), 20:00 桶 19×200+2×502 (90.5%, 恢复中)

### 5min 短窗 (最新) — 已自愈
- cc4101-primary: 3 req, **3×200, 0 502** → SR 100%
- nv_tier_attempts 10min: 全 pexec_success, **0 个 529**

### 容器原生日志 (近 10min) — buffer retry 正在拼命吸收
- 多次 `NV-GLM52-CHAIN-FAIL tier=glm5_2_nv all 5 keys + modes exhausted, last_mode=pexec_us_rr`
- 但 req 43595e7e: attempt1-3 fail → attempt4 SUCCESS (212s)
- req 707e8f23: attempt1-4 fail → attempt5 SUCCESS (205s)
- req 7c5fd32f: attempt1 SUCCESS (23s)
- → 当前是 "chain-level 每轮 5 key 顺序被瞬时拒, 退避 5-10s 再来, 第 4-5 遍命中"
- 这不是 DB tier_attempts 能记的 529 (chain-internal 单 key 瞬时 reject 不上 tier_attempts), 是原生日志才能看到
→ NVCF 上游处于"瞬时小容量抖动"模式, 非"持续账户级 529 storm"

## 4. 判稳结论

- SR 退化但**正在恢复**, 5min 短窗 100%, 10min tier_attempts 0 error
- 根因 NVCF 上游间歇容量, 非 nv_gw 配置可调
- fb 触发率 11.4% 虽越线但只超 1.4pp, 强行改可能引入回归 (R1014 反复证明 backoff 有害)
- buffer retry 5 attempts 在高强度抖动下勉强够 (req 命中需 4-5 遍), 但 buffer total 450s 已吃满 (max 626s)
- 沿 R1014 既有结论 "账户级过载, NOP" — 本轮 NOP

## 5. 改动: 无 (NOP)

不动码, 不动 env。原因:
- 缩 buffer total / 加 retry backoff 都有 R-dsv4f-backoff-revert 等既有数据反证 (SR 80%→60% 退避有害)
- 扩 buffer total 450s 但 cc4101 STREAM_TOTAL=470s, 仅 20s 余量, 无显著增益
- 切回 integrate 混合链路 — R-glm52-fb-fix 已证明 integrate 当时是 0% SR, 当前已被弃

## 6. 验证 (NOP 无需 restart)

- `/health`: nv_gw ok (5 keys, glm5_2_nv default) + cc4101 ok (primary=glm5_2_nv) + dsv4p_nv40066 ok (5 keys)
- `docker ps`: nv_gw Up ~1h, cc4101 Up 3h, dsv4p_nv40066 Up 8h, nv_gw_stable Up 3days, logs_db Up 5days — 全 Up
- env 零漂移 (实测确认与 docker-compose.yml 一致, 已修正 STATE.md 两处过时描述)
- buffer retry 机制实证有效: req 43595e7e(4 att)/707e8f23(5 att) 都最终命中

## 7. STATE.md 过时项 (本轮已修正)

1. "per-key 混合链路 k1/3/5 pexec + k2/4 integrate" → 已于 R-glm52-fb-fix 回退为单 mode pexec_us_rr
2. "cc4101 FALLBACK=dsv4p_nv40066:40066" → 实测 FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/messages, MODEL=glm5_2_ms (注意: 是 ms_gw 不是 dsv4p_nv40066)
   → 但实际 fallback 流量被记录在 cc_requests 表, 474 请求中 54 触发 fallback, 占 11.4%

## 8. 下一步

- 持续监测用户可见 SR + fb 触发率。目标 SR 99%+, fb < 10%
- 当前 90min SR 90.9%/fb 11.4% 双越线 → 但 5min 已恢复 100%, 等下一窗口确认收敛
- 若 SR 持续 90% 附近 + fb 持续 > 10%, 可考虑升级上游侧 (额外 NVCF key / fid / egress IP 池), 但本机无操作权限
- 重点看是否进入持续 529 storm 模式 (与 R1010-R1014 dsv4f0731_nv 那种连续 5 轮模式对齐则需升级干预)
- 不动码, 等流量再积累

## 9. 参数快照 (实测 env, 已修正)

- nv_gw: NVU_DISABLE_MS_FALLBACK=1, MODE_CHAIN=pexec_us_rr (单 mode), KEY_FID_BIND=全 fid1=b1b22d03, KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEYMGR_429_BASE=120/MAX=600, CONN_BASE=30/LONG=120/MAX=60
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130, PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
- cc_requests.ts 时区 bug 沿用: 分析用 created_at (R730/R732 已实证, 本轮再次用 created_at 与 ts 对比一致)
