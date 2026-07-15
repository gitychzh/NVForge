# HM2 Optimize HM1 — Round R1424

## 触发分析
cron脚本输出: "这是我提交的, 不触发"
- 最新commit author = opc2_uname (HM2)
- HM1本地git log停留在R1206 (217轮落后于HM2 R1423)
- 脚本正确检测到自提交并标记"不触发"
- cron仍被派遣 — 误触发(false trigger, double-dispatch, 580th chain of R1133)

## 数据收集 (改前必有数据)

### 容器状态
- nv_gw: Up ~2h (started 2026-07-15T03:25:06Z, healthy)
- Compose md5: `59dc3c54c49324859d1d31e7e422b31b` (稳定, 与R1423一致)

### 6h DB数据
- 37req/24OK/13fail (64.9% SR)
- zombie_empty_completion: 12 (glm5_2_nv: 7× integrate, dsv4p_nv: 5× pexec)
- all_tiers_exhausted: 2 (dsv4p_nv)
- 0 tier_attempts — 无key cycling
- ms_gw: 未触发 (0 fallback)

### 按模型
- glm5_2_nv: 25req/18OK/7zombie (72.0% SR, integrate, avg 8579ms)
- dsv4p_nv: 12req/6OK/5zombie+1ATE (50.0% SR, pexec, avg 25084ms)

### 24h全景
- 175req/131OK/44fail (74.9% SR)
- 35 zombie + 10 ATE (24h)
- ATE分布: 14日18:00(8) + 14日06:00(8) 为主要集中时段, 其余零星

### Log分析
- zombie=NVCF content-filter: 同R1423模式, finish_reason=stop, 字符数不足
- Gateway检测正确: [NV-ZOMBIE-ERROR-CHUNK] sent finish_reason=timeout
- NV-THINKING-TIMEOUT: dsv4p_nv thinking请求正常扩展至66s
- 0 NV-TIER-FAIL, 0 NV-ALL-TIERS, 0 NV-MS-FB, 0 NV-EMPTY-FASTBREAK
- glm5_2_nv integrate全first-attempt成功(无key cycling)
- 0 NVCFPexecTimeout, 0 429, 0 SSLEOF

### 参数状态
- 所有参数已floor/optimal: UPSTREAM=66, BUDGET=205, KEY_COOLDOWN=25, TIER_COOLDOWN=15
- FASTBREAK: PEXEC=1, INTEGRATE=1, EMPTY_200=2
- MS_GW_FALLBACK_TIMEOUT=195, PEER_FALLBACK_TIMEOUT=66
- Per-model: DSV4P_NV=112, GLM5_2_NV=96, MINIMAX_M3_NV=100
- PEER_FB_SKIP_MODELS="" (全启用)
- Compose md5稳定: 59dc3c54 (与R1423一致, 无漂移)

## 决策
**NOP — 零参数改动。**
- 12 zombie_empty_completion = NVCF content-filter (not config-fixable)
- 2 ATE dsv4p_nv = single anomaly, 0 tier_attempts
- 0 NVCFPexecTimeout, 0 429, 0 SSLEOF — 零可优化错误
- glm5_2_nv integrate 100% first-attempt success (0 key cycling)
- 所有参数floor/optimal, 无优化空间
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
