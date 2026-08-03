# R591: NOP 巡检轮 (cc2 0 流量, dsv4p_nv 9req 4×200+5×429 SR=44.4% NVCF 配额型)

## TL;DR
继续 NOP 巡检。cc2 0 流量（cc4101-primary 30min 0 req），dsv4p_nv 9req 4×200+5×429 SR=44.4%，
vs R590 37.5% (3/8) 略升，仍在 6h 波动区间 20-55% 内。命中 key2/key3 时 100% 200 (key2 avg_dur 10675ms,
key3 avg_dur 3274ms)，全挂时空 key 429 = NVCF 配额型波动，非 nv_gw tier 故障。KeyManager 429
cooldown/decay/reset 按设计工作。无新错误类型，无参数漂移。铁律1 cc2 视角不满足 → 不动码。

## 一、轮前链路分析 (2026-08-03 11:08:32 CST 注入)

### 1.1 30min cc2 (cc4101-primary) — 0 req
session 间歇空闲，无 cc2 评估样本。铁律1 不满足。

### 1.2 30min dsv4p_nv — 9 req, SR=44.4%
| 维度 | 值 |
|------|----|
| 总量 | 9 req (4×200 + 5×429) |
| SR | 44.4% |
| 唯一错误 | all_tiers_exhausted ×5 (avg_dur 1394ms) |
| per-key | key2: 3×200 (avg_dur 10675ms) ; key3: 1×200 (avg_dur 3274ms) ; 空 key: 5×429 |
| per-egress-IP | 203.10.96.139: 3×200 (100%) ; 134.195.101.194: 1×200 (100%) ; 空 IP: 5×0 |
| 200 延迟 | avg_dur=8825ms, max=13463ms, min=3274ms, avg_ttfb=8390ms |
| finish_reason | stop×2 + tool_calls×2 (健康, 无 zombie) |
| fallback 发生率 | f×9 (cc4101 层 ms_gw 兜底, 预期) |
| buffer/wait 日志 | 无 (30min 无 buffer 触发) |

### 1.3 30min 按分钟趋势
```
02:41|429|1
02:46|429|1
02:51|429|1
02:56|200|3   ← 命中可用 key 时连续 200
03:01|429|1
03:05|200|1
03:06|429|1
```
→ 5min 间隔单次 429 + 中段连续 200 = NVCF 配额型节流模式, 非 tier 故障。

## 二、判稳

### 2.1 vs 历史轮
| 轮 | SR | 状态 |
|----|----|------|
| R591 (本) | 44.4% (4/9) | NVCF 配额波动 |
| R590 | 37.5% (3/8) | 波动区间内 |
| R589 | 37.5% (3/8) | 完全一致 |
| R588 | 37.5% (3/8) | 完全一致 |
| R587 | 37.5% (3/8) | 完全一致 |
| R586 | 37.5% (3/8) | 完全一致 |
| R585 | 37.5% (3/8) | 完全一致 |
| R584 | 71.4% | 波动区间内 |
| R583 | 71.4% | 波动区间内 |
| R582 | 58.3% | 波动区间内 |

→ SR 在 20-55% 波动区间内持续, 命中可用 key 时 100% 200 = NVCF 配额型, 非 nv_gw tier 故障。

### 2.2 KeyManager 行为
- 全挂时 `all_tiers_exhausted` (avg_dur 1394ms) = 5key 全冷却, NVCF 侧拒绝
- 命中 key2 时 100% 200 (avg_dur 10675ms), 命中 key3 时 100% 200 (avg_dur 3274ms) = key 可用即成功
- nv_tier_attempts 0 行 = KeyManager 在 tier 层前拦截, 符合设计
- 全挂时 ABORT-NO-FALLBACK = dsv4p_nv 跳 peer/ms fb (NVU_PEER_FB_SKIP_MODELS 含 dsv4p_nv), cc4101 层 ms_gw(glm5_2_ms) 兜底
- 行为完全正确, 无介入必要

### 2.3 无新错误 / 无参数漂移
- 错误类型唯一 all_tiers_exhausted (NVCF 配额型), 无新错误
- 配置与 R472-R590 完全一致, 无漂移
- 无 stream_total_deadline, 无 zombie, 无 buffer 触发

## 三、本轮改动
无 (NOP)。铁律1 cc2 视角不满足 → 不动码。

## 四、依据
- cc2 0 流量 → 无评估样本, 铁律1 不满足
- dsv4p_nv 9 req: 4×200+5×429 = NVCF 配额波动区间 (命中 key2/key3 100% 200, 全挂时空 key 429)
- 6h 趋势: SR 波动 20%-55%, 命中可用 key 时 100% 200 → 非 nv_gw tier 故障
- KeyManager 行为完全正确: 429 cooldown/count decay/reset 按设计工作
  - 全挂时 `all_tiers_exhausted` = dsv4p_nv 跳 peer/ms fb, 预期行为
- 无新错误类型, 无参数漂移 → 无介入必要
- 本轮 SR=44.4% vs R590 37.5% vs R589 37.5% vs R588 37.5% → 波动区间内, 与 R545-R590 同一 NVCF 配额波动模式

## 五、验证
- 0 restart → 无需 py_compile / curl 复测
- curl /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv, models=[kimi_nv,dsv4p_nv,glm5_2_nv]
- docker ps: nv_gw Up 21h, nv_gw_stable Up 33h, cc4101 Up 10h, ms_gw Up 4 days, logs_db Up 4 days

## 六、下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为
- 关注新错误类型或 key/IP 级故障再决定介入
- dsv4p_nv 小时级 SR <60% + cc2 流量恢复 → 评估 TIER_COOLDOWN_S 180s 是否过激
- all_tiers_exhausted 中段不恢复再评估 (当前 ~10/h 全 NVCF 配额型)
- 502 (peer-fb-skip) >=6/h + cc2 流量恢复 → 评估 dsv4p_nv fallback 策略

## 七、参数快照 (R590 未改)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_MS_FALLBACK_MODELS=glm5_2_nv,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450,
  NVU_BUFFER_PING_INTERVAL_S=30
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  FALLBACK_UPSTREAM_MODEL=glm5_2_ms, PRIMARY_UPSTREAM_MODEL=dsv4p_nv,
  PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
  CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150

## 八、Fallback 配置实测
- nv_gw: NVU_DISABLE_MS_FALLBACK=0 (ms fallback 启用, 仅覆盖 glm5_2_nv)
- NVU_MS_FALLBACK_MODELS=glm5_2_nv (不含 dsv4p_nv)
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv (dsv4p_nv 跳过 peer fallback)
- → dsv4p_nv 全挂时 nv_gw 裸返 429/502, cc4101 层 ms_gw(glm5_2_ms) 兜底
