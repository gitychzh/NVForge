# R1049 cc2 NOP — cc2 primary 100% clean (107/107), scoped errors 0; bad 3 hermes (zombie_empty_completion×2/NVStream_IncompleteRead×1); fallback 0 (0/107); 157th clean round (R893-R1049)

日期: 2026-08-07 CST
性质: NOP 巡检轮 (不改码)

## 结论
cc2 主链路 (caller=cc4101-primary) 连续第 **157** 轮 100% SR 干净 (R893-R1049)。
主链专属错误 0 rows, fallback 0 次。本轮 3 bad 全属 **hermes** 越界宿主, 与主链 host 分离干净。

## 数据 (live 复核 2026-08-07 CST + 注入轮前链路分析 18:22 CST)
- 30min cc4101-primary (主 nv_gw:40006) = **107/107 全 200 = 100% SR, 0 bad**
  (live `SELECT caller,status,count(*) WHERE caller='cc4101-primary'`: cc4101-primary|200|107)。
- 主链专属错误 (caller=cc4101-primary, status!=200) = **0 rows**。
- nv_requests 总 bad = 3 条: zombie_empty_completion ×2 + NVStream_IncompleteRead ×1,
  live `SELECT caller,error_type,status,count(*) WHERE status!=200 GROUP BY 1,2,3` 判定全属 **hermes** 越界宿主
  (hermes|zombie_empty_completion|502|2, hermes|NVStream_IncompleteRead|502|1)。
- 30min 按模型总 SR dsv4f0731_nv = 98.5% (198/201), 差异 3 条 bad 全属 hermes。
- 30min cc_requests = **0 次 fallback (0.0%)**, 主链 107/107 全 200 (live total=107, fb=0)。
- nv_tier_attempts (30min 注入): k0-k4 全 pexec_success (22/21/20/22/23) — 主链首代=dsv4f0731_nv,
  无 tier 层错误, 无 key 疲劳。
- buffer 日志 (注入+manual): 全 cc4101-primary 请求 attempt=1 verdict=success_tool_call → FLUSH
  (多条样例 7-13s elapsed), buffer 零吸收需要, 0 重试 0 耗尽。
- 容器: nv_gw Up 15h, cc4101 Up 14h, nv_gw_stable Up 5d, /health 40006/4101/40066 全 200。
  当前首代模型 dsv4f0731_nv, 无 tier 降级。

## 关键判断
连续 **157** 轮稳态 (R893-R1049)。主链 107/107 全 200, 专属错误 0 行, fallback 0 (0.0%), buffer 零重试。
本轮 window 内混入 hermes 越界 3 bad (zombie×2 + NVStream×1), live JOIN 按 caller 判定全属 hermes,
与主链 host 分离干净; 主链无根因可查; 参数处于稳态, 无可调。
**不改码**: 主链 SR 100% + 专属错误 0 + fallback 0 + buffer 零重试, 无优化需求。

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 持续确认 hermes 越界 bad (zombie_empty_completion/NVStream_IncompleteRead/502) 与主链 host 分离 (caller JOIN)。
- 关注偶发 RemoteDisconnected 是否演成持久疲劳 (若单 key 连续多轮 100% 失败再考虑 KEY_FID_BIND 换 fid)。