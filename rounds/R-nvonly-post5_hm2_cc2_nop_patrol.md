# R-nvonly-post5 — NOP 巡检 + 恢复期持续爬升确认

**时间**: 2026-07-29 22:33 CST (HM2 cc2, 全新 session 接棒)
**改动**: 0 | **restart**: 0 | **回滚**: 不需要

## 数据 (30min / 6h 窗口)

### 30min cc2 (cc4101-primary) SR
```
 status | count
--------+-------
    200 |    58
    502 |     1
```
→ SR = 58/59 = **98.3%** (上轮 post4: 98.1%, post3: 97.9%, 持续微升单调爬升)

### 30min 错误分类 (含 caller 归属)
```
     caller     | status |       error_type        | count
----------------+--------+-------------------------+-------
 other          |    502 | all_tiers_exhausted     |     5
 unknown        |    502 | all_tiers_exhausted     |     4
 unknown        |    502 | zombie_empty_completion |     4
 cc4101-primary |    502 | buffer_exhausted        |     1   ← cc2 唯一 502
```
→ cc2 仅 1×buffer_exhausted (设计消化点, 同前轮). zombie×4 + all_tiers×9 属
   unknown/other (别的 agent, 非 cc2). 铁律: 不越权改别的 agent 路径.
   对比 post4: zombie 9→4, all_tiers 11→9 (别的 agent 侧也在好转).

### 30min tier transport 错误
```
    error_type     | count
-------------------+-------
 pexec_success     |   118
 pexec_SSLEOFError |     4
 pexec_429         |     3
```
→ transport 短惩罚机制持续工作: SSLEOF×4 + 429×3 全 pexec 内部吸收, 0 冒泡成
   cc2 502 (对比 post4 SSLEOF×4+429×3+RemoteDisconnected×1 → 本轮 RemoteDisconnected 已清零).
   118 次 pexec_success vs 共 ~118 次 tier 流量 = 平时段 1-attempt 成功率高.

### 6h cc2 SR
```
 status | count
--------+-------
    200 |   507
    502 |    40
    499 |     1
```
→ SR = 507/548 = **92.5%** (post4: 92.4%, 持平; 40×502+1×499 全 nv_gw 侧 buffer_exhausted/all_tiers 设计消化点,
   间歇期消化点随时间在 6h 尾部缓慢淡出)

### 6h fallback 铁证 (R-nvonly 核心, 应恒 0)
```
 error_type | count
------------+-------
(0 rows)
```
→ cc4101 fallback = **0** (6h 全量). **破釜沉舟 (NVU_DISABLE_MS_FALLBACK=1 +
   FALLBACK_UPSTREAM_URL=none) 持续生效**, nv_gw 纯靠 5key+5IP 自恢复无 fallback 兜底.

### 6h stream_total_deadline 频次 (deadline 链对齐铁证)
```
 hr | count
----+-------
(0 rows)
```
→ 470 墙 0 触达. deadline 链 450(buffer) < 470(cc4101) < 500(SDK idle) < 600(API)
   稳定, 长输出走 buffer_exhausted 终点, 不记 stream_total_deadline.

### 60min 时序 (恢复期斜率)
```
时段: 13:32 - 14:32 (CST 21:32-22:32)
502 分布: 13:33 / 13:40 / 13:45 / 14:09  (4 个孤立点)
14:09 之后: 14:10 - 14:32 连续 19min 全 200 零 502
```
→ 间歇期已过, 后 19min 零 502, SR 单调爬升中 (延续 post4 后 40min 零 502 趋势).

### buffer 轮转效果 (30min 实测, 5key 自恢复铁证)
```
[22:30] req=7e7b55be (input=105942c thinking=True):
  attempt=1/5 key=k2 -> EXEC-FAIL all_keys_exhausted=True (NVCF 单 key 间歇)
  -> 5s BACKOFF
  -> attempt=2/5 -> VERDICT success_text content=809c buffered=21122b
  BUFFER-SUCCESS flushed 21122b after 2 attempt(s), elapsed=26417ms  ← 救回!
[22:31] req=0eab5550: 1-attempt SUCCESS 5130ms
[22:31] req=452b0adc: 1-attempt SUCCESS 19091ms (success_tool_call)
[22:31] req=f4444d5a: 1-attempt SUCCESS 17895ms
[22:32] req=cd98bf39: 1-attempt SUCCESS 24078ms
```
→ 5key 轮转自恢复机制实战见效: req=7e7b55be attempt1 全 key 失败后,
   5s backoff + attempt2 用别 key 成功救回 21122b.
   平时段绝大多数 1-attempt SUCCESS, 5key 产能仅在 NVCF 间歇时启用.

## env 快照 (docker exec + /health 实测, 无漂移, 同 post1/2/3/4)
```
nv_gw: NVU_DISABLE_MS_FALLBACK=1 | NVU_BUFFER_CALLERS=cc4101-primary | NVU_BUFFER_MAX_RETRIES=5 |
  NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90 | NVU_BUFFER_TOTAL_DEADLINE_S=450 |
  NVU_CALLER_RETRY=0 | NVU_TIER_BUDGET_GLM5_2_NV=120 | UPSTREAM_TIMEOUT=90 |
  NVU_KEYMGR_429_BASE_COOLDOWN=120/MAX_COOLDOWN=600 | NVU_KEYMGR_CONN_BASE_COOLDOWN=30/FAIL_THRESHOLD=3/LONG_COOLDOWN=120 |
  NVU_KEYMGR_CONN_MAX_COOLDOWN=60 | NVU_EMPTY_200_FASTBREAK=3 | TIER_TIMEOUT_BUDGET_S=180/COOLDOWN_S=180 |
  KEY_COOLDOWN_S=60 | NVU_BIG_INPUT_THRESHOLD=250000 (HM1上R2422已改375000, HM2仍此值)
cc4101: FALLBACK_UPSTREAM_URL=none | CC4101_STREAM_TOTAL_DEADLINE_S=470 | PRIMARY_HEADER_TIMEOUT=400
  | UPSTREAM_TIMEOUT=130 / IDLE_TIMEOUT=150
/health: ok, nv_num_keys=5, nv_default_model=glm5_2_nv
容器: nv_gw Up 2h(RC=0, 无重启) / cc4101 Up 7h / logs_db Up 2d (本轮无 restart)
```

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 58/59 = 98.3% | ⚠<99% (1×buffer_exhausted 设计消化点) |
| cc4101 真 fallback | 0 (6h 全量) | ✓ 破釜沉舟持续生效 |
| 无新错误类型 | zombie/all_tiers 属 unknown/other(非cc2); cc2 仅 buffer_exhausted(已知消化点) | ✓ |
→ 1×502 = 设计预期 (NVCF 间歇全挂, 5key×90s 全败消化终点)
→ 改 nv_gw 配置无效 (间歇是基础设施侧 NVCF 问题) 且会撞 deadline 链 (450<470<500)
→ **冻结 NOP, 0 改动 0 restart**

## 本轮关键认知
1. **恢复期持续爬升单调确认**: 30min SR 92.4%→97.7%→97.9%→98.1%→98.3% (post2→post3→post4→post5
   跨轮单调微升). 6h SR 92.5% 持平 post4 (间歇消化点随时间在 6h 尾部缓慢淡出).
2. **buffer_exhausted 是"消化终点"非退化**: 1×502 发生在 NVCF 间歇窗口 (5key×90s 全败),
   改 nv_gw 配置无法解决 (基础设施侧问题), 贸然调参撞 deadline 链.
3. **transport 短惩罚机制持续净化**: 30min SSLEOF×4+429×3 全 pexec 内部吸收, 0 冒泡.
   对比 post4 多了的 RemoteDisconnected 本轮清零.
4. **5key 轮转自恢复实战铁证 req=7e7b55be**: attempt1 k2 全 key fail → 5s backoff →
   attempt2 SUCCESS 救回 21122b/26.4s. 平时段样本 1-attempt SUCCESS.
5. **zombie_empty_completion + all_tiers 仍属 unknown/other caller (别的 agent 非 cc2)**:
   30min 4+5+4=13 次全非 cc2, cc2 自己 0 次. 铁律: 不越权改别的 agent 路径.
   对比 post4 (9+6+5=20 次), 别的 agent 侧也在好转.
6. **stream_total_deadline 未在窗口出现**: 470 墙紧, 长输出走 buffer_exhausted, 不记 deadline.
7. **HM1 仍 R2422 (BIG_INPUT_THRESHOLD 375000 等); HM2 仍 250000/KEY_COOLDOWN_S=60**.
   **铁律: 只改 HM2, 不抄 HM1 参数.**

## 下一轮该做什么
1. 继续巡检. 盯 cc2 30min SR 是否回 100% (本轮后 19min 零 502, 很可能继续零 502).
2. 6h SR 是否随恢复期持续爬升 (当前 92.5%, 间歇消化点随时间淡出 6h 窗口).
3. 6h buffer/all_tiers 频次是否持续下降, fallback 是否恒 0.
4. transport 短惩罚是否持续在 pexec 层吸收 (SSLEOF/429 不冒泡).
5. 盯 unknown caller zombie_empty_completion 是否扩散到 cc2.
6. 长驻机制: 每30min touch ~/.claude/cc2.heartbeat (watchdog 15min); 改 .py 触发 R-guard(py_compile+restart+health); auto-compact 后从 STATE 接棒.
7. 铁律: 改前数据, 改后验证, 聚焦 40006, 不碰 40007 (NVU_DISABLE_MS_FALLBACK=1 不可改回0), 只改 HM2 (不抄 HM1 参数), 写入仓库, 尽量多走 glm5_2_nv.

## 回滚锚点 (本轮无改动, 无需回滚)
- 未改任何 gateway/*.py, 未改 compose env, 未重启容器.
- R-nvonly 配置锚点: 5key×90s/450s buffer, 470s cc4101, fallback=none, DISABLE_MS_FALLBACK=1.
- cc_s2/cc_s3 快照 (commit 5ec9c7c/d7392cf) 为 R-buffer 前, 不含 buffer_stream.py, 守护待用.

---
## 最近3轮摘要
- **R-nvonly-post5 (hm2_cc2, 本轮)**: NOP 巡检 + 恢复期持续爬升单调确认 (全新 session 接棒).
  cc2 30min 58/59→SR98.3% (1×buffer_exhausted 设计消化点);
  6h 507/548→SR92.5% (40×502+1×499 全 nv_gw 侧消化). cc4101 fb=0(6h)→破釜沉舟持续生效.
  transport 短惩罚 30min 7次 (SSLEOF×4/429×3, RemoteDisconnected 已清零) 全 pexec 内部吸收, 0 冒泡.
  5key 轮转自恢复铁证 req=7e7b55be 2-attempt (k2 fail→5s backoff→attempt2 SUCCESS 救回 21122b/26.4s).
  平时段样本 1-attempt SUCCESS. 60min 时序 502 散落 13:33/13:40/13:45/14:09, 后19min 零 502 → 间歇期已过 SR 爬升中.
  30min SR 跨轮单调: 92.4%→97.7%→97.9%→98.1%→98.3%.
  zombie×4+all_tiers×9 属 unknown/other(别的agent非cc2, 对比post4的20次在好转).
  1×502=设计消化点 (改码无效不越deadline链 450<470<500) → 冻结 NOP. 0改动0restart.
- R-nvonly-post4 (hm2_cc2): NOP 巡检 + 恢复期持续爬升确认. cc2 30min 52/53→SR98.1%
  (1×buffer_exhausted 设计消化点); 6h 499/540→SR92.4% (41×502+1×499 全 nv_gw 侧消化).
  cc4101 fb=0(6h)→破釜沉舟持续生效. transport 短惩罚 30min 8次 (SSLEOF×4/429×3/RemoteDisconnected×1)
  全 pexec 内部吸收, 0 冒泡. 5key 平时段高效 (全窗口 1-attempt SUCCESS). 60min 时序后40min 零 502
  → 间歇期已过 SR 爬升中. zombie×9+all_tiers×11 属 unknown/other(别的agent非cc2). 1×502=设计消化点
  (改码无效不越deadline链 450<470<500) → 冻结 NOP. 0改动0restart.
- R-nvonly-post3 (hm2_cc2): NOP 巡检 + 恢复期趋势确认. cc2 30min 46/47→SR97.9% (1×buffer_exhausted);
  6h 494/535+1×499→SR92.4%. cc4101 fb=0(6h). transport 短惩罚 7次全吸收. 5key 轮转自恢复见效
  (req=d6a0dabb 2-attempt 122s 救回). 30min SR(97.9%)>6h SR(92.4%) 恢复期延续. 0改动0restart.
