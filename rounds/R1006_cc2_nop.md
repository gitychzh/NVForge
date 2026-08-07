# R1006 cc2 NOP inspection — main chain 100% clean (110/110), scoped errors 0 rows; bad 5 hermes; fallback 0

> cc2 (HM2 nv_gw) 自优化巡检轮。**不改码**。连续第 114 轮 (R893-R1006) 主链干净。

## 结论 (NOP)

| 指标 | 值 | 状态 |
|---|---|---|
| 30min cc4101-primary (主 nv_gw:40006) | **110/110 = 100% SR, 0 bad** | ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** | ✅ |
| nv_requests 总 bad (非 200) | 5 条, 全属 hermes (dsv4f0731_nv), 主链 0 | ✅(主链) |
| fallback 次数 (cc_requests 30min) | **0** (120 total) | ✅ |
| buffer 停滞 (BUFFER-/WAIT-) | 无, 全 attempt=1 成功 (1-14s) | ✅ |
| 容器 | nv_gw Up 12h, cc4101 Up 12h, dsv4p Up 2d, health 全 200 | ✅ |

## 依据

- **按 caller×status**: `cc4101-primary|dsv4f0731_nv|200|110` — 主链 110 请求全 200。
- **scoped 错误 (caller≠200)**: 0 rows (cc4101-primary 无任何错误)。
- **总 bad = 5 条 (4 all_tiers_exhausted + 1 zombie_empty_completion)**, 经归属判定全属 **hermes**
  (dsv4f0731_nv 502, 越界宿主 fid 52e1ddb6 泄漏) — 与主链 host 分离保持。
- **fallback = 0**: 30min cc_requests 120 total, fallback_triggered 0, primary 全 200。
- **buffer 日志**: 全 attempt=1/5 一次成功 (elapsed 1-14s), verdict 全 success_text/success_tool_call,
  tool 均 id=True args=True, 无 BUFFER-/WAIT- 停滞。
- **主链首代模型 = dsv4f0731_nv** (config PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv)。

## 判断

主链连续第 **114** 轮 100% SR 干净 (R893-R1006), 主链专属错误 0 rows, fallback 0。
本轮 5 条 bad 全属 hermes 越界宿主 (fid 52e1ddb6 泄漏), 与主链 host 分离保持, 主链无根因可查。
buffer + multi-key round-robin + func_health 完全吸收瞬态错误, 无参数可调。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②bad 全属 hermes 越界非主链;
③ 链路已达稳态 (attempt=1 全成功)。

## 下一步

- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 后续窗口继续确认 hermes 越界 bad 与主链 host 隔离是否持续。