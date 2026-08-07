# R996 — cc2 NOP 巡检轮 (不改码)

- 日期: 2026-08-07
- 轮类: **NOP — cc2 主链路连续第 104 轮 100% 干净**
- 上轮: R995 (NOP, 主链 121/121=100%)

## 结论

cc4101-primary (主 nv_gw:40006) **120/120 = 100% SR, 0 bad**; 主链专属错误 **0 rows**;
fallback **0 次**。不改码。

## 本轮数据 (live re-pull 2026-08-07)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **120/120 = 100% SR, 0 bad** (live 复核; 注入快照 117/117, 流量推进至 120) | ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** (error_type 分组空) | ✅ |
| nv_requests 总 bad | 2 条, **全属 hermes** (nvcf_pexec 502: all_tiers_exhausted×1 + stream_absolute_cap×1, 越界宿主) | ✅(主链无) |
| fallback (cc_requests 30min) | 0 次 (120 req 全未 fallback_triggered) | ✅ |
| buffer/wait | 全 attempt=1 一次成功, flush 9.6–25.5KB, elapsed 5–14s, 无 WAIT 停滞, 无多 attempt 泄漏 | ✅ |
| nv_tier_attempts | 5 key 全 pexec_success (21–27/key), 瞬态 RemoteDisconnected(1–6)/Timeout(1)/empty_200(1) 被 multi-key round-robin 吸收, 无 all_tiers_exhausted | ✅ |
| 模型 SR | dsv4f0731_nv = 136/138 = 98.6% (含 hermes 2 bad) | — |
| 容器 | nv_gw Up 12h, cc4101 Up 11h, health 全 200 | ✅ |

## 分析

- cc2 主链 (caller=cc4101-primary) 120/120 全 200, 主专属错误 0 rows, **无任何 cc2 主链错误**。
- nv_requests 中仅有的 2 条非 200 (all_tiers_exhausted + stream_absolute_cap, 均 nvcf_pexec 502)
  **经 caller 归属 JOIN 判定为 hermes 越界宿主请求**, 非 cc2 主链 (与 R994/R993 同源的 fid 52e1ddb6 泄漏, host 分离保持)。
- fallback 0 次, 链路全走 primary dsv4f0731_nv。buffer 全 attempt=1 一次成功,
  无 multi-attempt 泄漏; func_health + multi-key round-robin 完全吸收瞬态键错误。
- 达稳态, 无持久 key 疲劳, 无 cc2 主链可调点。**不改码**。

## 下一步

- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 继续监控 hermes 越界 bad (fid 52e1ddb6) 是否与主链 host 隔离持续保持。