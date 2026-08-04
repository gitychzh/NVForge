# R755 — NOP 巡检轮 (2026-08-05, ~06:30 CST)

## 改动: 不改码 (NOP)

## 依据 (实测 ~06:30 CST created_at 实测核验)
- **cc2 (cc4101-primary) glm5_2_nv: nv_requests 89×200 (SR=100%) + cc_requests 88 total/88 ok/0 fb (SR=100%, fb=0%)** — 连续第 21 轮 100%
- per-key pexec_success 实测 (created_at 口径): k0=20, k1=17, k2=16, k3=18, k4=17 = 总 88, 与 cc_requests 88 一致 (零差额) — 无任何错误穿透 cc2
- 噪声 all_tiers_exhausted × 6 来自 hermes->dsv4f0731_nv NVCF 容量, 非 cc2 链路 (cc2 nv_requests 全 200)
- 注入的 NVCFPexecRemoteDisconnected/529/empty_200 全部不在 cc2 可见路径

## 判稳结论
- **cc2 nv_gw 链路连续 21 轮 (R735~R755) SR 100%, fb 0%** — 全面达标 (目标 SR 99%+/fb <10%)
- 本轮 per-key 全 pexec_success 无 cc2 错误穿透 — 连续第 9 轮最干净
- NOP 巡检轮 — 链路已稳, 无可改项

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (5 keys, nv_num_keys=5), cc4101 ok (primary=glm5_2_nv) — 全 ok
- `docker ps`: nv_gw Up 3h, cc4101 Up 4h, dsv4p_nv40066 Up 9h, nv_gw_stable Up 3d, logs_db Up 5d — 全 Up
- env 沿 R754, 无漂移

## SR 趋势
| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R735 | 100% (最近 22min) | 30min 91.6% 被 529 余波拖低 |
| R742 | 100% (81 nv / 83 cc) | 8th consecutive, fb=0 |
| R753 | 100% (84 nv / 84 cc) | 19th consecutive, fb=0 |
| R754 | 100% (87 nv / 87 cc) | 20th consecutive, fb=0, 8th consecutive cleanest |
| R755 | 100% (89 nv / 88 cc) | 21th consecutive, fb=0, 9th consecutive cleanest |

## 下一步
- 持续监控 cc2 SR + fb 触发率
- 流量低时不动码, 仅 NOP 记数据
- created_at 口径沿用 (cc_requests.ts 时区 bug)

## 参数快照 (实测 env, 沿 R754, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, 单 mode pexec_us_rr, 全 5 key 绑 fid1=b1b22d03,
  KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899, buffer 5×90s=450s
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007,
  STREAM_TOTAL=470, HEADER=400
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
