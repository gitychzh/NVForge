# R1039 cc2 NOP — cc2 primary 100% clean (110/110), scoped errors 0; bad 2 hermes (NVStream_IncompleteRead/zombie_empty_completion); fallback 0 (0/110); 147th clean round (R893-R1039)

日期: 2026-08-07 CST
性质: NOP 巡检轮 (不改码)

## 结论
cc2 主链路 (caller=cc4101-primary) 连续第 **147** 轮 100% SR 干净 (R893-R1039)。
主链专属错误 0 rows, fallback 0 次。本轮 2 bad 全属 **hermes** 越界宿主, 与主链 host 分离干净。

## 数据 (live 复核 2026-08-07 + 注入轮前链路分析 17:42 CST)
- 30min cc4101-primary (主 nv_gw:40006) = **110/110 全 200 = 100% SR, 0 bad**
  (live `SELECT caller,status,count(*) ... WHERE caller='cc4101-primary'`: cc4101-primary|200|110)。
- 主链专属错误 (caller=cc4101-primary, status!=200) = **0 rows**。
- nv_requests 总 bad = 2 条 (NVStream_IncompleteRead ×1 + zombie_empty_completion ×1, 全 caller 160/162=98.8%),
  经 live `SELECT caller,error_type ... WHERE status!=200 GROUP BY` 判定全属 **hermes**。
- 30min cc_requests = 110 request, fallback **0 次 (0.0%), SR=100.0%**。
- nv_tier_attempts per-key: pexec_success 为主 (k0=23/k1=19/k2=27/k3=21/k4=22), 偶发 k3 NVCFPexecRemoteDisconnected ×1,
  被 multi-key round-robin + func_health + buffer 吸收, 未穿透 caller。
- buffer 日志: 无 BUFFER-/WAIT- 重试 (主链请求 1 attempt 成功 flush)。
- 容器: nv_gw Up 14h, cc4101 Up 14h, dsv4p_nv40066 Up 2d, /health 40006/4101/40066 全 200。

## 关键判断
连续 147 轮稳态。主链 110/110 全 200, 专属错误 0 行, fallback 0。
本轮 2 bad 全属 hermes 越界, 主链无根因可查; 参数处于稳态, 无可调。
**不改码**: 主链 SR 100% + 专属错误 0 + storm 完全吸收瞬态错误。