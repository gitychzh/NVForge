# R1007 — cc2 NOP 巡检轮

> 结论: **不改码**。cc2 主链路 (cc4101-primary → nv_gw:40006, dsv4f0731_nv 首代)
> 30min = **105/105 = 100% SR, 0 bad**, 主链专属错误 **0 rows**, fallback **0 次**。
> 连续第 **115** 轮 (R893-R1007) 100% 干净。

## 数据 (live re-pull 2026-08-07 15:44 CST)

| 指标 | 值 | 归属 |
|---|---|---|
| cc4101-primary (主 nv_gw:40006) 30min | **105/105 = 100% SR, 0 bad** | cc2 主链 ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** | cc2 主链 ✅ |
| nv_requests 总 bad (非 200) | 4 条, 全属 hermes (dsv4f0731_nv) | hermes, 非主链 |
| 错误分类 | all_tiers_exhausted ×3 + zombie_empty_completion ×1 | 全 hermes |
| cc_requests 30min fallback | 106 total, **fb=0** | ✅ |
| buffer 日志 | 全 attempt=1 一次成功 (6-8s), verdict=success_tool_call | ✅ |
| health | nv_gw/cc4101/dsv4p 全 200 | ✅ |

## 判定

### 1. 主链 100% 干净, 无优化需求
cc4101-primary 105/105 全 200 = **100% SR**, 主链专属错误分组为空 (scoped 0 rows)。
这是连续第 115 轮 100% SR。

### 2. 本轮 4 条 bad 全属 hermes (越界宿主泄漏)
scoped 错误分组铁证: `caller=hermes` 独占 all_tiers_exhausted ×3 + zombie_empty_completion ×1。
这是已知的 hermes 越界宿主 (fid 52e1ddb6 泄漏) 问题, 与 cc2 主链 host 完全分离 (memory:
bad-fid-52e1ddb6-leaks-into-dsv4f0731-rotation)。归属判定用 request_id/caller JOIN, 非主链。

### 3. fallback 0 次 + buffer attempt=1 全成功 = 无参数可调
multi-key round-robin + func_health + buffer (全 attempt=1 一次 6-8s 成功) 完全吸收瞬态
NVCFPexecRemoteDisconnected/Timeout, 稳态已达成。deadline 链 90s×5=450s < 470s cc4101 不触发。

### 不改码理由
①主链 100% SR + 专属错误 0 行, 无优化目标; ②本轮 bad 全属 hermes 越界, 主链无根因可查;
③buffer + multi-key RR 已达稳态, 无参数可调 (铁律 1: 改前必须有数据驱动, 此处无数据支撑改动)。

## 验证
- 30min nv_requests cc4101-primary = 105/105 (0 bad)。
- 主链专属错误分组 = 空 (0 rows)。
- 4 条非 200 经 scoped 分组确认归属 hermes (caller=hermes), 非 cc2 主链。
- cc_requests primary 106/106, fallback 0 次。
- buffer 日志: 全 attempt=1 一次成功, 无 BUFFER-/WAIT- 停滞。
- health: 4101/40006/40066 全 200。

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 首代, 无参数改动。
- 继续确认 hermes 越界 bad 与主链 host 分离保持 (后续窗口隔离性复核)。