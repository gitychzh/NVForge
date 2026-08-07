# R1045 cc2 NOP — cc2 primary 100% clean (106/106), scoped errors 0; bad 4 hermes (zombie_empty_completion×3/NVStream_IncompleteRead×1); fallback 0 (0/106); 153rd clean round (R893-R1045)

日期: 2026-08-07 CST
性质: NOP 巡检轮 (不改码)

## 结论
cc2 主链路 (caller=cc4101-primary) 连续第 **153** 轮 100% SR 干净 (R893-R1045)。
主链专属错误 0 rows, fallback 0 次。本轮 4 bad 全属 **hermes** 越界宿主, 与主链 host 分离干净。
nv_tier_attempts 非成功 1 row (k2 瞬态 NVCFPexecRemoteDisconnected ×1 次), 主链请求全 1 attempt success flush。

## 数据 (live 复核 2026-08-07 18:0x CST + 注入轮前链路分析 18:07 CST)
- 30min cc4101-primary (主 nv_gw:40006) = **106/106 全 200 = 100% SR, 0 bad**
  (live `SELECT caller,status,count(*) WHERE caller='cc4101-primary'`: cc4101-primary|200|106)。
- 主链专属错误 (caller=cc4101-primary, status!=200) = **0 rows**。
- nv_requests 总 bad = 4 条 (zombie_empty_completion ×3 + NVStream_IncompleteRead ×1),
  live `SELECT caller,error_type,count(*) WHERE status!=200 GROUP BY 1,2` 判定全属 **hermes** 越界宿主。
- 30min 按模型总 SR dsv4f0731_nv = 97.8% (182/186), 差异 4 条 bad 全属 hermes。
- 30min cc_requests = **0 次 fallback (0.0%)**, 主链 106/106 全 200 (live total=106, ok=106, sr=100.0)。
- nv_tier_attempts per-key: 非成功 **1 row** (k2 NVCFPexecRemoteDisconnected ×1 次, 瞬态不累计),
  其余 k0-k4 全 pexec_success (24/22/20/19/21)。与历史偶发模式 (R1040-R1044) 一致, 非持久 key 疲劳。
- buffer 日志 (docker logs nv_gw --since 30m): 无 buffer/wait/keymanager 日志 = 全部 cc4101-primary 请求
  attempt=1 直接 success flush (不必经历 buffer 重试)。buffer 零吸收需要。
- 容器: nv_gw Up 19h, cc4101 Up 14h。当前首代模型 dsv4f0731_nv, 无 tier 降级。

## 关键判断
连续 **153** 轮稳态 (R893-R1045)。主链 106/106 全 200, 专属错误 0 行, fallback 0 (0.0%), buffer 零重试。
本轮 window 内仍混入 hermes 越界 4 bad (zombie×3 + NVStream×1), 主链无根因可查; 参数处于稳态, 无可调。
tier 层 k2 偶发 RemoteDisconnected ×1 (与上轮 R1040-R1044 一致的瞬态模式, key 恢复正常后无续错),
主链请求全 1 attempt success, buffer 零吸收 — 链路处于健康状态。
**不改码**: 主链 SR 100% + 专属错误 0 + fallback 0 + buffer 零重试, 无优化需求。

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 后续窗口继续确认 hermes 越界 bad (zombie_empty_completion/NVStream_IncompleteRead/502) 是否持续与主链隔离 (caller JOIN)。
- 关注 k2 偶发 RemoteDisconnected 是否演变成持久疲劳 (若单 key 连续多轮 100% 失败再考虑 KEY_FID_BIND 换 fid)。