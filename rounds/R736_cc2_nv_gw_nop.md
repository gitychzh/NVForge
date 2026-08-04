# R736: cc2 nv_gw NOP 巡检 (08-05 ~04:50, cc2 SR 100%/fb 0%, 持续收敛)

> 时间: 2026-08-05 04:50 CST (20:50 UTC)
> 容器: nv_gw (40006, HM2, glm5_2_nv via NVCF) + cc4101 + dsv4p_nv40066 (Up 但非当前 fallback)
> 状态: NOP (不改码, 不改 env)

## 1. 背景 (改前必有数据)

R735 STATE.md 记录 "最近 22min SR 100%/fb 0%, 30min 全窗 91.6%/8.1% 受前段 529 余波拖累"。
接棒注入数据 (~04:46 快照) 显示 cc4101-primary 30min: 42×200+1×502(buffer_exhausted) → SR 97.7%,
hermes caller 走 dsv4f0731_nv 出现 8×502 all_tiers_exhausted。本轮实测 ~04:50 拉数据验证。

## 2. 真实当前架构 (实测 env, 沿 R735 round §2, 无漂移)

- nv_gw: 单 mode pexec_us_rr, 全 5 key 绑 fid1=b1b22d03, per-key 绑死 US IP (7901/7894/7897/7896/7899)
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
- 注: STATE.md 顶部 CLAUDE.md 仍写 "R-glm52split per-key 混合链路 + cc4101 fallback=dsv4p_nv40066" 是过时描述, R735 round 已修正, 本轮沿修正版

## 3. 改前数据 (实测 ~04:50 CST, 30min 窗)

### cc4101-primary (cc2 我自己, 30min nv_requests)
| status | count | avg_dur |
|--------|-------|---------|
| 200 | 47 | 38430ms |
- **nv_gw 层 SR (我) = 47/47 = 100%** (零 502/499/503)
- fb 触发率 = 0/47 = **0%**
- 分钟分布: 20:17-20:47 UTC 共 22 个分钟桶, 全 200, 无抖动

### cc4101 全 caller (30min cc_requests)
| total | ok | fb | sr | fb_pct |
|-------|----|----|----|--------|
| 46 | 45 | 0 | 97.8 | 0.0 |
- 1×非 200 是 buffer_exhausted (time=, avg 不详) 非 cc2 caller

### per-caller nv_requests (30min)
| caller | status | error_type | count | avg_ms |
|--------|--------|------------|-------|--------|
| cc4101-primary | 200 | - | 47 | 38430 |
| hermes | 200 | - | 17 | 34198 |
| hermes | 502 | all_tiers_exhausted | 8 | 51445 |
- **cc2 (cc4101-primary) 100% SR**, hermes 502 全走 dsv4f0731_nv (NVCF 上游容量, 非 cc2 链路)

### per-key tier (glm5_2_nv, cc2 的请求, 30min nv_tier_attempts)
| nv_key_idx | error_type | count |
|------------|------------|-------|
| 0 | pexec_success | 11 |
| 1 | pexec_success | 8 |
| 2 | pexec_success | 8 |
| 3 | pexec_success | 10 |
| 4 | pexec_success | 10 |
- **全 5 key pexec_success, 零 529/零 RemoteDisconnected/零 Timeout** — glm5_2_nv 链路非常 healthy
- 注: 30min 全 tier (含 dsv4f0731_nv) 有 529_nv_overloaded×68 + integrate_overloaded×5, 全来自 hermes→dsv4f0731_nv, 非 cc2

### 注入快照 vs 实测一致性
- 注入 "30min cc4101-primary: 42×200+1×502" vs 实测 "47×200+0×502" — 实测窗口更晚, 502 已消失, SR 升至 100%
- 注入 "8×all_tiers_exhausted" 对应 hermes caller (dsv4f0731_nv), 与实测一致
- 注入 "per-key 529_nv_overloaded k0=14/k1=18/..." 是全 tier 30min聚合, glm5_2_nv tier 本身零 529

## 4. 判稳结论

- **cc2 nv_gw 链路 (glm5_2_nv) 本轮 30min SR 100%, fb 0%, per-key 全 pexec_success** — 全面达标 (SR≥99%, fb<10%)
- 持续收敛: R735 最近 22min 100% → R736 最近 30min 100%, 529 余波已平息 (对 cc2 路径)
- hermes caller 的 8×502 全是 dsv4f0731_nv NVCF 上游容量问题, 不是 cc2 nv_gw 链路, 非 nv_gw 配置可解
- avg_dur 38s 正常 (无长尾), 无 buffer_exhausted (上轮 1× 已消失)
- **NOP 巡检轮** — 链路已稳, 无可改项

## 5. 改动 + 验证

### 改动: 不改码 (NOP)

### 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (5 keys, glm5_2_nv default) + cc4101 ok (primary=glm5_2_nv) — 全 ok
- `docker ps`: nv_gw Up 2h, cc4101 Up 3h, dsv4p_nv40066 Up 8h, nv_gw_stable Up 3days, logs_db Up 5days — 全 Up
- env 沿 R735, 无漂移

## 6. 下一步

- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+ / fb <10%)
- 连续 2 轮 (R735/R736) cc2 路径 SR 100%, 529 余波对 cc2 已平息 — 链路稳定
- 若 dsv4f0731_nv 的 529 storm 再起影响 hermes, 非本 agent 职责 (cc2 只走 glm5_2_nv)
- 流量低时不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 沿用: 分析用 created_at (R730/R732/R735/R736 已实证)

## 7. 参数快照 (实测 env, 沿 R735, 无变化)

- nv_gw: NVU_DISABLE_MS_FALLBACK=1, 单 mode MODE_CHAIN=pexec_us_rr, KEY_MODE_BIND=空,
  KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0 (全 5 key 绑 fid1=b1b22d03),
  KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899, RR_US_PROXIES=7901,7894,7897,7896,7899
  - buffer 5×90s=450s (NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450)
  - UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, NVU_KEYMGR_429_BASE=120/MAX=600, CONN_BASE=30/LONG=120/MAX=60
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007,
  STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130,
  PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
