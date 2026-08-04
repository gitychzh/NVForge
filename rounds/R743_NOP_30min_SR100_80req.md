# R743 — cc2 nv_gw NOP 巡检 (第 9 连续 100% 轮)

**时间**: 2026-08-05 05:12 CST
**上轮**: R742 (NOP, 100%/fb 0%, 第 8 连续)
**本轮**: NOP 巡检 — 无改码 (链路已稳)

## 实测数据 (created_at 30min 窗, ~05:12 CST)

### cc2 (cc4101-primary) 真实 SR
- cc_requests: **80×200, fb=0, SR=100.0%** (created_at 实测)
- nv_requests: **80×200, SR=100%** (caller=cc4101-primary)
- 注入 ts 口径 "f|95" = cc_requests.ts 列时区 bug 旧数据混入, 非真实 fb (R730 起实证沿用)

### per-key tier 分布 (cc2 链路, nv_tier_attempts, tier=glm5_2_nv)
- k0-k4 各 15-16 pexec_success ≈ 合计 77 (快照时刻), 与注入 77×200 一致; created_at 复测 80×200
- 529_nv_overloaded 散布全 key (k0:5, k1:2, k2:3, k3:2, k4:3) + NVCFPexecRemoteDisconnected (各 2-3) → 被 buffer 兜住
- k1/k3 empty_200×1, k4 529_integrate_overloaded×1 — 微噪声, cc2 不可见

### 全 caller 错误分类 (nv_requests, status!=200)
- all_tiers_exhausted × 5 (avg_dur 94s) — hermes→dsv4f0731_nv 6×502 对应, NVCF 容量
- NVStream_IncompleteRead × 1 (36s)

### hermes→dsv4f0731_nv (非 cc2 链路)
- 12×200 + 6×502 (SR 66.7%) — NVCF upstream 容量, 非 cc2 nv_gw

## 判稳结论
- **cc2 nv_gw 链路连续 9 轮 (R735~R743) SR 100%, fb 0%** — 全面达标
- 529 storm + empty_200/integrate_overloaded 微噪声持续, 但被 buffer (fid1 b1b22d03) 兜住, cc2 不可见
- hermes 6×502 是 dsv4f0731_nv NVCF 容量, 不是 cc2 链路
- NOP 巡检轮 — 链路已稳, 无可改项

## 验证 (NOP 无需 restart)
- /health: nv_gw ok (5 keys, glm5_2_nv default) + cc4101 ok (primary=glm5_2_nv)
- docker ps: nv_gw Up 2h, cc4101 Up 4h, dsv4p_nv40066 Up 9h, dsvf0731_nv40666 Up ~1h — 全 Up
- env 沿 R742, 无漂移

## 改动: 无 (NOP)

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+ / fb <10%)
- 529 noise + empty_200 持续观察, 若泄漏到 cc2 (buffer 失效) 再查
- 流量低时不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 沿用: 分析用 created_at (R730 起实证)

## SR 趋势
| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R735 | 100% (最近 22min) | 30min 91.6% 被 529 余波拖低 |
| R736 | 100% (47/47) | 余波平息 |
| R737 | 100% (51/51) | 持续稳定 |
| R738 | 100% (60/60) | 52e1ddb6 fid 529 被 buffer 兜住 |
| R739 | 100% (68/68) | empty_200/integrate_overloaded 微噪声不可见 |
| R740 | 100% (73/73) | 流量略增 |
| R741 | 100% (77/77) | pexec_success=77 与 cc2 200 一致 |
| R742 | 100% (81 nv / 83 cc) | 8th consecutive, fb=0 (created_at 实测) |
| R743 | 100% (80 nv / 80 cc) | 9th consecutive, fb=0 (created_at 实测) |
