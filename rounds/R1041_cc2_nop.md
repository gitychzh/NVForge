# R1041 cc2 NOP — cc2 primary 100% clean (105/105), scoped errors 0; bad 4 hermes (zombie_empty_completion×3/NVStream_IncompleteRead×1); fallback 0 (0/106); 149th clean round (R893-R1041)

日期: 2026-08-07 CST
性质: NOP 巡检轮 (不改码)

## 结论
cc2 主链路 (caller=cc4101-primary) 连续第 **149** 轮 100% SR 干净 (R893-R1041)。
主链专属错误 0 rows, fallback 0 次。本轮 4 bad 全属 **hermes** 越界宿主, 与主链 host 分离干净。
nv_tier_attempts 非成功 **0 rows** (30min 无任何 key 错误), buffer 全 request 1 attempt 直接 success flush。

## 数据 (live 复核 2026-08-07 + 注入轮前链路分析 17:50 CST)
- 30min cc4101-primary (主 nv_gw:40006) = **105/105 全 200 = 100% SR, 0 bad**
  (live `SELECT caller,status,count(*) WHERE caller='cc4101-primary'`: cc4101-primary|200|105)。
- 主链专属错误 (caller=cc4101-primary, status!=200) = **0 rows**。
- nv_requests 总 bad = 4 条 (zombie_empty_completion ×3 + NVStream_IncompleteRead ×1),
  live `SELECT caller,error_type,count(*) WHERE status!=200 GROUP BY 1,2` 判定全属 **hermes** 越界宿主。
- 30min 总 SR dsv4f0731_nv = 97.3% (145/149), 差异全来自 hermes 4 条 bad。
- 30min cc_requests = 106 request, fallback **0 次 (0.0%), SR=100.0%** (106/106 ok)。
- nv_tier_attempts per-key: **非成功 0 rows** (30min 无任何 key 错误, 无 RemoteDisconnected/execute_failed,
  比上轮 R1040 的偶发 k2/k3 RemoteDisconnected 更干净)。
- buffer 日志 (docker logs nv_gw --since 30m): 全部 cc4101-primary 请求 attempt=1 verdict=success 直接 flush
  (elapsed 0.9s~12s, 无 backoff 无重试无缓冲耗尽)。buffer 无任何瞬态失败需要吸收。
- 容器: /health 40006/4101/40066 全 200 (nv_gw Up 14h, cc4101 Up 14h, dsv4p_nv40066 Up 2d)。

## 关键判断
连续 149 轮稳态。主链 105/105 全 200, 专属错误 0 行, fallback 0, nv_tier_attempts 0 rows 非成功。
本轮 4 bad 全属 hermes 越界 (zombie×3 + NVStream×1), 主链无根因可查; 参数处于稳态, 无可调。
nv_tier_attempts 0 rows 表明本轮 무key 层瞬态错误 (连多 key round-robin 的触达都没有),
主链请求全 1 attempt success, buffer 零吸收需要 — 链路处于最健康状态。
**不改码**: 主链 SR 100% + 专属错误 0 + tier 层 0 错误 + buffer 零重试, 无优化需求。