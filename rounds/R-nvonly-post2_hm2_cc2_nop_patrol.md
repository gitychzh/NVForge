# R-nvonly-post2 (hm2_cc2, NOP 巡检轮) — R-nvonly NVCF 间歇恢复期基线确认

**时间**: 2026-07-29 22:20 CST
**轮型**: NOP 巡检 (R-nvonly 间歇故障恢复期基线)
**改动**: 0  | **restart**: 0 | **铁律违反**: 0

## 背景: 接棒 R-nvonly-post1

STATE.md 停在旧 R-buffer-post6 / R-keyretry 时代逻辑 (ms_gw fallback 仍在), 但 CLAUDE.md 已更新为
R-nvonly 方向 (2026-07-28 确立): ms_gw fallback **彻底禁用**, 5key×90s buffer, 450s total deadline,
470s cc4101 STREAM_TOTAL_DEADLINE. 主仓 worktree 头 = R2422 (HM1 上外部监督者迭代 BIG_INPUT_THRESHOLD).

R-nvonly-post1 (2026-07-29 20:39 CST, 上一轮) 是 cc2 首次在 R-nvonly 架构下巡检, 确认:
- 30min cc2 SR 100% (52/52), cc4101 fallback=0 (6h 全量) ✓ R-nvonly 破釜沉舟生效
- transport 短惩罚机制工作, 5key 轮转自恢复见效

本轮 = 新 session 接棒, 重建基线, 盯 R-nvonly 核心目标 (nv_gw 纯自恢复 99%+ SR).

## 本轮判稳数据 (21:50-22:20 CST = 13:50-14:20 UTC, 实测)

### 30min cc2 (cc4101-primary) — 恢复期, 接近清零
```
status | count
  200  |   42
  502  |    1         → SR = 42/43 = 97.7%
```
1×502 = buffer_exhausted (NVCF 间歇 5key×90s 全挂的设计预期消化点).

### 30min 错误分类 (全 caller, 看是否有新类型)
```
error_type               | count | caller 归属
zombie_empty_completion  |   15  | **unknown** (非 cc2!)
all_tiers_exhausted      |   11  | 6×unknown + 5×other (非 cc2!)
buffer_exhausted         |    1  | **cc4101-primary** (cc2 唯一, 1 次)
```
→ **`zombie_empty_completion` 是 unknown caller (别的 agent), 非 cc2 责任**. 铁律: 不碰别的 agent 路径.
cc2 自己 30min 仅 1×buffer_exhausted, 无新错误类型 ✓.

### 30min tier transport 错误 (R-nvonly 关注: 短惩罚不累计 conn_count)
```
error_type                    | count
pexec_success                 |   100    ← 主流 NVCF 正常
pexec_429                     |     6    ← KeyManager 120s→600s 退避
pexec_SSLEOFError             |     6    ← R-nvonly 短惩罚
pexec_conn_RemoteDisconnected |     4    ← 5-10s 快速惩罚
pexec_empty_200               |     1    ← FASTBREAK=3 容忍
```
→ SSLEOF(6)+RemoteDisconnected(4)=10 transport 错误, 全 nv_gw 内部退避吸收, **0 冒泡成 cc2 502**.
R-nvonly transport 短惩罚机制持续工作 ✓.

### 6h cc4101-primary SR (含间歇期集中爆发)
```
status | count | sr_pct
 200   |   484 |   → SR = 484/527 = 91.8% (6h 累积, 含间歇期 42×502)
 502   |    42 |
 499   |     1 |   ← client_gone_during_flush (BUG-A 家族)
```
6h 502 错误分类:
```
buffer_exhausted          |  30
all_tiers_exhausted       |  12
client_gone_during_flush  |   1
```
6h buffer_exhausted + all_tiers_exhausted 时序 (按 UTC 小时, 看 NVCF 间歇期->恢复期):
```
08h=6(buffer_exh) | 09h=12(buffer_exh)+1(ATE)+1(client_gone)=14  ← 间歇期高峰
10h=2             | 11h=5             | 12h=4(buffer)+2(ATE)=6
13h=9(ATE)        ← 21h CST 集中爆发 (all_tiers 9 次, NVCF 全 5key 短窗口全挂)
14h=1(buffer_exh)  ← 近窗已清零 (1 次残余)
```
→ **间歇期高峰在 09h UTC (17h CST, 14×502) 已恢复到 14h UTC (22h CST, 1×502)**.
13h UTC 的 9×all_tiers 是一次短窗口集中爆发 (NVCF 全 5key 短时全挂), 也已在 14h 清零.

### R-nvonly 核心验证: cc4101 真 fallback = 0 (6h 全量) ✓
```
cc_requests where error_type like 'fallback%' (6h): 0 行
```
→ **破釜沉舟持续生效**: 42×502 全在 nv_gw 侧 (buffer_exhausted/all_tiers) 消化, 无 1 次走 ms_gw.
即使 5key×90s 全挂, nv_gw 返 502 给客户端, 不 fallback. R-nvonly 设计无 fallback 副作用 ✓.

### 6h tier transport 错误分类 (近 3h 分时段)
```
11hUTC: success=92 / RemoteDisconnected=6 / 429=4 / SSLEOF=2
12hUTC: success=231 / 429=8 / SSLEOF=4 / RemoteDisconnected=2
13hUTC: success=179 / 429=7 / RemoteDisconnected=4 / SSLEOF=4 / empty_200=2
14hUTC: success=69 / SSLEOF=3 / 429=2
```
→ 13h UTC (NVCF 全 5key 集中爆发窗) transport 错误 = 4+4=8, 但仍个位数, 短惩罚吸收正常.
14h UTC (近窗) 仅 5 transport 错误, 已恢复.

### buffer 5key 轮转效果 (30min 日志, 自恢复铁证)
- req=1f968636 走 **attempt 1→2→3 才 SUCCESS** (153.4s):
  - attempt1 → CHAIN-FAIL (all_keys_exhausted) → backoff 5s
  - attempt2 (k1) → EXEC-FAIL (all_keys_exhausted) → backoff 10s
  - attempt3 → SUCCESS (18293c / 281986b)
  → **5key 轮转自恢复机制见效**: 间歇 NVCF 故障靠 buffer 下一次 attempt 救回, 不 fallback ✓
- req=701ede2d / 7d5329e2 / b590dfb2 / d8969d28: 全 1 attempt SUCCESS (12-22s)
- 0 `BUFFER-EXHAUSTED` 日志在 30min 窗 (DB 记的 1×buffer_exhausted 在窗口外或刚跨边界)

### stream_total_deadline 频次 (6h)
```
6h: 0 行  ← cc_requests.stream_total_deadline = 0
```
→ 同 post1: 470 墙 (R-cc_s3 清理后) 紧于旧 580 墙, 长输出 >470s 直接 buffer_exhausted,
不走 stream_total_deadline 路径. 主失败路径 = buffer_exhausted/all_tiers. deadline 链无漂移.

## env 快照 (docker exec 实测, R-nvonly 配置确认无漂移, 同 post1)
```
nv_gw:
  NVU_DISABLE_MS_FALLBACK=1            ✓ R-nvonly 核心 (不可改回 0)
  NVU_BUFFER_CALLERS=cc4101-primary
  NVU_BUFFER_MAX_RETRIES=5             ✓ 5key
  NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90  ✓ 5×90=450s
  NVU_BUFFER_TOTAL_DEADLINE_S=450      ✓
  NVU_CALLER_RETRY=0                   ✓ (R-keyretry 已回退)
  NVU_TIER_BUDGET_GLM5_2_NV=120        ✓
  UPSTREAM_TIMEOUT=90                  ✓ < TIER_BUDGET 120
  NVU_KEYMGR_429_BASE_COOLDOWN=120 / MAX_COOLDOWN=600  ✓ R-nvonly 429 退避
  NVU_KEYMGR_CONN_BASE_COOLDOWN=30 / FAIL_THRESHOLD=3 / LONG_COOLDOWN=120
  NVU_KEYMGR_CONN_MAX_COOLDOWN=60
  NVU_EMPTY_200_FASTBREAK=3
cc4101:
  FALLBACK_UPSTREAM_URL=none          ✓ R-nvonly 核心
  CC4101_STREAM_TOTAL_DEADLINE_S=470   ✓
  PRIMARY_HEADER_TIMEOUT=400           ✓
/health: ok, nv_num_keys=5, nv_default_model=glm5_2_nv ✓
```
容器: nv_gw Up 2h, cc4101 Up 7h, logs_db Up 2d (本轮无 restart).

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 42/43 = 97.7% | ⚠ <99% (1×buffer_exhausted) |
| cc4101 真 fallback | 0 (6h 全量) | ✓ |
| 无新错误类型 | zombie_empty_completion 属 unknown caller (非 cc2); cc2 仅 buffer_exhausted (已知消化点) | ✓ |

## 判稳结论: 冻结 NOP, 0 改动 0 restart

**为什么不改 despite SR<99%:**
1. cc2 唯一失败 (1×buffer_exhausted) 是 **NVCF 间歇期 5key×90s 全挂的设计预期消化点**, 非 nv_gw 配置缺陷.
2. 改 nv_gw 配置 (加大 buffer attempt / 延长 deadline) **无法解决 NVCF 上游间歇性全挂** — 是基础设施侧问题.
3. 贸然调参会撞 deadline 链: 450s buffer < 470s cc4101 < 500s SDK idle 已顶满, 不可再提.
4. 恢复趋势明确: 09h UTC 14×502 (高峰) → 14h UTC 1×502 (清零), nv_gw 已靠 5key 轮转自恢复消化间歇期.
5. cc4101 fallback=0 = **R-nvonly 核心目标 (nv_gw 自扛无 fallback) 已达成**, 间歇期 502 是可接受的"消化终点".

→ **冻结 NOP**. R-nvonly 在稳定期达 100% (近窗 30min 接近清零), 间歇期靠 key 轮转自恢复逐步消化.
6h SR 91.8% 反映的是 09h 一次 NVCF 间歇高峰的累积, 非 nv_gw 退化.

## 关键认知 (供下轮)

1. **R-nvonly 破釜沉舟持续生效 (本轮复证)**: 6h 42×502 全 nv_gw 侧 (buffer_exhausted/all_tiers) 消化,
   cc4101 fallback=0. 不再有 fallback 兜底, 所有故障 nv_gw 自扛 ✓.
2. **zombie_empty_completion 是 unknown caller (别的 agent) 的新错误, 非 cc2**: 30min 15 次全属 unknown,
   cc2 自己 0 次. 铁律: 不越权改别的 agent 路径. (R2019/R1457/R2181 等历史 round 提及此错误类型, 是已知项)
3. **NVCF 间歇期->恢复期时序清晰**: 09h UTC 高峰 (14×502) → 14h UTC 清零 (1×502).
   nv_gw 靠 5key 轮转自恢复消化, buffer_exhausted/all_tiers 是"消化终点"非退化.
4. **transport 短惩罚机制持续工作**: 30min 10 次 transport 错误全内部吸收不冒泡成 cc2 502.
5. **5key 轮转自恢复见效 (复证)**: req=1f968636 走 3 attempt 救回, 间歇故障靠 key 轮转恢复不 fallback.
6. **deadline 链无漂移**: 470 墙持续工作, stream_total_deadline 0 次, 主失败路径=buffer_exhausted.
7. **HM1 已迭代到 R2422** (外部监督者): BIG_INPUT_THRESHOLD 250000→375000 等参数在 HM1 调.
   HM2 仍 250000 / KEY_COOLDOWN_S=60. **铁律: 只改 HM2, 不抄 HM1 参数**.

## 下一轮该做什么

1. 继续巡检. 盯 cc2 (cc4101-primary) SR 是否稳定/恢复到 99%+, buffer_exhausted 频次是否持续下降.
2. 重点盯 **R-nvonly 核心目标: nv_gw 纯自恢复 99%+ SR**:
   - 30min SR 是否回到 100% (间歇期已过)
   - 6h buffer_exhausted/all_tiers 频次是否持续清零
   - transport 短惩罚持续快速恢复
   - cc4101 fallback 持续 0
3. 若 6h SR 持续 <95% (间歇期 buffer_exhausted 不收敛) → 找根因 (是否特定 key/IP 退化, 特定输入段)
   但**不改 fallback** (R-nvonly 核心), 不越 deadline 链.
4. 盯 unknown caller 的 zombie_empty_completion (别的 agent) 是否扩散到 cc2 — 若 cc2 也出现才考虑治理.
5. 长驻机制: 每 30min touch ~/.claude/cc2.heartbeat; 改 .py 触发 R-guard (py_compile+restart+health);
   auto-compact 后从 STATE 接棒.
6. 铁律: 改前数据, 改后验证, 聚焦 40006, 不碰 40007 (NVU_DISABLE_MS_FALLBACK=1 不可改回 0),
   只改 HM2, 写入仓库, 尽量多走 glm5_2_nv.

## 回滚锚点 (本轮无改动, 无需回滚)
- 未改任何 gateway/*.py, 未改 compose env, 未重启容器.
- R-nvonly 配置锚点: 同 post1 env 快照 (5key×90s/450s/470s, fallback=none/DISABLE=1).

---
## 最近3轮摘要
- R-nvonly-post2 (hm2_cc2, 本轮): NOP 巡检 + NVCF 间歇恢复期基线. cc2 30min 42×200/1×502→SR97.7%
  (1×buffer_exhausted 设计消化点), 6h 484/527→SR91.8% (42×502 全 buffer/all_tiers +1 client_gone).
  cc4101 fallback=0 (6h) → R-nvonly 破釜沉舟持续生效. transport 短惩罚 30min 10 次全内部吸收.
  5key 轮转自恢复见效 (req=1f968636 走3attempt救回). zombie_empty_completion 15次属 unknown caller 别的agent
  (非cc2, 不越权). NVCF 间歇期->恢复期时序: 09hUTC 14×502高峰→14hUTC 1×502清零. 三阈值除SR外全满足;
  1×502=设计消化点(改码无法解决NVCF上游间歇全挂, 不越deadline链450<470<500)→冻结NOP. 0改动0restart.
- R-nvonly-post1 (hm2_cc2): R-nvonly 方向确立后首次巡检. cc2 30min 52/52→SR100%, 6h 357/406→87.9%
  (48×502全buffer_exhausted, 早期NVCF间歇期). cc4101 fallback=0→破釜沉舟生效. transport短惩罚 + 5key轮转
  自恢复验证. 0改动0restart.
- (更早 R-buffer-post6 系列为旧 fallback 时代, R-nvonly 确立前的逻辑, 已被 CLAUDE.md R-nvonly 方向取代)
