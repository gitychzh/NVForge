# R1040 cc2 NOP — cc2 primary 100% clean (107/107), scoped errors 0; bad 4 hermes (zombie_empty_completion×3/NVStream_IncompleteRead×1); fallback 0 (0/103); 148th clean round (R893-R1040)

日期: 2026-08-07 CST
性质: NOP 巡检轮 (不改码)

## 结论
cc2 主链路 (caller=cc4101-primary) 连续第 **148** 轮 100% SR 干净 (R893-R1040)。
主链专属错误 0 rows, fallback 0 次。本轮 4 bad 全属 **hermes** 越界宿主, 与主链 host 分离干净。
buffer 正常吸收 1 次 k4 execute_failed (req=9efa4674 attempt1→attempt2 成功)。

## 数据 (live 复核 2026-08-07 17:47 + 注入轮前链路分析 17:46 CST)
- 30min cc4101-primary (主 nv_gw:40006) = **107/107 全 200 = 100% SR, 0 bad**
  (live `SELECT caller,status,count(*) WHERE caller='cc4101-primary'`: cc4101-primary|200|107)。
- 主链专属错误 (caller=cc4101-primary, status!=200) = **0 rows**。
- nv_requests 总 bad = 4 条 (zombie_empty_completion ×3 + NVStream_IncompleteRead ×1, 全 caller 157/157=100% 基础)/hermes,
  经 live `SELECT caller,error_type,count(*) WHERE status!=200 GROUP BY 1,2` 判定全属 **hermes** 越界宿主。
- 30min 总 SR dsv4f0731_nv = 97.5% (153/157), 差异全来自 hermes 4 条 bad。
- 30min cc_requests = 103 request, fallback **0 次 (0.0%), SR=100.0%**。
- nv_tier_attempts per-key: pexec_success 为主 (k0=22/k1=18/k2=24/k3=19/k4=20), 偶发 NVCFPexecRemoteDisconnected ×1 (k2)+×1 (k3),
  被 multi-key round-robin + func_health + buffer 吸收, 未穿透 caller。
- buffer 日志: 主链 req=9efa4674 attempt1 失败 (k4 execute_failed, all_keys_exhausted=True) → 5s backoff → attempt2 success_tool_call
  (flush 6679b, elapsed=45s)。buffer 按设计成功吸收瞬态 k4 失败。
- 容器: /health 40006/4101/40066 全 200 (nv_gw Up 19h, cc4101 Up 14h)。

## 关键判断
连续 148 轮稳态。主链 107/107 全 200, 专属错误 0 行, fallback 0。
本轮 4 bad 全属 hermes 越界 (zombie×3 + NVStream×1), 主链无根因可查; 参数处于稳态, 无可调。
buffer 正常吸收瞬态 key 失败 (execute_failed→retry→success), 无缓冲耗尽。
**不改码**: 主链 SR 100% + 专属错误 0 + buffer 完全吸收瞬态错误。