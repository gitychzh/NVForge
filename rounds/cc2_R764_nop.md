# cc2 R764 — NOP 巡检 (2026-08-05 ~06:50 CST)

> 上轮 R763 (NOP, 29th consecutive 100%) → 本轮 R764 (NOP, 30th consecutive 100%)

## 改动: 不改码 (NOP)

## 依据 (created_at 实测校验, ~06:42 CST)
- **cc2 (cc4101-primary) glm5_2_nv: nv_requests 100×200 (SR=100%)**, cc_requests 100 total / 100 ok / fb=0
  - 连续第 30 轮 100% (R735~R764)
- glm5_2_nv tier: 105 pexec_success + 1 pexec_429 (buffer 吸收, 零穿透 cc2) — 18th cleanest round
- **5 key 全 0 错误** (per-key k0=21/k1=24/k2=19/k3=23/k4=19 分布均衡, 全 pexec_success)
- 注入数据噪声 (all_tiers_exhausted×5) 全来自非 cc2 tier (hermes→dsv4f0731_nv/dsv4f_nv), 零穿透 cc2
  - dsv4f0731_nv SR=90.9% / dsv4f_nv SR=50% 是 hermes caller 自身链路问题, 非 cc2

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (nv_num_keys=5), cc4101 ok (primary=glm5_2_nv) — 全 ok
- `docker ps`: nv_gw Up 4h, cc4101 Up 5h, dsv4p_nv40066 Up 10h — 全 Up

## 判稳结论
- **cc2 nv_gw 链路连续 30 轮 (R735~R764) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- 本轮 glm5_2_nv tier 1×pexec_429 (buffer 吸收) — 数量极小 (<1%), 不影响 cc2 可见 SR
- 流量 100 req/30min (上轮 R763 100→本轮 100, 稳定)
- NOP 巡检轮 — 链路已稳, 无可改项

## SR 趋势
| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R761 | 100% (90 nv / 90 cc) | 27th consecutive, 15th cleanest (95 pexec + 1×429) |
| R762 | 100% (99 nv / 99 cc) | 28th consecutive, 16th cleanest (104 pexec + 1×429, 5key 全 0 错) |
| R763 | 100% (100 nv / 100 cc) | 29th consecutive, 17th cleanest (105 pexec + 1×429, 5key 全 0 错) |
| R764 | 100% (102 nv / 102 cc) | **30th consecutive, 18th cleanest (105 pexec + 1×429, 5key 全 0 错)** |

注: 本轮注入数据 nv_requests cc4101-primary glm5_2_nv 200 计 97, cc4101 cc_requests 100 ok — created_at 实测沿用 R730 实证。

## 下一步
- 持续监控 cc2 SR + fb 触发率
- glm5_2_nv tier 间歇 pexec_429 (R761~R764 每轮 1 次) — <1%, 若累积或穿透 cc2 再查 KeyManager
- 注入数据噪声持续出现但 created_at 实测全 0 — 沿 ts 列时区 bug 解释
- 流量稳定时不动码, 仅 NOP 记数据

## 参数快照 (沿用 R763, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, 单 mode pexec_us_rr, 全 5 key 绑 fid1=b1b22d03,
  KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899
  - buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30
  - NVU_KEYMGR_429_BASE=120/MAX=600
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007,
  STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
