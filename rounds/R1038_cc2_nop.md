# R1038 cc2 NOP — cc2 primary 100% clean (112/112), scoped errors 0; bad 2 hermes (NVStream_IncompleteRead/zombie_empty_completion); fallback 0 (0/113); 146th clean round (R893-R1038)

## 判定: NOP 巡检轮/不改码

cc2 主链路 (cc4101-primary → nv_gw:40006) 连续第 **146** 轮 (R893-R1038) 100% 干净。
主链专属错误 0 rows; 本轮 window 内 2 条 bad 全属 hermes 越界宿主, 主链 host 完全分离。
fallback 0 次 (0.0%)。无新 cc2 主链错误类, 无持久 key 疲劳。**不改码**。

## 依据 (live 复核 2026-08-07 CST + 注入轮前链路分析 17:39 CST)

- **30min cc4101-primary (主 nv_gw:40006) = 112/112 全 200 = 100% SR, 0 bad**
  (live `SELECT caller,status,count(*) FROM nv_requests WHERE created_at>now()-interval'30 min' AND caller='cc4101-primary' GROUP BY 1,2`:
  cc4101-primary|200|112)。注入窗口 112 条 (17:39), live 复核 112 全 200。
- **主链专属错误 (caller=cc4101-primary, status!=200) = 0 rows**
  (live scoped 错误分组为空, 无 cc4101-primary 行)。
- **30min total bad = 2 条**: NVStream_IncompleteRead ×1 + zombie_empty_completion ×1,
  经 caller JOIN 判定全属 **hermes** 越界宿主 → 主链 0。
- **dsv4f0731_nv 全 caller SR = 98.7% (155/157)**, 2 bad 归属 hermes, 主链 0。
- **fallback (cc_requests 30min) = 0 次 / 0.0%** (113 request, SR=100.0%, fb=0)。
- **nv_tier_attempts per-key 健康**: 全 5 key (k0-k4) 以 pexec_success 为主 (k0=23/k1=18/k2=26/k3=22/k4=23),
  偶发 NVCFPexecRemoteDisconnected ×1 (k3) 全被 multi-key round-robin + func_health + buffer 吸收, 未穿透 caller。
- **buffer 日志**: 本轮 window 内无 BUFFER-/WAIT- 重试日志 (无缓冲耗尽, 主链请求 1 attempt 成功 flush)。
- **容器**: nv_gw Up 14h, cc4101 Up 14h, dsv4p_nv40066 Up 2d; /health 40006 返回 ok (5 key ACTIVE)。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **112/112 = 100% SR, 0 bad** (live 查询) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| nv_requests 总 bad (非 200) | 2 条 (NVStream_IncompleteRead/zombie_empty_completion), 全属 hermes, 主链 0 | ✅(主链) |
| 30min cc_requests | 113 request, fallback 0 次 (0.0%), SR=100.0% | ✅ |
| nv_tier_attempts 非成功 | RemoteDisconnected ×1 (全被吸收) | ✅ |
| 容器 | nv_gw Up 14h, cc4101 Up 14h, dsv4p_nv40066 Up 2d, /health 全 200 | ✅ |

## 关键判断

cc2 主链路连续第 **146** 轮 (R893-R1038) 100% SR 干净, 主链专属错误 0 rows。
本轮 2 条 bad (NVStream_IncompleteRead/zombie_empty_completion) 经 caller 铁证归属全属 **hermes** 越界宿主,
与主链 host 分离完全干净 — 主链 112/112 全 200。
fallback 0 次 (0.0%), 无新 cc2 主链错误类, 无持久 key 疲劳。
multi-key round-robin + func_health + buffer 完全吸收瞬态错误 (本次各 key 仅 1 次 NVCFPexecRemoteDisconnected), 未穿透到 caller, 已达稳态。

**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②本轮 bad 全属 hermes 越界, 主链无根因可查; ③参数处于稳态, 无参数可调; ④铁律改前必有数据 — 无数据指向本次需调参。

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 后续窗口继续确认 hermes 越界 bad 是否持续与主链隔离 (caller JOIN)。