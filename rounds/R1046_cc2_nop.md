# R1046 cc2 NOP — cc2 primary 100% clean (105/105), scoped errors 0; bad 4 hermes (zombie_empty_completion×3/NVStream_IncompleteRead×1); fallback 0 (0/106); 154th clean round (R893-R1046)

日期: 2026-08-07 CST
性质: NOP 巡检轮 (不改码)

## 结论
cc2 主链路 (caller=cc4101-primary) 连续第 **154** 轮 100% SR 干净 (R893-R1046)。
主链专属错误 0 rows, fallback 0 次。本轮 4 bad 全属 **hermes** 越界宿主, 与主链 host 分离干净。

## 数据 (live 复核 2026-08-07 18:1x CST + 注入轮前链路分析 18:11 CST)
- 30min cc4101-primary (主 nv_gw:40006) = **105/105 全 200 = 100% SR, 0 bad**
  (live `SELECT caller,status,count(*) WHERE caller='cc4101-primary'`: cc4101-primary|200|105)。
- 主链专属错误 (caller=cc4101-primary, status!=200) = **0 rows**。
- nv_requests 总 bad = 4 条: zombie_empty_completion ×3 + NVStream_IncompleteRead ×1,
  live `SELECT caller,error_type,count(*) WHERE status!=200 GROUP BY 1,2` 判定全属 **hermes** 越界宿主
  (hermes|zombie_empty_completion|502|3, hermes|NVStream_IncompleteRead|502|1)。
- 30min 按模型总 SR dsv4f0731_nv = 98.0% (193/197), 差异 4 条 bad 全属 hermes。
- 30min cc_requests = **0 次 fallback (0.0%)**, 主链 106/106 全 200 (live total=106, ok=106, sr=100.0)。
- nv_tier_attempts (30min glm5_2_nv 层): 本轮 live 查询 0 rows — 主链首代=dsv4f0731_nv,
  自有流量不落 glm5_2_nv tier 层; 注入分析曾见 k2 瞬态 NVCFPexecRemoteDisconnected ×1 (偶发不累计)。
- buffer 日志 (docker logs nv_gw --since 30m): 无 buffer/wait/keymanager 日志 = 全部 cc4101-primary 请求
  attempt=1 直接 success flush (不必经历 buffer 重试)。buffer 零吸收需要。
- 容器: nv_gw Up 15h, cc4101 Up 14h, /health 40006/4101 全 200。当前首代模型 dsv4f0731_nv, 无 tier 降级。

## 关键判断
连续 **154** 轮稳态 (R893-R1046)。主链 105/105 全 200, 专属错误 0 行, fallback 0 (0.0%), buffer 零重试。
本轮 window 内混入 hermes 越界 4 bad (zombie×3 + NVStream×1), live JOIN 按 caller 判定全属 hermes,
与主链 host 分离干净; 主链无根因可查; 参数处于稳态, 无可调。
**不改码**: 主链 SR 100% + 专属错误 0 + fallback 0 + buffer 零重试, 无优化需求。

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 持续确认 hermes 越界 bad (zombie_empty_completion/NVStream_IncompleteRead/502) 与主链 host 分离 (caller JOIN)。
- 关注偶发 RemoteDisconnected 是否演成持久疲劳 (若单 key 连续多轮 100% 失败再考虑 KEY_FID_BIND 换 fid)。