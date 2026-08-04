# R759 — NOP 巡检轮 (2026-08-05 ~06:20 CST)

> 上轮: R758 (NOP, 第 24 连续 100%)
> 容器: nv_gw Up 3h, cc4101 Up 5h, dsv4p_nv40066 Up 10h, logs_db Up 5d — 全 Up

## 决策: NOP (不改码)

### 依据 (注入轮前链路分析 ~06:13 CST + created_at 实测校验)

**cc2 主链路 (glm5_2_nv via nv_gw)** — SR 100%, fb 0%:
- 注入: cc4101-primary|glm5_2_nv|200|79 — 79/79 = 100%
- 注入: cc4101-primary 30min = `200|79|14808` — 全 200
- **created_at 实测**: cc_requests 79 total / 79 ok / **fb=0** ✅
- **created_at 实测**: nv_requests caller=cc4101-primary = 79×200, 零非 200 ✅

**tier 铁证 (created_at 30min)**:
- `glm5_2_nv` tier: **pexec_success=79, 零错误** ✅
- `dsv4f0731_nv` tier: NVCFPexecRemoteDisconnected=14, empty_200=4 — hermes 备用链路噪声, 不在 cc2 路径

**注入噪声溯源**:
- all_tiers_exhausted × 6 (avg_dur 111068ms): hermes→dsv4f0731_nv 全挂导致的 502, 被 hermes 侧 buffer 兜住, 零穿透到 cc2
- "f|94" fallback 段: ts 列时区 bug 口径, created_at 实测 fb=0 (R730 起实证, 沿用)
- NVCFPexecRemoteDisconnected × 14 / empty_200 × 4: 全部 dsv4f0731_nv tier

**per-key 平衡** (注入 nv_tier_attempts, 全 pexec_success):
- k0=17, k1=16, k2=16, k3=14, k4=16 = 79 (与 cc2 nv_requests 79 一致, 零丢失)

### 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (5 keys), cc4101 ok (primary=glm5_2_nv) — 全 ok
- `docker ps`: 全 Up, 无重启
- env 沿 R758, 无漂移

## 判稳结论
- **cc2 nv_gw 链路连续 25 轮 (R735~R759) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- 本轮 glm5_2_nv tier 零错误, 零穿透 — **连续第 13 轮最干净**
- 流量 79 req/30min (上轮 84→79, 窗口抖动正常范围), 链路稳
- NOP 巡检轮 — 无可改项

### SR 趋势
| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R735 | 100% | 22min 窗内 100% |
| R742-R758 | 100% | R735 起连续 24 轮 |
| R759 | 100% (79 nv / 79 cc) | **25th consecutive, fb=0, 13th cleanest** |

## 下一步
- 持续监控 cc2 SR + fb 触发率
- hermes→dsv4f0731_nv 502 容量噪声若扩大可监测, 不属本轮 cc2 优化范围
- 流量低时不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 沿用 created_at 分析 (R730 起实证)

## 参数快照 (实测 env, 沿 R758, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, MODE_CHAIN=pexec_us_rr, 全 key 绑 fid1=b1b22d03,
  KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899
  - buffer 5×90s=450s (NVU_BUFFER_MAX_RETRIES=5)
  - UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NVU_KEYMGR_429_BASE=120/MAX=600
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007,
  STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
