# R922 cc2 NOP 巡检轮

> 日期: 2026-08-07 ≈10:05 CST | 上轮: R921 | 容器: nv_gw Up 7h, cc4101 Up 6h, dsv4p_nv40066 Up 2d

## 结论: NOP (不改码) — cc2 主链路连续第 **31** 轮 100% 干净 (R892-R922)

## 数据 (live DB 30min 实拉)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **118/118 = 100% SR, 0 bad** (实拉 `status!=200` → 0 条) | ✅ |
| 所有 bad (502) | 5 条全 `caller=hermes`, error `all_tiers_exhausted` | ⚠️ 越界 (非 cc2) |
| hermes 线坏 bid | 5 req 全 caller=hermes; cc2 primary 0 bad | ✅ 隔离 |
| fallback (cc_requests) | **0 次** (0/117) | ✅ |
| per-key tier | pexec_success 117 主导; 瞬态 NVCFPexecRemoteDisconnected(16)/Timeout(4)/504(3) 被多 tier round-robin + func_health 吸收 | ✅ |
| buffer 效果 | 最近请求 attempt=1/5 ~5-10s 一次成功, 无 retry/exhaustion | ✅ |
| 容器 health | 4101/40006/40066 全 ok; nv_gw Up 7h, cc4101 Up 6h | ✅ |

## 判断依据

- SR 100% ≥ 99% 判稳; 无新错误类; bad 请求 100% call=hermes (越 cc2 范围),
  caller 列 + request_id 级 JOIN 双重归属铁证未进 cc2 主链。
- fallback 0 次, buffer 全一次成功, 主链达稳态。
- 不改码: ①主链 100% 无优化需求; ②坏请求全属 hermes; ③多 tier round-robin + func_health 健康选择已自适应吸收底层瞬态失败。

## 下一步

- 保持监控; 若 hermes 的 all_tiers_exhausted 持续上升且跨主机泄漏进 cc2 主链再处理 (R897 越界容器 40666 已 host-separated)。
- 待 NOP 基线稳定 35 轮后评估是否收紧 hermes 与 cc2 的 key 池隔离。