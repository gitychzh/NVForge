# R-nvonly-post6 — NOP 巡检 + 恢复期持续爬升确认

**时间**: 2026-07-29 22:39 CST (HM2 cc2, 全新 session 接棒)
**改动**: 0 | **restart**: 0 | **回滚**: 不需要

## 数据 (30min / 6h 窗口)

### 30min cc2 (cc4101-primary) SR
```
 status | count
--------+-------
    200 |    64
    502 |     1
```
→ SR = 64/65 = **98.46%** (上轮 post5: 98.3%, post4: 98.1%, post3: 97.9%, post2: 97.7% 持续单调爬升)

### 30min 错误分类 (含 caller 归属)
```
     caller     | status |     error_type      | count
----------------+--------+---------------------+-------
 other          |    502 | all_tiers_exhausted |     5
 cc4101-primary |    502 | buffer_exhausted    |     1
```
→ cc2 唯一错误 1×buffer_exhausted (NVCF 间歇全挂设计消化点, 同 post2-post5 模式)
→ other caller 5×all_tiers_exhausted 属别的 agent, **非 cc2**, 不越权

### 30min tier transport 错误
```
    error_type     | count
-------------------+-------
 pexec_success     |   130
 pexec_SSLEOFError |     7
 pexec_429         |     3
```
→ transport 短惩罚 30min 10次 (SSLEOF×7/429×3, **RemoteDisconnected 已清零**)
→ 全 pexec 内部吸收, **0 冒泡成 cc2 502** (短惩罚机制持续工作)

### 6h cc2 SR + 错误分类
```
 status | count
--------+-------
    200 |   516
    502 |    39
    499 |     1
```
→ 6h SR = 516/556 = **92.8%** (上轮 post5: 92.5%, post4: 92.4%, 微升; 间歇消化点持续淡出 6h 窗口)

### 6h fallback 铁证 (R-nvonly 核心: 应恒 0)
```
 error_type | count
------------+-------
(0 rows)
```
→ **cc4101 真 fallback = 0 (6h 全量)** → 破釜沉舟持续生效, NVU_DISABLE_MS_FALLBACK=1 / FALLBACK_UPSTREAM_URL=none 不变

### 60min 时序 (恢复期斜率)
```
13:39-14:38 (60min): 共 ~90×200 + 3×502
- 13:40, 13:45, 14:09 各 1×502 (NVCF 间歇窗口)
- 14:09 之后 (后 ~30min) 全 200, 零 502
```
→ 间歇期已过, SR 持续爬升中; 后 30min 零 502 (post5 同期后40min零502 模式延续)

### buffer 5key 轮转效果 (docker logs 30min)
```
req=ee4ee298: attempt1 k2 EXEC-FAIL (all_keys_exhausted=True) → 5s BACKOFF →
  attempt2 SUCCESS (tool_call, 4340b, 47s 整体)  ← 5key 轮转自恢复铁证
req=08f8a155: 1-attempt SUCCESS (tools, 2630b, 17s)  ← 平时段高效
req=415c357b: 1-attempt SUCCESS (text, 1180b, 11s)
req=a8b4ff58: 1-attempt SUCCESS (tools, 1765b, 22s)
req=36087566: 1-attempt SUCCESS (tools, 4638b, 29s)
```
→ 5key 平时段全 1-attempt SUCCESS; 轮转产能仅 NVCF 间歇全挂时启用 (req=ee4ee298 救回)

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 64/65 = 98.46% | ⚠<99% (1×buffer_exhausted 设计消化点) |
| cc4101 真 fallback | 0 (6h 全量) | ✓ |
| 无新错误类型 | 30min buffer_exhausted(已知)+other=all_tiers(非cc2); tier 仅 SSLEOF/429(已知 transport) | ✓ |

→ **1×502 = 设计预期** (NVCF 间歇全挂, 5key×90s 全败, 改 nv_gw 配置无法解决, 贸然调参撞 deadline 链 450<470<500)
→ **冻结 NOP, 0 改动 0 restart**

## 30min SR 跨轮单调轨迹 (恢复期持续)
post2: 97.7% → post3: 97.9% → post4: 98.1% → post5: 98.3% → **post6: 98.46%** (单调爬升, 间歇期已过)

## 健康 + env 快照 (实测, 无漂移, 同 post1-post5)
```
/health: ok, nv_num_keys=5, nv_default_model=glm5_2_nv
nv_gw: NVU_DISABLE_MS_FALLBACK=1 | NVU_BUFFER_CALLERS=cc4101-primary | NVU_BUFFER_MAX_RETRIES=5 |
  NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90 | NVU_BUFFER_TOTAL_DEADLINE_S=450 |
  NVU_KEYMGR_429_BASE_COOLDOWN=120/MAX_COOLDOWN=600 | NVU_KEYMGR_CONN_BASE_COOLDOWN=30/LONG_COOLDOWN=120 |
  NVU_KEYMGR_CONN_MAX_COOLDOWN=60 | UPSTREAM_TIMEOUT=90
cc4101: FALLBACK_UPSTREAM_URL=none | CC4101_STREAM_TOTAL_DEADLINE_S=470 | PRIMARY_HEADER_TIMEOUT=400
容器: nv_gw Up 2h / cc4101 Up 7h / logs_db Up 2d (本轮无 restart)
```

## 本轮关键认知
1. 恢复期持续爬升: 30min SR 98.46% (post5 98.3%) > 6h SR 92.8% (post5 92.5%). 60min 后30min 零 502, 间歇期已过 SR 单调爬升中.
2. buffer_exhausted 是"消化终点"非退化: 1×502 发生在 NVCF 间歇窗口 (5key×90s 全败), 改 nv_gw 配置无法解决 (基础设施侧问题), 贸然调参撞 deadline 链.
3. transport 短惩罚机制持续工作: 30min 10 次 SSLEOF/429 全 nv_gw 内部 pexec 吸收, 0 冒泡. RemoteDisconnected 已清零 (R-nvonly transport 分类改动的持续收益).
4. 5key 平时段高效: 全窗口样本 1-attempt SUCCESS, 5key 轮转产能仅在 NVCF 间歇全挂时启用 (req=ee4ee298 救回铁证).
5. zombie/all_tiers 仍属 unknown/other caller (别的 agent, 非 cc2): 30min 5×all_tiers 全非 cc2. 铁律: 不越权改别的 agent 路径.
6. stream_total_deadline 未在窗口出现: 470 墙紧, 长输出走 buffer_exhausted, 不记 deadline.
7. HM1 仍 R2422 (BIG_INPUT_THRESHOLD 375000 等); HM2 仍 250000/KEY_COOLDOWN_S=60. **铁律: 只改 HM2, 不抄 HM1 参数**.

## 下一轮该做什么
1. 继续巡检. 盯 cc2 30min SR 是否回 100% (60min 后30min 零 502, 极可能零 502)。
2. 6h SR 是否随恢复期持续爬升 (当前 92.8%, 间歇消化点随时间淡�� 6h 窗口, 跨越 13:39-14:09 间歇区后预期跳升)。
3. 6h buffer/all_tiers 频次是否持续下降, fallback 是否恒 0。
4. transport 短惩罚是否持续在 pexec 层吸收 (SSLEOF/429 不冒泡, RemoteDisconnected 是否持续清零)。
5. 盯 unknown caller all_tiers_exhausted 是否扩散到 cc2。
6. 长驻机制: 每30min touch ~/.claude/cc2.heartbeat (watchdog 15min); 改 .py 触发 R-guard(py_compile+restart+health); auto-compact 后从 STATE 接棒。
7. 铁律: 改前数据, 改后验证, 聚焦 40006, 不碰 40007 (NVU_DISABLE_MS_FALLBACK=1 不可改回0), 只改 HM2 (不抄 HM1 参数), 写入仓库, 尽量多走 glm5_2_nv。

## 回滚锚点
- 未改任何 gateway/*.py, 未改 compose env, 未重启容器. 无需回滚。
- R-nvonly 配置锚点: 5key×90s/450s buffer, 470s cc4101, fallback=none, DISABLE_MS_FALLBACK=1.
- cc_s2/cc_s3 快照 (commit 5ec9c7c/d7392cf) 为 R-buffer 前, 不含 buffer_stream.py, 守护待用。
