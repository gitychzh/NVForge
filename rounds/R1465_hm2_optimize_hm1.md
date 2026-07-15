# HM2 Optimize HM1 — Round R1465 (NOP)

## 1. 触发分析
- cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 预运行脚本已提交 R1464 (NOP), symlink 正确
- cron 仍被派遣 — 双派遣误触发
- 这是 R1395 链的第 45 次连续误触发 (R1395→R1465)

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态
- 容器: nv_gw (Up About an hour, healthy)
- 容器重启: 2026-07-15T13:09:29Z (HM1 外部循环重启, 与 R1464 的 06:39:45Z 不同)
- compose md5: 45c1f284 (与 R1464 的 3863a7c1 不同 — R1292 模式: 外部循环变更, 环境变量未变)

### 2.2 nv_gw 环境变量 (全部 floor/optimal)
- UPSTREAM_TIMEOUT=66
- TIER_COOLDOWN_S=15
- KEY_COOLDOWN_S=25
- NVU_TIER_BUDGET_DSV4P_NV=66
- NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05
- NVU_EMPTY_200_FASTBREAK=2
- NVU_PEER_FALLBACK_ENABLED=1
- NVU_PEER_FALLBACK_TIMEOUT=66
- NVU_PEER_FB_SKIP_MODELS=
- NVU_FORCE_STREAM_UPGRADE=0
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NV_INTEGRATE_KEY_COOLDOWN_S=0
- NV_INTEGRATE_MODELS=glm5_2_nv

### 2.3 6h 统计数据
- 总计: 42req/19OK/23fail → 45.2%SR
- 错误分布: zombie_empty_completion=14, all_tiers_exhausted=9
- 无 NVStream_IncompleteRead, 0 tier_attempts, 0 fallback

### 2.4 按上游路径
- nv_integrate: 26req/15OK/11fail (57.7%), avg_ttfb=12232ms, avg_dur=12233ms
- nvcf_pexec: 7req/4OK/3fail (57.1%), avg_ttfb=50359ms, avg_dur=50359ms
- NULL (ATE): 9req/0OK/9fail, avg_dur=77567ms

### 2.5 按模型
- glm5_2_nv: 27req/15OK/12fail (55.6%), avg_dur=18712ms
- dsv4p_nv: 15req/4OK/11fail (26.7%), avg_dur=57563ms

### 2.6 zombie 详情
- dsv4p_nv zombie: 3req, avg_input_chars=218535, avg_dur=49159ms (NVCF content-filter, stop+14-29 chars)
- glm5_2_nv zombie: 11req, avg_input_chars=216664, avg_dur=12083ms (NVCF content-filter, stop+28-32 chars)

### 2.7 ATE 详情
- dsv4p_nv ATE: 8req, avg_dur=63867ms (NVCF 504 → all tiers exhausted)
- glm5_2_nv ATE: 1req, avg_dur=187171ms

### 2.8 ms_gw 信号
- 24 total / 20 OK (83.3%)

### 2.9 每小时 SR
- 08:00: 2/1 OK (50%)
- 09:00: 8/4 OK (50%)
- 10:00: 6/2 OK (33.3%)
- 11:00: 6/2 OK (33.3%)
- 12:00: 7/3 OK (42.9%)
- 13:00: 9/5 OK (55.6%)
- 14:00: 4/2 OK (50%)

### 2.10 日志
- 容器日志仅显示 NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK (zombie detection working)
- NV-THINKING-TIMEOUT 正常触发 (dsv4p_nv thinking requests)
- 无 crash, 无 OOM, 无 panic

## 3. 决策: NOP

### 3.1 原因
1. 所有参数已 floor/optimal, 无可调整空间
2. zombie=NVCF content-filter (input_chars 216K+, stop+12-36 chars) — 不可配置修复
3. ATE=NVCF 504 (all_tiers_exhausted) — 上游问题, 非本地配置可解
4. 0 tier_attempts — 键循环干净
5. 0 fallback — 无回退触发
6. ms_gw 24/20 OK — 回退正常运行
7. Gateway zombie detection 正确工作

### 3.2 外部循环变更
- compose md5 从 3863a7c1 → 45c1f284 (R1292 模式)
- 容器重启 06:39:45Z → 13:09:29Z (HM1 外部循环重启)
- env vars 完全一致 — 无参数变更

## 4. HM1 状态
- HM1 git log: 停留在 R1206 (259 轮落后)
- 无新提交, 无新配置

## 5. 操作
- 零参数修改
- 零 compose 修改
- 零容器重启
## ⏳ 轮到HM1优化HM2
