# R994 — cc2 NOP 巡检轮 (不改码)

> 日期: 2026-08-07
> 结果: **NOP** — cc2 主链路连续第 **102** 轮 (R893-R994) 100% 干净
> 判定: cc4101-primary = **117/117 = 100% SR, 0 bad**; 唯一 bad 全属 hermes 越界; fallback 0

## 结论一句话

cc2 主链 (nv_gw:40006 → dsv4f0731_nv) 在 30min 窗口 117/117 全 200, 主链专属错误 **0 rows**, fallback 0 次;
唯一 2 个 bad (all_tiers_exhausted ×2) 100% 属 caller=hermes (宿主越界容器), 与主链 host 分离。
**不改码, NOP 巡检。**

## 本轮数据 (live 复核 2026-08-07 + 注入轮前链路分析)

| 指标 | 值 | 状态 |
|---|---|---|
| cc4101-primary (主 nv_gw:40006) | **117/117 = 100% SR, 0 bad** (live re-pull) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| 唯一 bad (非 200) | 2 条, 全 caller=hermes 线 (all_tiers_exhausted ×2) | ⚠️ 越界 |
| bad caller 归属 | 100% hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests 30min) | 0 次 (118 req 全未 fb) | ✅ |
| 30min 总模型 SR | dsv4f0731_nv = **98.5% (130/132)** (bad 2 全 hermes) | ✅ |
| buffer/wait | 全 attempt=1 一次成功, flush 1.4–13s, 无 WAIT 停滞 | ✅ |
| 容器 | nv_gw Up, cc4101 Up, health 全 200 | ✅ |

## 依据 (注入轮前链路分析 + live 复核)

- 30min nv_requests cc4101-primary = **117/117 全 200** (live re-pull:
  `SELECT caller,status,error_type,count(*) GROUP BY` → cc4101-primary=200|117, 无其他 status)。
- bad 分组 (live by caller×err_type): 仅 `hermes | all_tiers_exhausted | 2` — 100% hermes 线
  (fid 52e1ddb6 宿主越界容器, 2026-08-05 起持续 host 分离)。本次窗口无 zombie_empty_completion。
- cc_requests 30min: total 118, ok=118, fb=0, 全未 fallback_triggered。
- buffer 日志: NV-BUFFER-START/VARDICT/SUCCESS 全 attempt=1 verdict=success_tool_call, flush 1650b~15.9KB
  elapsed 1.4~13s, 一 try 即成功; 无 BUFFER-ATTEMPT>1, 无 WAIT-STALL, 无 all_tiers 泄漏。
- health: 40006/4101 全 200; nv_gw / cc4101 皆 Up (live curl)。

## 本轮改动
- 无 (NOP)。主链 SR 100% + 专属错误 0 行, 多 key round-robin (dsv4f0731_nv 为首) + func_health + buffer
  达稳态, 瞬态 key 错误全被吸收, 无参数可调。

## 关键判断
cc2 主链路连续第 **102** 轮 (R893-R994) 100% SR 干净, 主链专属错误 0 rows。
唯一 2 个 bad 100% 属 hermes 线 (caller=hermes + 已知坏 fid 52e1ddb6 越界容器), fallback 0 次,
无新 cc2 主链错误类, 无持久 key 疲劳。**不改码。**

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 继续监控 hermes bad (fid 52e1ddb6) 是否真正与主链 host 隔离 (R897 起持续隔离保持)。