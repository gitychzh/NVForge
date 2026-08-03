# R716 (cc2/HM2): NOP 巡检 — cc2 零流量 + dsv4p93.5% + glm5_2_nv NVCF 上游持续退化

## TL;DR
R715 后 ~30min. cc2 本窗口零流量 (cc4101-primary 0 rows) — 无数据不动手. nv_gw 全量 30min: dsv4p_nv SR 93.5% (29/31, 兜底健康), glm5_2_nv SR 0% (0/2, NVCF 上游持续退化 ~10h+ 自 R713 起未恢复). 错误 all_tiers_exhausted × 4 (无新类型). per-key/per-IP 均衡健康. fallback f×33 全非 cc2. /health ok, 容器全 Up, 配置零漂移. 不改码.

---

## 一、依据 (30min 窗口 ~20:30-21:00 CST, 注入数据)

### 1.1 cc2 (cc4101-primary) 专属
- **0 rows** — cc2 本窗口零流量, 无数据不动手

### 1.2 nv_gw 全量 30min (hermes/openclaw caller, 非 cc2)
| model | 200 | 502 | SR |
|-------|-----|-----|-----|
| dsv4p_nv | 29 | 2 | 93.5% (29/31) — 兜底链路健康 |
| glm5_2_nv | 0 | 2 | 0% (0/2) — NVCF 上游持续退化 ~10h+ |

### 1.3 错误分类 (30min)
| error_type | count |
|------------|-------|
| all_tiers_exhausted | 4 |
(无新错误类型)

### 1.4 per-key (dsv4p)
| key | 200 | avg_dur(ms) |
|-----|-----|-------------|
| k0 | 6 | 13422 |
| k1 | 7 | 6444 |
| k2 | 5 | 7128 |
| k3 | 6 | 9021 |
| k4 | 5 | 14262 |
均衡健康, 无单 key 突出.

### 1.5 per-egress-IP (dsv4p)
| IP | count | SR% |
|----|-------|-----|
| 134.195.101.188 | 7 | 100 |
| 134.195.101.180 | 6 | 100 |
| 134.195.101.194 | 6 | 100 |
| 134.195.101.120 | 5 | 100 |
| 203.10.96.139 | 5 | 100 |
5 US IP 全 100%, IP 轮转健康.

### 1.6 dsv4p 200 延迟/token
- avg_dur 9887ms, max 28658ms, min 2491ms
- avg_ttfb 9416ms, avg_in 1, avg_out 10
- finish_reason: tool_calls×24, stop×3, length×2 (无 zombie)

### 1.7 fallback
- f×33 (全非 cc2, hermes/openclaw 流量)

### 1.8 buffer/wait/keymanager 日志
- 无 (无 buffer 触发, 链路直接 fallback 到 dsv4p)

---

## 二、改动: 不改码 (NOP)

### 决策
- cc2 零流量 → 无数据不动手 (铁律 1)
- dsv4p_nv SR 93.5% 兜底健康, glm5_2_nv NVCF 上游退化非 nv_gw 可控
- 无新错误类型, 配置零漂移 → NOP 巡检轮

---

## 三、验证: NOP 无需 restart

### /health
- nv_gw: ok (5keys, glm5_2_nv/dsv4p_nv/kimi_nv, port 40006)
- cc4101: ok (primary=glm5_2_nv, port 4101)
- dsv4p_nv40066: ok (5keys, port 40066)

### docker ps
- nv_gw Up 4h, cc4101 Up 5h, dsv4p_nv40066 Up 4h, nv_gw_stable Up 42h, logs_db Up 4d — 全 Up

### 配置零漂移 (R661 baseline)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, TIER_TIMEOUT_BUDGET_S=180
- NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2, NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, PRIMARY_SKIP_S=30, FAIL_THRESHOLD=3
- dsv4p_nv40066: pexec-only, NV_INTEGRATE_MODELS=空, NVU_DISABLE_MS_FALLBACK=1, PEER_FALLBACK=0

---

## 四、下一步
- 持续监控 cc2 SR + fallback 触发率 (目标 SR99%+ fb<10%)
- glm5_2_nv NVCF 上游持续退化中 (~10h+, 自 R713 起未恢复), 依赖 dsv4p 兜底, 非 nv_gw 可控
- 若 cc2 流量恢复后 fallback 率 >10% 再深入查 glm5_2_nv tier
- R661 post-restart ~42h+ 仍无新错误类型, 配置稳定
