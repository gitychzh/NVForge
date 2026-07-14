# HM2 Optimize HM1 — Round R1317

## 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- 预运行脚本已提交 R1316 NOP，symlink 正确指向 rounds/R1316_hm2_optimize_hm1.md
- git status 干净 — 无待修复项
- 本次为 false trigger，double-dispatch 模式
- 31st consecutive post-R1286 false trigger

## 数据收集 (改前必有数据)

### 容器状态
- nv_gw: Up 5 hours (healthy), 重启于 2026-07-13T22:14:51Z
- Compose md5: 6e1b58bc70eca49e500e3034b08376d9 (stable, 同 R1316)

### 6h 总体
- 58 req, 51 OK, 7 fail, 87.9% SR
- 全部流量: glm5_2_nv integrate (100%)
- dsv4p_nv: 0 traffic
- kimi_nv: 0 traffic

### 错误分类
- zombie_empty_completion: 7 (全部 7 个失败)
- 0 all_tiers_exhausted, 0 NVStream_TimeoutError, 0 NVStream_IncompleteRead
- 0 tier_attempts (0 key cycling)
- 0 fallback 触发

### 每小时 SR
- 22:00: 7req/5OK 71.4%
- 23:00: 6req/5OK 83.3%
- 00:00: 6req/5OK 83.3%
- 01:00: 29req/28OK 96.6%
- 02:00: 5req/5OK 100.0%
- 03:00: 5req/3OK 60.0% (最后2个请求 zombie)

### zombie 详情
- glm5_2_nv integrate, avg input_chars=202,159, avg dur=5,009ms
- NVCF content-filter stop + 12 chars output
- 网关正确检测 → 发送 error SSE chunk → 触发 openclaw fallback
- 每个 zombie 在 ~3-7s 内中止，非旧 8min stall

### ms_gw
- 13/13 100% SR

### 容器 env (关键参数)
- UPSTREAM_TIMEOUT=66
- TIER_TIMEOUT_BUDGET_S=205
- TIER_COOLDOWN_S=15
- KEY_COOLDOWN_S=25
- KEY_AUTHFAIL_COOLDOWN_S=60
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_INTEGRATE_THINKING_TIMEOUT_S=90
- NVU_TIER_BUDGET_DSV4P_NV=72
- NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_TIER_BUDGET_MINIMAX_M3_NV=100
- NVU_FORCE_STREAM_UPGRADE=0
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- NVU_MS_GW_FALLBACK_TIMEOUT=195
- NVU_SSLEOF_RETRY_DELAY_S=1.0
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05
- NVU_PEER_FB_SKIP_MODELS=(empty)
- NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms

### nv_gw 日志
- 仅 NV-REQ 行 (glm5_2_nv integrate, tier_chain=['glm5_2_nv'], no fallback, 3model)
- NV-ZOMBIE-EMPTY: 2 occurrences (glm5_2_nv, content_chars=12, input_chars=175K+, finish_reason=stop)
- NV-ZOMBIE-ERROR-CHUNK: 正确发送 content_filter error SSE chunk
- 0 NV-TIER-FAIL, 0 NV-MS-FB, 0 NV-EMPTY-FASTBREAK
- 0 error/warn 日志

## 决策: NOP

### 不可配置修复
- zombie_empty_completion: NVCF 端 content-filter 行为，非代码/配置可修复
- 网关检测+中止正确 (3-7s)，非旧 8min stall
- 所有 7 个失败均�� zombie，无其他错误类型

### 参数状态
- 所有参数已处于 floor/optimal
- UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- 所有 FASTBREAK 参数已优化
- 所有 per-model tier budget 已优化
- NVU_PEER_FB_SKIP_MODELS 空（无模型需要跳过 peer-fb）
- 无参数可调空间

### 历史一致性
- R1316 数据: 59req/52OK 88.1%SR, 7 zombie
- R1317 数据: 58req/51OK 87.9%SR, 7 zombie
- 完全一致的 zombie 模式，无退化，无新错误类型

### 铁律
- 只改 HM1 不改 HM2 — NOP 无违规

## ⏳ 轮到HM1优化HM2
