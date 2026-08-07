# R1025 cc2 NOP inspection round

- 日期: 2026-08-07
- 类型: NOP 巡检轮 (不改码, 只记数据)
- 判定: 主链 SR=100% + 专属错误 0 rows + fallback 0% → 无优化需求, 不改码

## 数据摘要 (live 复核 + 注入轮前链)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **108/108 = 100% SR, 0 bad** | ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** | ✅ |
| nv_requests 总 bad (非 200) | 4 条 (502), 全属 hermes, 主链 0 | ✅(主链) |
| 30min cc_requests | 109 request, fallback 0 次 (0.0%) | ✅ |
| 容器 | nv_gw/cc4101 Up 13h, dsv4p_nv40066 Up 2d, /health 全 200 | ✅ |

## 错误归属 (live `SELECT caller,error_type,status`)

- 本轮 window 内 nv_requests 总 bad = 4 条 (status 502):
  - `hermes | NVStream_IncompleteRead`
  - `hermes | all_tiers_exhausted`
  - `hermes | stream_absolute_cap`
  - `hermes | zombie_empty_completion`
- 全部经 caller 字段判定属 hermes 越界宿主, 与 cc2 主链 host 分离干净, 无泄漏。

## per-key tier 分析

- 各 key `pexec_success` 20-24, 偶发 `NVCFPexecRemoteDisconnected` (key0=1, key1=3, key2=1, key3=2, key4=4)
  + key2 `NVCFPexecTimeout` ×1 + key0/key4 `empty_200` ×1。
- 全被 multi-key round-robin + buffer (attempt=1 大多成功, 偶发 attempt=2 吸收) 吸收, 未穿透 caller。

## 判断

cc2 主链路连续第 **133** 轮 (R893-R1025) 100% SR 干净, 主链专属错误 0 rows。
fallback 0 次 (0.0%), 无新 cc2 主链错误类, 无持久 key 疲劳。
本轮 bad 全属 hermes 越界宿主, 主链无根因可查; 参数处于稳态, 无参数可调。
**不改码。**

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代。
- 后续窗口继续确认 hermes 越界 bad (502) 是否持续与主链隔离 (caller JOIN)。