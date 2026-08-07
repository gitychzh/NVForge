# R1008 — cc2 NOP 巡检轮

> 结论: **不改码**。cc2 主链路 (cc4101-primary → nv_gw:40006, dsv4f0731_nv 首代)
> 30min = **107/107 = 100% SR, 0 bad**, 主链专属错误 **0 rows**, fallback **0 次**。
> 连续第 **116** 轮 (R893-R1008) 100% 干净。

## 数据 (live re-pull 2026-08-07 15:49 CST)

| 指标 | 值 | 归属 |
|---|---|---|
| cc4101-primary (主 nv_gw:40006) 30min | **107/107 = 100% SR, 0 bad** | cc2 主链 ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** | cc2 主链 ✅ |
| nv_requests 总 bad (非 200) | 5 条, 全属 hermes (dsv4f0731_nv 502) | hermes, 非主链 |
| 错误分类 | all_tiers_exhausted ×4 + zombie_empty_completion ×1 (注入) | 全 hermes |
| cc_requests 30min fallback | 107 total, **fb=0** | ✅ |
| buffer 日志 | 全 attempt=1 一次成功 (2-13s), verdict=success_text/success_tool_call | ✅ |
| health | nv_gw/cc4101/dsv4p 全 200 | ✅ |

## 判定

cc2 主链路 (caller=cc4101-primary) 连续第 **116** 轮 (R893-R1008) 100% SR。
本轮 5 条 bad (dsv4f0731_nv 502) 归属全属 hermes 越界宿主 (fid 52e1ddb6 泄漏), 与主链 host 分离
保持, 主链 107/107 全 200。fallback 0 次, 无新 cc2 主链错误类, 无持久 key 疲劳。
buffer + multi-key round-robin + func_health 完全吸收瞬态错误, 全 attempt=1 一次成功 (2-13s)，
无 BUFFER-/WAIT- 停滞。

**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②本轮 bad 全属 hermes 越界, 主链无根因可查;
③ multi-key round-robin + func_health + buffer (attempt=1 全成功) 已达稳态, 无参数可调。

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 后续窗口继续确认 hermes 越界 bad (fid 52e1ddb6) 是否持续与主链隔离 (host 分离保持)。