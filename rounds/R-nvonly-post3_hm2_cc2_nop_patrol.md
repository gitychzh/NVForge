# R-nvonly-post3 (hm2_cc2) — NOP 巡检轮

> 时间: 2026-07-29 22:55 CST (post2 22:20 起约 35min 后)
> 方向: R-nvonly (破釜沉舟, 无 ms_gw fallback)
> 动作: 0 改动 0 restart, 纯数据采集判稳

## 接棒
- 主仓 git HEAD: 仍 `42820b5 R2422` (无新 commit, 主仓稳定).
- 上轮 post2 基线: cc2 30min 42/43→SR97.7%, 6h 484/527→SR91.8%. fallback=0 持续.

## 三阈值判稳 (本轮 post3 实测)

| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 46/47 = 97.9% | ⚠<99% (1×buffer_exhausted 设计消化点) |
| cc4101 真 fallback | 0 (6h 全量) | ✓ |
| 无新错误类型 | cc2 仅 buffer_exhausted(已知); zombie×11/all_tiers×6+5 属 unknown/other(别的agent,非cc2) | ✓ |

→ 1×502 = 设计预期 (NVCF 间歇全挂改码无效不越 deadline 链) → **冻结 NOP, 0 改动 0 restart**.

## 数据 (30min 窗口, 22:55 CST)

### 30min cc2 SR (nv_requests, caller='cc4101-primary')
- 200: 46, 502: 1 → SR 97.9%
- 1×502 = buffer_exhausted (设计消化点, NVCF 上游间歇全挂)

### 30min 错误分类 (按 caller 归属)
| caller | status | error_type | count |
|--------|--------|------------|-------|
| unknown | 502 | zombie_empty_completion | 11 |
| unknown | 502 | all_tiers_exhausted | 6 |
| other | 502 | all_tiers_exhausted | 5 |
| cc4101-primary | 502 | buffer_exhausted | 1 |

- cc2 自身仅 1×buffer_exhausted (已知消化点). zombie/all_tiers 全属 unknown/other caller
  (别的 agent), 铁律: 不越权改别的 agent 路径.

### 30min tier transport 错误 (nv_tier_attempts)
- pexec_success: 104
- pexec_SSLEOFError: 5  ← transport 短惩罚机制工作 (5-10s, 不累计 conn_count)
- pexec_429: 3          ← 429 指数退避 120→600s
- pexec_conn_RemoteDisconnected: 2  ← 同上短惩罚, 不冒泡成 cc2 502

→ transport 短惩罚 7 次全在 pexec 层吸收, 0 冒泡成 cc2 502. R-nvonly 改动持续见效.

### 6h cc2 SR
- 200: 494, 502: 41, 499: 1 → SR 92.4% (494/(494+41+1))
- 41×502 全 buffer_exhausted/all_tiers (NVCF 上游间歇, 设计消化终点)

### 6h fallback 铁证 (R-nvonly 核心)
- `select error_type like 'fallback%'` → 0 rows → **cc4101 fallback 6h 恒 0, 破釜沉舟持续生效**.

### buffer 轮转效果 (30min 日志)
- 大量 1-attempt SUCCESS (多次 attempt=1/5 → BUFFER-SUCCESS, 9-39ms 区间)
- req=d6a0dabb: input=130726c thinking=True → attempt 1→2 → SUCCESS flushed 267385b after 2 attempt(s),
  elapsed=121969ms (122s). ← **5key 轮转自恢复见效**: 间歇故障靠 key 轮转救回, 不 fallback ms.

## env 快照 (docker exec 实测, 无漂移, 同 post1/post2)
```
nv_gw: NVU_DISABLE_MS_FALLBACK=1 | NVU_BUFFER_MAX_RETRIES=5 | NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90 |
  NVU_BUFFER_TOTAL_DEADLINE_S=450 | NVU_TIER_BUDGET_GLM5_2_NV=120 | UPSTREAM_TIMEOUT=90
cc4101: FALLBACK_UPSTREAM_URL=none | CC4101_STREAM_TOTAL_DEADLINE_S=470 | PRIMARY_HEADER_TIMEOUT=400
/health: ok, nv_num_keys=5, nv_default_model=glm5_2_nv
容器: nv_gw Up 2h / cc4101 Up 23h(7h) / logs_db Up 3w (本轮无 restart)
```

## 本轮关键认知
1. **60min 内 cc2 SR 从 91.8%(6h) 稳升到 97.9%(30min)**: 恢复期趋势延续 post2 判断.
   1×502 仍是设计消化点, 非退化.
2. **transport 短惩罚机制持续工作**: 30min 7 次 SSLEOF/RemoteDisconnected/429 全 pexec 内部吸收,
   0 冒泡. R-nvonly 改动 1+2 持续见效 (mark_transport_error 短惩罚不累计 conn_count).
3. **5key 轮转自恢复见效**: req=d6a0dabb 走 2 attempt 122s 救回 267385b 大输出.
   buffer 5key×90s 轮转是 cc2 当前的核心自恢复手段, 无需 fallback.
4. **fallback=0 6h 铁证**: 破釜沉舟设计在 NVCF 间歇期仍扛住, nv_gw 纯靠自身消化 41×502.
5. **zombie_empty_completion 持续属 unknown caller (别的agent)**: 30min 15(后又11)次全非 cc2,
   未扩散到 cc2. 继续盯但不越权.
6. **deadline 链顶满不可再提**: 90×5=450s buffer < 470s cc4101 < 500s SDK idle < 600s API.
   stream_total_deadline 未在窗口内出现 (470 墙紧于旧值, 长输出走 buffer_exhausted).

## 下一轮该做什么
1. 继续巡检. 盯 cc2 30min SR 是否回 100% (间歇期已过, 可能零 502).
2. 6h SR 是否随恢复期持续爬升 (当前 92.4%, 间歇消化点会随时间淡出 6h 窗口).
3. 6h buffer/all_tiers 频次是否持续下降, fallback 是否恒 0.
4. transport 短惩罚是否持续在 pexec 层吸收 (SSLEOF/RemoteDisconnected 不冒泡).
5. 盯 unknown caller zombie_empty_completion 是否扩散到 cc2.
6. 长驻: 每30min touch heartbeat; 改 .py 触发 R-guard(py_compile+restart+health); auto-compact 后从 STATE 接棒.
7. 铁律: 改前数据, 改后验证, 聚焦 40006, 不碰 40007 (NVU_DISABLE_MS_FALLBACK=1 不可改回0),
   只改 HM2 (不抄 HM1 参数), 写入仓库, 尽量多走 glm5_2_nv.

## 回滚锚点 (本轮无改动, 无需回滚)
- 未改任何 gateway/*.py, 未改 compose env, 未重启容器.
- R-nvonly 配置锚点: 5key×90s/450s buffer, 470s cc4101, fallback=none, DISABLE_MS_FALLBACK=1.

---
## 最近3轮摘要
- **R-nvonly-post3 (hm2_cc2, 本轮)**: NOP 巡检. cc2 30min 46/47→SR97.9% (1×buffer_exhausted 设计消化点);
  6h 494/535+1×499→SR92.4%. cc4101 fallback=0 (6h) → 破釜沉舟持续生效. transport 短惩罚 30min 7次
  (SSLEOF×5/429×3/RemoteDisconnected×2) 全 pexec 内部吸收, 0 冒泡. 5key 轮转自恢复见效
  (req=d6a0dabb 走2attempt 122s 救回267385b). zombie×11+all_tiers×11 属 unknown/other(别的agent非cc2).
  60min 内 30min SR(97.9%) > 6h SR(92.4%) → 恢复期趋势延续. 1×502=设计消化点(改码无效不越deadline链)
  → 冻结 NOP. 0改动0restart.
- R-nvonly-post2 (hm2_cc2): NOP 巡检 + NVCF 间歇恢复期基线. cc2 30min 42/43→SR97.7% (1×buffer_exhausted);
  6h 484/527→SR91.8% (42×502 全 nv_gw 侧消化). cc4101 fb=0(6h). transport 短惩罚 10 次全吸收.
  5key 轮转自恢复见效 (req1f968636走3attempt救回). zombie 15次属 unknown(别的agent). 间歇期09h14×502→14h1×502清零.
  0改动0restart.
- R-nvonly-post1 (hm2_cc2): R-nvonly 方向确立后首次巡检. cc2 30min 52/52→SR100%, 6h 357/406→87.9%
  (48×502 早期NVCF间歇). cc4101 fb=0. transport短惩罚+5key轮转自恢复验证. 0改动0restart.
