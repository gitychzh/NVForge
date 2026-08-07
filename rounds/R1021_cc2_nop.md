# R1021 — cc2 NOP 巡检轮 (不改码)

**轮次**: R1021 | **日期**: 2026-08-07 | **类型**: NOP (主链连续第 129 轮 100% 干净)

## 判定
**NOP**: cc2 主链路 cc4101-primary 连续第 129 轮 (R893-R1021) 100% SR 干净,
主链专属错误 0 rows, fallback 0 次, 无新错误类, 无 key 疲劳. **不改码.**

## 依据 (live 复核 2026-08-07 ~16:47 CST + 注入轮前链路分析)

### 注入轮前链路分析 (2026-08-07 16:35 CST)
- 30min 链路总览: `cc4101-primary|dsv4f0731_nv|200|116`, `hermes|dsv4f0731_nv|200|16`, `hermes|dsv4f0731_nv|502|5`.
- 30min 按模型: `dsv4f0731_nv SR=96.4% (132/137)`, 主链 116/116 全 200 无 bad.
- 错误分类 (status!=200): `NVStream_IncompleteRead|2`, `all_tiers_exhausted|2`, `stream_absolute_cap|1`— 全属 hermes.
- nv_tier_attempts per-key: 各 key 大量 `pexec_success` (22-24), 偶发 `NVCFPexecRemoteDisconnected` (2-3/key)
  与 `NVCFPexecTimeout` (1/key), 全被 buffer 吸收, 未穿透 caller.
- fallback (cc_requests 30min): **0 次 / 0.0%** (2021 request).
- 无 buffer/WaitQueue/cooldown 异常日志 (buffer attempt=1 全 success).

### live 复核 (16:47 CST)
- `SELECT caller,status,count(*) ... caller='cc4101-primary'` → **117/117 = 100% SR, 0 bad**.
- `SELECT caller,error_type,status ... status!=200` → 30min 内全部 bad 全属 hermes
  (NVStream_IncompleteRead 2 / all_tiers_exhausted 2 / stream_absolute_cap 1, 均 502), **主链 0**.
- cc_requests 30min = 2021 request, fallback_triggered = **0** (0.0%).
- /health: 40006 nv_gw 200, 4101 cc4101 200, 40066 dsv4p 200. **全 200**.
- 容器: nv_gw Up 13h, cc4101 Up 13h, dsv4p_nv40066 Up 2d, nv_gw_stable Up 5d.
- buffer 日志: 多请求 attempt=1 verdict=success_tool_call, elapsed 6-9s, flushing 全 success, 无 attempt>1.

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **117/117 = 100% SR, 0 bad** (live) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| nv_requests 总 bad (非 200) | 5 条 (502), 全属 hermes, 主链 0 | ✅(主链) |
| 30min cc_requests | 2021 request, fallback 0 次 (0.0%) | ✅ |
| 容器 | nv_gw/cc4101 Up 13h, dsv4p Up 2d, /health 全 200 | ✅ |

## 关键判断
cc2 主链路连续第 **129** 轮 (R893-R1021) 100% SR 干净, 主链专属错误 0 rows.
本轮 5 条 bad (502) 全属 hermes 越界宿主 (NVStream_IncompleteRead 2 / all_tiers_exhausted 2 / stream_absolute_cap 1),
经 caller 铁证与主链 host 分离完全干净 — 主链 117/117 全 200.
fallback 0 次 (0.0%), 无新 cc2 主链错误类, 无持久 key 疲劳.
multi-key round-robin + func_health + buffer (attempt=1 全成功, elapsed 6-9s) 完全吸收瞬态错误
(偶发 RemoteDisconnected/Timeout), 未穿透到 caller, 已达稳态.
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②本轮 bad 全属 hermes 越界, 主链无根因可查;
③参数处于稳态, 无参数可调.

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动.
- 后续窗口继续确认 hermes 越界 bad (502) 是否持续与主链隔离 (caller JOIN).

## 容器健康
- nv_gw Up 13h, cc4101 Up 13h, dsv4p_nv40066 Up 2d; /health 40006/4101/40066 全 200.
- 配置快照: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, nv_gw nv_default_model=glm5_2_nv,
  NVU_DISABLE_MS_FALLBACK=0, NVU_BUFFER_MAX_RETRIES=5, KeyManager 429 120s-600s 退避,
  ProbeWorker 15s, WaitQueue max 120s, nv_breaker mid-stream 软挂→OPEN.
  deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle. ms_gw fallback 保持不禁用.