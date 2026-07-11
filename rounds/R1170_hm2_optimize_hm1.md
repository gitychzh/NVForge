# HM2 Optimize HM1 — Round R1170

## 1. 触发分析

cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发（38th chain of R1133）
- HM1 本地 git log 停留在 R821（349 轮落后）

## 2. HM1 数据收集 (改前必有数据)

### 容器状态
- nv_gw: 正常运行（logs 显示活跃请求），compose md5: 7975939c245761e451a8813852dcb9bf (unchanged)
- 容器未重启，配置与 R1165–R1169 一致

### DB 6h 统计 (created_at >= now() - 6h)
- 35req/13OK(37.1%)/22zombie
- 全部 glm5_2_nv integrate (nv_integrate upstream_type)
- 22x zombie_empty_completion (avg 4.7s, max 12.6s, NVCF content-filter stop+12chars, 164K-169K input)
- 0 fallback (fallback_occurred=f for all 35)
- nv_tier_attempts: 3x 429_integrate_rate_limit (glm5_2_nv)
- dsv4p_nv: 0 traffic 6h, ms_gw: 0 traffic 6h

### 小时分布
| Hour | Total | OK | Fail | SR% |
|------|-------|-----|------|-----|
| 00:00 | 7 | 1 | 6 | 14.3 |
| 01:00 | 4 | 2 | 2 | 50.0 |
| 02:00 | 4 | 2 | 2 | 50.0 |
| 03:00 | 4 | 2 | 2 | 50.0 |
| 04:00 | 2 | 1 | 1 | 50.0 |
| 22:00 | 5 | 1 | 4 | 20.0 |
| 23:00 | 9 | 4 | 5 | 44.4 |

### nv_key_idx 分布
- K1=7, K2=6, K3=6, K4=9, K5=7 — 均匀分布

### 日志分析
- 所有请求: NV-INTEGRATE-SUCCESS on first attempt (1/7 attempt, various keys)
- 全部 zombie: NV-ZOMBIE-EMPTY → NV-ZOMBIE-ERROR-CHUNK (stop+12chars detection correct)
- 无 timeout, 无 empty_200, 无 504, 无 SSLEOF
- 每~30min 一组请求（openclaw 轮询间隔），每组 2 请求：第 1 个 OK (1.6-4.3s)，第 2 个 zombie (3.5-12.6s)

### 当前参数 (docker exec nv_gw env)
| Param | Value | Floor/Optimal |
|-------|-------|---------------|
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor (–5 from R1119) |
| UPSTREAM_TIMEOUT | 66 | validated optimal |
| TIER_TIMEOUT_BUDGET_S | 198 | validated |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor (R1010) |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor (R997) |
| NVU_EMPTY_200_FASTBREAK | 2 | bug-confirmed no-op (R1039) |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv | correct |

## 3. 决策: NOP

### 同 R1165–R1169

所有参数已在地板/最优。zombie_empty_completion 是 NVCF 层面的 content-filter（stop+12chars for 164K-169K input），不是配置可修复的。Gateway 的 zombie 检测 + error-chunk 机制正确识别并处理。

3x 429_integrate_rate_limit 是 NVCF 瞬态行为，KEY_COOLDOWN_S=25 已足够。NV_INTEGRATE_KEY_COOLDOWN_S=0 对 integrate path 无额外惩罚。

dsv4p_nv 和 ms_gw 6h 零流量，无需调整 tier budget 或 peer-fb。

### 变更: 零参数
- 无 compose 修改
- 无容器重启
- 无代码修改

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2