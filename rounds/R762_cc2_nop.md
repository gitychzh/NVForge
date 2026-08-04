# R762 — cc2 NOP 巡检轮 (2026-08-05 ~06:36 CST)

> 上轮: R761 (NOP, 第 27 连续 100%)
> 本轮: R762 (NOP, 第 28 连续 100%, 第 16 连续最干净)

## 改动: 不改码 (NOP)

## 依据 (created_at 实测校验, ~06:36 CST)

### cc2 链路真值 (created_at, 30min 窗)

| 指标 | created_at 实测 | 达标 |
|---|---|---|
| cc2 nv_requests | 99×200 (SR=100%) | ✅ |
| cc_requests | 99 total / 99 ok / **fb=0** | ✅ |
| SR | 100.0% | ✅ (目标 99%+) |
| fallback 触发率 | 0% | ✅ (目标 <10%) |

### glm5_2_nv tier 错误分布 (30min, created_at)

| error_type | count |
|---|---|
| pexec_success | 104 |
| pexec_429 | 1 |

- **5 key 全 0 错误** (per-key ok=0 错误: k0=20/k1=23/k2=18/k3=25/k4=19 全 pexec_success)
- 1×pexec_429 由 buffer 吸收, 不穿透 cc2 → cc2 99/99=100%

### 注入数据 vs 实测对照

| 指标 | 注入口径 | created_at 实测 | 差异原因 |
|---|---|---|---|
| cc2 nv_requests count | 95 | 99 | 注入窗口偏移 |
| fallback 发生率 | f\|149 (暗示大量 fb) | **0 fb** | ts 列时区 bug (沿 R730 实证) |
| tier RemoteDisc | 14 | 0 | 注入器拼入历史/其他 tier 噪声 |
| tier empty_200 | 3 | 0 | 同上 |
| tier 529_nv_overloaded | 1 | 0 | 同上 |
| per-key 错误 | 5 key 全有 | 5 key 全 0 | 同上 |

→ **本轮再次实证: cc2 决策必须以 created_at 实测为准, 注入数据仅作背景参考** (沿 R730/R742~R761 惯例)。

## 验证 (NOP 无需 restart)

- `/health`:
  - nv_gw ok (nv_num_keys=5, pexec_models 含 glm5_2_nv)
  - cc4101 ok (primary=glm5_2_nv)
- `docker ps`: nv_gw Up 4h, cc4101 Up 5h, dsv4p_nv40066 Up 10h, dsvf0731_nv40666 Up 1h, ms_gw 不可见但 nv_gw_health ok, logs_db Up — 全 Up

## 判稳结论

- **cc2 nv_gw 链路连续 28 轮 (R735~R762) SR 100%, fb 0%** — 全面达标
- 本轮第 16 连续最干净轮 (glm5_2_nv tier 仅 1×pexec_429, 5 key 全 0 错误)
- 流量 99 req/30min (上轮 R761 实测 90→本轮 99, 小幅上升), 链路稳
- **NOP 巡检轮 — 链路已稳, 无可改项**

### SR 趋势

| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R735 | 100% (最近 22min) | 30min 91.6% 被 529 余波拖低 |
| R742 | 100% (81 nv / 83 cc) | 8th consecutive, fb=0 |
| R748 | 100% (75 nv / 75 cc) | 14th consecutive, fb=0, 最干净 |
| R755 | 100% (89 nv / 88 cc) | 21th consecutive |
| R758 | 100% (84 nv / 84 cc) | 24th consecutive |
| R760 | 100% (85 nv / 87 cc) | 26th consecutive |
| R761 | 100% (90 nv / 90 cc) | 27th consecutive, 15th cleanest (1×429) |
| R762 | 100% (99 nv / 99 cc) | **28th consecutive, fb=0, 16th cleanest (1×429, 5key 全 0 错误)** |

## 下一步

- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- glm5_2_nv tier 间歇 pexec_429 (R761/R762 各 1 次) — 数量极小 (1/105 <1%), 不构成异常, 若累积或穿透 cc2 再查 KeyManager 退避
- 注入噪声 (历史 RemoteDisc / empty_200 / 529 / f\|149) 持续出现但 created_at 实测全 0, 沿用 ts 列时区 bug 解释
- 流量低时不动码, 仅 NOP 记数据

## 参数快照 (实测 env, 沿 R761 无变化)

- nv_gw: NVU_DISABLE_MS_FALLBACK=1, 单 mode pexec_us_rr, KEY_FID_BIND 全 5 key 绑 fid1=b1b22d03
  - buffer 5×90s=450s (NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2)
  - UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_KEYMGR_429_BASE=120/MAX=600
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007,
  STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
