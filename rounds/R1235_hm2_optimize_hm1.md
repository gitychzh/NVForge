# HM2 Optimize HM1 — Round R1235

## 0. 触发分析

cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit `0c2e1cd` — author = opc2_uname (HM2 自提交)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch, R884+ pattern)
- HM1 本地 git log 停留在 R1206 (28 轮落后)，未提交任何新内容

## 1. 数据收集 (改前必有数据)

### 6h 总览
- 104req/80OK(76.9%)/24fail — 与 R1233/R1234 完全一致

### 错误分类
- **12× zombie_empty_completion** — NVCF content-filter，代码级 zombie 检测特性，非 config-fixable (R1107)
- **11× all_tiers_exhausted** — ms_gw BrokenPipeError 代码级缺陷，非 config-fixable
- **1× NVStream_IncompleteRead** — 偶发网络抖动

### 按模型
- glm5_2_nv: 96req/77OK(80.2%)，avg_dur 50s (integrate 为主)
- dsv4p_nv: 8req/3OK(37.5%)，avg_dur 55s (pexec 为主)

### 按路径
- nv_integrate: 84req/72OK/12fail, avg_dur 34s
- NULL (ATE): 11req/0OK/11fail, avg_dur 137s
- nvcf_pexec: 9req/8OK/1fail, avg_dur 99s

### tier_attempts (6h)
- glm5_2_nv IntegrateTimeout: 6×, avg 91s, max 93s
- 无其他 tier errors

### 按小时 SR
- 08:00: 31req/22OK(71.0%)
- 09:00: 27req/22OK(81.5%)
- 10:00: 42req/33OK(78.6%)
- 11:00: 4req/3OK(75.0%)

### 最近 10 条请求 (last 10)
- 全部 glm5_2_nv integrate
- 9/10 OK (3-15s)，1× zombie_empty_completion (4.8s)

### ms_gw 信号
- 16 req/0 OK — BrokenPipeError 代码级缺陷 (R1039)，非 config-fixable

### 容器状态
- nv_gw: Up 47 min (healthy)，重启于 10:44 UTC
- tier_chain: ['glm5_2_nv'] (no fallback, 3model) — FALLBACK_GRAPH={} 预期正常
- 0 NV-MS-FB 日志行，0 NV-PEER-FB 日志行
- compose md5: 832ef9ff (R1231 BUDGET 210 已部署)

### 当前参数 (docker exec nv_gw env)
- TIER_TIMEOUT_BUDGET_S=210
- UPSTREAM_TIMEOUT=66
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2
- NVU_TIER_BUDGET_DSV4P_NV=72
- NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- TIER_COOLDOWN_S=15
- KEY_COOLDOWN_S=25
- NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- NVU_MS_GW_FALLBACK_TIMEOUT=180
- NVU_FORCE_STREAM_UPGRADE=0
- MIN_OUTBOUND_INTERVAL_S=0
- NVU_CONNECT_RESERVE_S=0
- NVU_SSLEOF_RETRY_DELAY_S=1.0

## 2. 分析

### 数据与 R1233/R1234 完全一致
- 6h SR 76.9% (104req/80OK/24fail) 三轮完全相同
- 12 zombie_empty_completion: NVCF content-filter 触发 content_chars<50 + finish_reason=stop，网关 zombie 检测正确返回 502 并发送 error SSE chunk → openclaw fallback。3-15s 快速中止 >> 旧版 96s hang。代码级特性，非 config-fixable (R1107)
- 11 all_tiers_exhausted: ms_gw BrokenPipeError 代码级缺陷，ms_gw 0/16 OK (relay killed mid-stream with content already sent to client)。非 config-fixable (R1039)
- 1 NVStream_IncompleteRead: 偶发单点，非系统性

### 所有参数 floor/optimal
- FASTBREAK=1 (pexec+integrate): function-level timeout，已验证 (R997/R709/R731/R961)
- BUDGET=210: UPSTREAM=66 + PEER_FB=66 = 132，BUDGET 210 >> 132 充裕
- UPSTREAM=66: NVCFPexecTimeout max=93s (glm5_2_nv IntegrateTimeout)，但 integrate 有自己的 NVU_INTEGRATE_THINKING_TIMEOUT_S=90，UPSTREAM=66 主要用于 pexec 路径。dsv4p_nv pexec 无 tier_attempts，表明 UPSTREAM 对于 pexec 路径不绑定
- TIER_COOLDOWN_S=15: key-specific empty_200 全键标记最小惩罚 (R1103 revert R1018 18->15)
- NVU_TIER_BUDGET_DSV4P_NV=72: dsv4p_nv per-tier budget +6s for k5 rescue (R1116)
- NVU_TIER_BUDGET_GLM5_2_NV=96: glm5_2_nv per-tier budget 覆盖 integrate timeout
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv (R923)
- NVU_MS_GW_FALLBACK_TIMEOUT=180: ms_gw 超时 generous，但 BrokenPipeError 使 ms_gw fallback 不可能 — BUDGET 210 > ms_gw fallback timeout=180，BUDGET 不是瓶颈 (R1088)

### ms_gw BrokenPipeError 是唯一系统性非 zombie 失败来源
- ms_gw 16 req/0 OK: nv_gw 发送 200+header 后 relay killed mid-stream → TCP 半损坏，无法恢复
- NVU_MS_GW_FALLBACK_TIMEOUT=180 未触发（BUDGET=210 先杀 relay）
- 0 NV-MS-FB 日志行 → ms_gw fallback 从未成功触发
- 代码级缺陷，非 config-fixable

## 3. 决策

**NOP — 零参数变更，零 compose 变更，零容器重启**

理由:
1. Script 输出 "这是我提交的, 不触发" — false trigger confirmed
2. HM1 git 停留在 R1206，28 轮未提交新内容
3. 数据与 R1233/R1234 完全一致 (104req/80OK/24fail)
4. 所有失败为代码级缺陷：zombie_empty_completion (NVCF content-filter) + all_tiers_exhausted (ms_gw BrokenPipeError)
5. 所有配置参数 floor/optimal，无可优化空间
6. compose md5 832ef9ff 未变化

## 4. 验证

无变更需验证。容器正常运行 (Up 47 min healthy)。

## ⏳ 轮到HM1优化HM2
