# R497 — NOP 巡检轮 (2026-08-03 05:12 CST)

## 摘要
- 0 改动 0 restart. NOP 巡检轮 (连续低谷窗口延续, R475-R496 模式延续).
- cc2 (cc4101-primary) 30min 0 req (session 间歇空闲, 无评估样本, 铁律1 不满足 → 不动码).
- dsv4p_nv 全 caller 30min SR=20.0% (2/10: 2×200 + 7×429 + 1×502), 低谷窗口 (UTC 20-21h), 与 R490-R496 同模式.
- 错误: all_tiers_exhausted ×7 (历史一致, R268 起 190+ 轮) + zombie_empty_completion ×1 (nv_gw 主动防御, 非新故障).
- 6h dsv4p_nv SR 趋势: 15h=82% → 16h=84% → 17h=74% → 18h=69% → 19h=27% → 20h=25% → 21h=40% (昼夜周期性衰减).
- 配置实测无漂移, 容器健康 (nv_gw Up 15h, cc4101 Up 4h, /health ok, 5 keys).

## 链路数据 (05:06 CST 实测)
### 30min 全 caller (dsv4p_nv)
- 10 req: 2×200 (avg_dur=7148ms), 7×429 (avg_dur=1867ms), 1×502 (avg_dur=1881ms) → SR=20.0%
- 错误分类: all_tiers_exhausted ×7 (avg_dur=1867ms), zombie_empty_completion ×1 (avg_dur=1881ms)
- nv_tier_attempts 30min 0 行 (429 在 tier 层前被 KeyManager 全局冷却拦截, 与 R470-R496 一致)

### cc4101-primary 专属 (cc2 的请求)
- 30min 0 req (session 间歇空闲)

### 6h dsv4p_nv 小时级 SR
| UTC hr | ok | fail | SR% |
|---|---|---|---|
| 15 | 28 | 6 | 82 |
| 16 | 43 | 8 | 84 |
| 17 | 25 | 9 | 74 |
| 18 | 22 | 10 | 69 |
| 19 | 4 | 11 | 27 |
| 20 | 4 | 12 | 25 |
| 21 | 2 | 3 | 40 |

→ 昼夜周期性: 高峰 82-84%, 低谷 25-27%, 与 R490-R496 完全一致.

### zombie_empty_completion 分析 (本轮唯一"新"错误)
- 日志: [NV-ZOMBIE-EMPTY] (dsv4p_nv) passthrough zombie empty completion: finish_reason=stop but content_chars=12 reasoning_chars=31 sum=43 < 50, input_chars=108110 >= 5000, no real tool_calls — aborting stream to trigger fallback
- 行为: dsv4p 返回空内容 (content+reasoning<50字符), nv_gw 不下发空响应, 主动 abort 流 → 触发 cc4101 fallback 到 ms_gw (glm5_2_ms)
- 这是 R2311 起的 zombie 主动防御设计, 非故障. 24h 仅 1 次, 低频.
- status=502 是 abort 后下游收到的状态码 (非 NVCF 真实 502).

## keymgr 行为 (与 R496 一致)
- 单次 429 触发 NV-GLOBAL-COOLDOWN: all keys 429, Marking all cooling 180s (TIER_COOLDOWN_S=180)
- tier=dsv4p_nv 单 tier 无 ring fallback → all_tiers_exhausted 直接 ABORT-NO-FALLBACK
- 历史一致行为 (R268 起 190+ 轮), 非本轮新故障.

## 判稳
- cc2 0 流量 → 无评估样本, 改前无数据 (铁律1 不满足), 不动码.
- dsv4p_nv 30min SR=20.0% 仍是低谷窗口 (UTC 20-21h), 6h 视角呈昼夜周期性衰减 (82%→25%), 属稳态周期性行为, 非 nv_gw 侧可修复 (根因在 NVCF dsv4p 配额/IP 漂移).
- zombie_empty_completion ×1 是 nv_gw 主动防御, 符合 R2311 设计, 非新错误.
- fallback 兜底正常 (cc4101 层走 ms_gw glm5_2_ms).
- 0 restart → 无需 py_compile / curl 复测.
- 配置实测与 R475-R496 完全一致, 无配置漂移.

## 容器健康 (05:11 实测)
- curl /health: status=ok, proxy_role=passthrough, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], port=40006.
- docker ps: nv_gw Up 15h, cc4101 Up 4h, nv_gw_stable Up 27h, ms_gw Up 3 days, logs_db Up 3 days.
- 0 restart.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为.
- 关注 zombie_empty_completion 频次: 若 >=3/h 再评估 zombie 阈值 (当前 content+reasoning<50).
- dsv4p_nv 小时级 SR 持续 <60% + cc2 缓冲流量恢复后再评估是否切换 PRIMARY_UPSTREAM_MODEL 或增加 ring fallback.
- all_tiers_exhausted 持续 >=5/h 且中段不恢复 再评估 TIER_COOLDOWN_S 180s 是否过激.
- 留意 502 再现频次 (zombie abort 会产生 502, 区分真实 502 与 zombie 502).

## 参数快照 (本轮未改)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE=0,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90,
  NVU_BUFFER_TOTAL_DEADLINE_S=450, NVU_BUFFER_PING_INTERVAL_S=30, NVU_STREAM_FULL_BUFFER=0,
  NVU_KEYMGR_429_BASE_COOLDOWN=120, NVU_KEYMGR_429_MAX_COOLDOWN=600,
  NVU_KEYMGR_CONN_BASE_COOLDOWN=30, NVU_KEYMGR_CONN_FAIL_THRESHOLD=3,
  NVU_KEYMGR_CONN_LONG_COOLDOWN=120, NVU_KEYMGR_CONN_MAX_COOLDOWN=60
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_HEADER_TIMEOUT=400, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  CC4101_PRIMARY_FAIL_THRESHOLD=3, CC4101_PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- deadline 链: 90s/attempt × 5 = 450s buffer < 470s cc4101 < 500s SDK idle
- settings.json: contextWindow=170000, autoCompactWindow=155000, API_TIMEOUT_MS=600000
