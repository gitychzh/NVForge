# R923 cc2 NOP 巡检轮

> 日期: 2026-08-07 ≈10:01 CST | 上轮: R922 | 容器: nv_gw Up 7h, cc4101 Up 6h, dsv4p_nv40066 Up 2d
> 本 session 全新, 轮前链路分析数据已注入; 用 live DB 复核实拉确认归属。

## 结论: NOP (不改码) — cc2 主链路连续第 **32** 轮 100% 干净 (R892-R923)

## 数据 (live DB 30min 实拉 + 轮前注入快照)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **117/117 = 100% SR, 0 bad** (实拉 caller 分组 200 全归 cc4101-primary) | ✅ |
| 所有 bad (502) | 6 条全 `caller=hermes`, error `all_tiers_exhausted` | ⚠️ 越界 (非 cc2) |
| hermes 线坏累归 | 6 req 全 caller=hermes; cc2 primary 0 bad (0 leak) | ✅ host 分离 |
| 聚合 dsv4f0731_nv SR | 95.9% (116/121) — 纯被 hermes 502 拉低, cc2 primary 自身 100% | ⚠️ 越界 |
| fallback (cc_requests) | **0 次** (0/118) | ✅ |
| per-key tier | pexec_success 23/key 主导; 瞬态 NVCFPexecRemoteDisconnected/Timeout/504 分散 k0~k4, 被多 tier round-robin + func_health 吸收 | ✅ |
| buffer 效果 | 最近请求 attempt=1/5 一次成功 2~15s (66400c/67934c tool_calls), 无 retry/exhaustion | ✅ |
| 容器 health | 4101/40006/40066 全 200; nv_gw Up 7h, cc4101 Up 6h | ✅ |

## 判断依据

- cc2 自有主链 (cc4101-primary) SR **100% ≥ 99% 判稳**; 无新错误类; 0 fallback。
- bad 请求 100% `caller=hermes` (越 cc2 范围), caller 列实拉归属铁证 0 条进 cc2 主链。
- 聚合 dsv4f0731_nv 的 95.9% 是被 hermes 的 6 条 502 拉的, 非 cc2 自身问题 — 不作为改码依据。
- 不改码: ①cc2 主链 100% 无优化需求; ②坏请求全属 hermes 宿主, 与 R897 越界容器 40666 同模式 host-separated; ③多 tier round-robin + func_health 健康选择已达稳态。

## 下一步

- 保持监控; 若 hermes 的 all_tiers_exhausted 持续上升且跨 host 泄漏进 cc2 主链再处理。
- 已连续 32 轮 NOP 干净; 待基线稳定后评估是否收紧 hermes 与 cc2 的 key 池隔离 (坏 fid 52e1ddb6 容器+候选池双层隔离沿用)。