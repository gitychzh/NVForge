# R783 — cc2 NOP 巡检 (49th consecutive 100%)

**日期**: 2026-08-05 ~08:20 CST
**上轮**: R782 (NOP, 48th consecutive 100%)
**改动**: 不改码 (NOP)

## 轮前链路分析 (30min 窗口 ~08:16 CST)

### cc2 (cc4101-primary|glm5_2_nv)
- **107 req × 200, SR=100%, 0 fallback** ✅
- avg_dur 27293ms — 稳定
- 零穿透坐实: cc4101-primary caller 全 200, 无错误

### tier 噪声 (全被 buffer/KeyManager 消化, 零穿透)
- `NVCFPexecRemoteDisconnected × 16`: k0:3 + k2:2 + k3:5 + k4:6
- `pexec_429 × 1`: k0 (单次 429, KeyManager 退避消化)
- `529_nv_overloaded × 2`: k1 + k2
- `empty_200 × 1`: k3
- per-key pexec_success: k0:21 + k1:21 + k2:22 + k3:24 + k4:19 = 107 (全 attempt=1 success)
- 无 buffer/wait 日志 (全 attempt=1 success)

### 注入噪声 (零穿透 cc2, 全在 dsv4 hermes caller)
- `dsv4f0731_nv 502 × 8` + `all_tiers_exhausted × 7` (98.57s avg) + `zombie_empty × 1`
- 注入目标为 hermes caller 的 dsv4f0731_nv, 非 cc2 链路

### dsv4p_nv fallback 链路健康
- SR=100% (30/30), per-key 均衡 (k0:7+k1:6+k2:6+k3:6+k4:5)
- avg_dur 16967ms, finish_reason 全 stop — 无 zombie

## 判稳结论
- **cc2 nv_gw 链路连续 49 轮 (R735~R783) SR 100%, fb 0%** — 全面达标
- 本轮 tier 噪声 20 (上轮 22→20, -2) — buffer 容错有效, 全 attempt=1 success
- 流量 107 req/30min (上轮 79→107, +28, 正常波动)
- k4 RemoteDisc 6 仍偏高 (连续 2 轮 k4:6) — 在容错范围, 监控
- NOP 巡检轮 — 链路已稳, 无可改项
- cleanest 计数停 27 (R774) — R774 后每轮 tier 噪声均>0

## 验证 (NOP 无需 restart)
- 容器: nv_gw Up 5h (上轮 STATE 记 10h, 重启过一次), cc4101 Up 7h, dsv4p_nv40066 Up 12h
- /health 全 ok: nv_gw passthrough (5 key), cc4101 primary=glm5_2_nv, dsv4p_nv40066 passthrough
- 注入链路分析实测 cc4101-primary: 107 nv / 107 ok / 0 err

## 下一步
- 持续监控 cc2 SR + fb 触发率 (目标 SR 99%+/fb <10%)
- 监控 k4 RemoteDisc (连续 2 轮 6 次) — 若持续升高可考虑排查 k4 fid3 (b6029a96)
- dsv4p_nv fallback 链路健康 — 应急链路 OK
