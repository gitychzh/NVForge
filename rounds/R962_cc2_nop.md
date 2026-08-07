# R962 — cc2 NOP 巡检轮 (不改码)

## 结论
cc2 主链路连续第 **70** 轮 (R893-R962) 100% SR 干净, 主链专属错误 0 行, fallback 0 次。
**不改码**。

## 数据 (live `/opt/cc-infra` 30min, ≈2026-08-07 12:31 CST)

- **cc4101-primary (主 nv_gw:40006) = 124/124 全 200 = 100% SR, 0 bad** (live re-pull, avg ~9066ms)
- 全局 nv_requests 30min = 136 req: 132 ok + 4 hermes bad (502)
- 4 bad = **均 caller=hermes**: `all_tiers_exhausted ×3` + `zombie_empty_completion ×1`
  (caller 列归属 hermes, 双重隔离 non cc2)
- fallback (cc_requests 30min) = **0 次** (124 req 全 status=200)
- nv_tier_attempts 30min: pexec_success 为主, NVCFPexecRemoteDisconnected 每 key 1-6 (瞬态,
  被多 key round-robin + func_health + buffer 全部吸收 → resolve 200)
- buffer 日志 (nv_gw --since 30m): cc4101-primary 全 **attempt=1 verdict=success_tool_call**,
  无 WAIT-/KEYMGR- 错误噪声
- health: 4101/40006/40066 全 200; 容器 nv_gw Up 9h, cc4101 Up 9h, dsv4p_nv40066 Up 2d

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | 124/124 = 100% SR, 0 bad | ✅ |
| 主链专属错误 (caller=cc4101-primary) | 0 rows | ✅ |
| 唯一 bad (非 200) | 502 all_tiers_exhausted ×3 + zombie_empty_completion ×1 (均 hermes) | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes, cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (124 全 200) | ✅ |
| 全局 nv_requests SR | 132/136 = 97.1% | ✅ |

## 关键判断
主链 SR 100% + 专属错误 0 行 + fallback 0 次, 稳态无优化需求。4 bad 全属 hermes 越 cc2 范围,
hermes 的 all_tiers_exhausted/zombie 由 hermes 自身 key pool 疲劳所致, 不泄漏进 cc2 主链。
多 tier round-robin (dsv4f0731_nv 为首) + func_health fid 健康选择持续自适应吸收底层瞬态。
**不改码。**

## 下一步
主链 SR 已达上限, 无需代码改动。继续 NOP 巡检; 若 hermes 的 all_tiers_exhausted/疲劳
异常漫过 cc4101-primary (主链专属错误 > 0 或 SR < 99%) 再干预。