# R739 — cc2 nv_gw NOP 巡检 (2026-08-05 05:01 CST)

## 改动: 不改码 (NOP)

## 依据 (实测 ~05:01 CST, 30min 窗, created_at 时区)
- **cc2 (cc4101-primary) glm5_2_nv: 68×200, SR=100%, fb=0%** — 连续第 5 轮 100%
- cc_requests 30min: total=68, ok=67, fb=0, SR=98.5% (1 个非 200 边缘, cc2 nv_gw 全 200)
- 注入数据 cc4101-primary|glm5_2_nv|200|65 与 DB 68×200 一致 (窗口偏移)
- hermes→dsv4f0731_nv: 12×200 + 9×502 all_tiers_exhausted (NVCF 容量, 非 cc2 链路)

## per-key tier 分布 (529 余波仍在但被 buffer 兜住)
- k0-k4 各 9-12 个 529_nv_overloaded + 几个 NVCFPexecRemoteDisconnected
- k3 出现 1 个 empty_200, k4 出现 3 个 529_integrate_overloaded
- 52e1ddb6 fid 继续在 tier attempts 跑 (R738 观察,多 caller 共用副作用),对 cc2 不可见
- buffer 用 fid1 (b1b22d03) 兜住 529 → 最终 cc2 全 200

## 验证 (NOP 无需 restart)
- `/health`: nv_gw ok (5 keys, glm5_2_nv default) + cc4101 ok (primary=glm5_2_nv) — 全 ok
- `docker ps`: nv_gw Up 2h, cc4101 Up 3h, dsv4p_nv40066 Up 8h, ms_gw Up 3h — 全 Up 无异常
- env 沿 R738, 无漂移

## 判稳结论
- **cc2 nv_gw 链路连续 5 轮 (R735-R739) SR 100%, fb 0%** — 全面达标
- 529 storm + 52e1ddb6 fid 噪声持续, 但对 cc2 不可见 (buffer 兜住)
- NOP 巡检轮 — 链路已稳, 无可改项

### SR 趋势
| 轮 | 30min 窗 SR | 备注 |
|---|---|---|
| R735 | 100% (22min) | 529 余波 |
| R736 | 100% (47/47) | 余波平息 |
| R737 | 100% (51/51) | 持续稳定 |
| R738 | 100% (60/60) | 52e1ddb6 fid 出现,被 buffer 兜住 |
| R739 | 100% (68/68) | 持续稳定, EMPTY_200/integrate_overloaded 微噪声不可见 |

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+ / fb <10%)
- 52e1ddb6 fid + 529 storm 持续观察, 若未来泄漏到 cc2 (buffer 失效) 再查
- 流量低时不动码, 仅 NOP 记数据
- cc_requests.ts 时区 bug 沿用: 分析用 created_at
