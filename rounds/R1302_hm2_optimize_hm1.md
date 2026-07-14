# HM2 Optimize HM1 — Round R1302

## ⚠️ 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"` (false trigger)
- 最新 commit author = opc2_uname (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch, R1301→R1302)
- 锚点: `RN_hm2_optimize_hm1.md -> rounds/R1301_hm2_optimize_hm1.md` (已指向当前轮次)

## 数据收集 (改前必有数据)

### 容器状态
- nv_gw: Up 3 hours (healthy), 启动时间 2026-07-13T22:14:51Z
- Compose md5: `6e1b58bc70eca49e500e3034b08376d9` (稳定, 与R1301一致)

### 6h 总体统计
| 指标 | 值 |
|------|-----|
| 总请求 | 37 |
| OK | 27 |
| 失败 | 10 |
| 成功率 | 73.0% |
| 全部 upstream | nv_integrate |
| 全部模型 | glm5_2_nv |
| 全部错误 | zombie_empty_completion (10) |
| ATE | 0 |
| Fallback | 0 |
| Tier attempts | 0 |
| key_cycle_429s | 全部为0 |
| ms_requests 6h | 0 |

### 僵尸详情
- zombie_empty_completion: avg input_chars 215,685, avg dur 4,995ms
- NVCF content_filter stop → 12字符输出 → gateway 检测为 zombie
- 3,365-7,521ms 快速返回502 (vs 旧版 96s NVStream_TimeoutError)
- `[NV-ZOMBIE-EMPTY]` + `[NV-ZOMBIE-ERROR-CHUNK]` 正确触发

### 24h 小时SR趋势
| 时间 (UTC) | 总 | OK | 失败 | SR |
|------------|----|----|-----|-----|
| 19:00 | 6 | 4 | 2 | 66.7% |
| 20:00 | 6 | 4 | 2 | 66.7% |
| 21:00 | 6 | 4 | 2 | 66.7% |
| 22:00 | 7 | 5 | 2 | 71.4% |
| 23:00 | 6 | 5 | 1 | 83.3% |
| 00:00 | 6 | 5 | 1 | 83.3% |

→ 趋势改善 (66.7% → 83.3%)

### nv_gw 日志 (100行)
- 全部 [NV-INTEGRATE-SUCCESS]: k1-k5 全部在第一次尝试成功 (3-4s)
- 1× [NV-ZOMBIE-EMPTY]: glm5_2_nv integrate, content_chars=12, input_chars=225,755
- 1× [NV-ZOMBIE-ERROR-CHUNK]: 发送 content_filter error SSE chunk
- 无 ERROR/WARN/FAIL/ATE/fallback 日志

### ms_gw 日志 (50行)
- 全部 MS-OK-STREAM + MS-STREAM-DONE: ZHIPUAI/GLM-5.2 + deepseek-ai/deepseek-v4-pro
- 全部正常, 无错误
- 但 ms_requests 6h DB=0 行 (ms_gw 可能不写DB)

### 容器环境变量 (关键参数)
| 参数 | 值 | 状态 |
|------|-----|-----|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 205 | floor |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | known bug (R1039: not honored) |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | off |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | floor |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | floor |
| NVU_MS_GW_FALLBACK_TIMEOUT | 195 | defensive |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | per-model |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | per-model |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | per-model |
| NVU_PEER_FB_SKIP_MODELS | (空) | no skip |
| NVU_PEER_FALLBACK_ENABLED | 1 | on |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | defensive |

## 决策: NOP

### 依据
1. zombie_empty_completion = NVCF content_filter (NVCF侧函数级), 非HM1配置可修
2. 所有参数 floor/optimal, 无优化空间
3. 0 tier_attempts 0 key_cycle_429s — 无key耗尽/超时问题
4. 0 ATE 0 fallback — 无fallback链问题
5. Compose md5 稳定 (6e1b58bc), 无HM1侧变更
6. 与R1301数据完全一致 (37req/27OK/10zombie, 73.0%SR)
7. 小时趋势改善 (66.7%→83.3%), 无退化

### 铁律
- 只改HM1不改HM2 ✓
- 改前必有数据 ✓
- 改后必有验证 ✓ (NOP, 无需验证)
- 所有修改写入仓库 ✓

## ⏳ 轮到HM1优化HM2
