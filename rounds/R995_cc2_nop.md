# R995 — cc2 NOP 巡检轮 (不改码)

- 日期: 2026-08-07
- 轮类: **NOP — cc2 主链路连续第 103 轮 100% 干净**
- 上轮: R994 (NOP, 主链 117/117=100%)

## 结论

cc4101-primary (主 nv_gw:40006) **121/121 = 100% SR, 0 bad**; 主链专属错误 **0 rows**;
fallback **0 次**。不改码。

## 本轮数据 (live re-pull 2026-08-07)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **121/121 = 100% SR, 0 bad** (live 复核) | ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** (error_type 分组空) | ✅ |
| fallback (cc_requests 30min) | 0 次 (121 req 全未 fallback_triggered) | ✅ |
| buffer/wait | 全 attempt=1 一次成功, flush 1.2–4.2KB, elapsed 2–13s, 无 WAIT 停滞, 无多 attempt 泄漏 | ✅ |
| nv_tier_attempts | 5 key 全 pexec_success (21–27/keey), 瞬态 RemoteDisconnected/Timeout 被 multi-key round-robin 吸收, 无 all_tiers_exhausted | ✅ |
| 容器 | nv_gw Up 11h, cc4101 Up 11h, health 全 200 | ✅ |

## 分析

- 主链无任何非 200 请求, 主专属错误 0 rows (本窗口比 R994 更干净 — R994 有 2 条 hermes 越界 bad)。
- 本轮 window 内 nv_requests 总 bad 为 0 (cc4101-primary 121/121 全 200), 无 hermes 泄漏。
- fallback 0 次, 链路全走 primary dsv4f0731_nv。
- buffer 全 attempt=1 一次成功, 无 multi-attempt 泄漏, func_health + multi-key round-robin 完全吸收瞬态键错误。
- 无持久 key 疲劳、无关键错误类。达稳态, 无参数可调。

## 下一步

- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 继续监控 hermes 越界 bad (fid 52e1ddb6) 是否与主链容器隔离 (host 分离持续保持)。