# R746 — NOP 巡检 (2026-08-05 05:25 CST)

> 上轮: R745 (NOP, 11th consecutive 100%). 本轮: R746 (NOP, 12th consecutive 100%).

## 改动: 不改码 (NOP)

## 依据 (实测 ~05:25 CST, 30min 窗, created_at 实测核验)

### cc4101-primary (cc2 链路, created_at)
- nv_requests: 80×200 (SR=100%)
- cc_requests: 80 req / 80 ok / 0 fb / SR=100% (created_at 实测)
- 注入的 "f\|90" 在 fallback 段 → created_at 实测 0 fb (ts 列时区 bug 口径, 沿 R730/R742-R745 实证)

### per-key tier 分布 (nv_tier_attempts, created_at)
- pexec_success=80 (与 cc2 80×200 一致)
- NVCFPexecRemoteDisconnected=14 (各 key 散布, 被 buffer 兜住)
- 529_nv_overloaded=3 (NVCF 容量, 被 buffer 兜住)
- empty_200=1 (微噪声, 不可见)
- **5key 全健康的 pexec_success 80 = cc2 80×200**, 噪声全部 buffer 兜住

### hermes→dsv4f0731_nv (非 cc2 链路, 注入)
- 9×200 + 6×502 (all_tiers_exhausted) + 2×NVStream_IncompleteRead
- NVCF 容量, 与 cc2 链路无关

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (5 keys, glm5_2_nv default) + cc4101 ok (primary=glm5_2_nv)
- `docker ps`: nv_gw Up 3h, cc4101 Up 4h, dsv4p_nv40066 Up 9h, dsvf0731_nv40666 Up ~1h, nv_gw_stable Up 3d, ms_gw Up 4h, logs_db Up 5d — 全 Up
- nv_gw env 沿 R745, 无漂移 (单 mode pexec_us_rr, 全 key 绑 fid1=b1b22d03, KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899)
- cc4101 env 沿 R745, 无漂移 (PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007, STREAM_TOTAL=470, HEADER=400)

## 判稳结论
- **cc2 nv_gw 链路连续 12 轮 (R735~R746) SR 100%, fb 0%** — 全面达标
- 529 storm + empty_200 + NVCFPexecRemoteDisconnected 微噪声持续, 但被 buffer 兜住, cc2 不可见
- hermes 6×502 + 2×IncompleteRead 是 dsv4f0731_nv NVCF 容量, 不是 cc2 链路
- NOP 巡检轮 — 链路已稳, 无可改项

### SR 趋势
| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R735-R744 | 100% | 略 (详见 STATE.md) |
| R745 | 100% (82 nv / 82 cc) | 11th consecutive |
| R746 | 100% (80 nv / 80 cc) | 12th consecutive, fb=0 (created_at 实测) |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+ / fb <10%)
- 529/empty_200/NVCFPexecRemoteDisconnected 持续观察, 若泄漏到 cc2 (buffer 失效) 再查
- 流量低时不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 沿用: 分析用 created_at (R730 起实证)
