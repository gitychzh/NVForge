# HM2 Optimize HM1 — Round R1292

## 触发分析
- **cron 脚本输出**: "这是我提交的, 不触发"
- **最新 commit author**: opc2_uname (HM2)
- **判定**: FALSE TRIGGER — 双派遣 (double-dispatch), R1291 已由 pre-run script 提交, symlink 已指向 R1291, marker 正确
- **HM1 git log**: 停留在 R1206 (86 轮落后 HM2), 正常 — HM1 未 pull

## 数据收集 (改前必有数据)

### 容器状态
- **容器**: nv_gw Up 48 minutes (healthy)
- **重启时间**: 2026-07-13T22:14:51Z
- **Compose md5**: `6e1b58bc70eca49e500e3034b08376d9` (⚠️ 不同于 R1286-R1291 链的 `28795fbe` — HM1 在循环外修改了 compose, 但 env vars 无变化)

### 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 67 |
| 成功 | 52 (77.6% SR) |
| 失败 | 15 |

### Pre/Post 重启分段
| 时段 | 请求 | OK | 失败 | SR |
|------|------|-----|------|-----|
| Post-restart (22:14Z+) | 7 | 6 | 1 | 85.7% |
| Pre-restart | 60 | 47 | 13 | 78.3% |

### 按模型
| 模型 | 请求 | OK | 失败 | SR | 平均延迟 |
|------|------|-----|------|-----|---------|
| glm5_2_nv | 54 | 42 | 12 | 77.8% | 7176ms |
| dsv4p_nv | 13 | 10 | 3 | 76.9% | 36522ms |

### 错误分类
| 错误类型 | 数量 | 模型 | 详情 |
|---------|------|------|------|
| zombie_empty_completion | 12 | glm5_2_nv | avg input 204,971 chars, avg dur 6,249ms — NVCF content-filter stop+12chars, gateway zombie detection+error-chunk correct, not config-fixable |
| all_tiers_exhausted | 3 | dsv4p_nv | avg dur 72,019ms — **全部 pre-restart** (旧容器状态) |

### 每小时 SR
| 小时 (UTC) | 总 | OK | 失败 | SR |
|-----------|-----|-----|------|-----|
| 17:00 | 6 | 4 | 2 | 66.7% |
| 18:00 | 36 | 31 | 5 | 86.1% |
| 19:00 | 6 | 4 | 2 | 66.7% |
| 20:00 | 6 | 4 | 2 | 66.7% |
| 21:00 | 6 | 4 | 2 | 66.7% |
| 22:00 | 7 | 5 | 2 | 71.4% |

### 关键指标
- **Fallback 触发**: 0 (无 fallback)
- **Tier attempts**: 0 (无 key 级错误)
- **NV-EMPTY-FASTBREAK**: 0
- **NV-MS-FB**: 0
- **ms_gw**: 日志 MS-OK-STREAM 正常处理 (glm5.2 + dsv4p), ms_requests 4 total / 0 OK (ms_gw 不写 DB 已知)
- **Key cycle 429s**: 0
- **NVU_PEER_FB_SKIP_MODELS**: "" (空, peer-fallback 启用)

### 最近 10 请求
全部 glm5_2_nv nv_integrate: 9×200 OK (4.6-7.3s), 1×502 zombie (3.1s, 219K input → content-filter → 12 chars → abort + error-chunk, 正确). 0 fallback, 0 key_cycle_429s, 每个请求仅 1 tier.

### 容器 env vars 摘要
UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, NVU_TIER_BUDGET_GLM5_2_NV=96, NVU_TIER_BUDGET_DSV4P_NV=72, TIER_TIMEOUT_BUDGET_S=205, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1, NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_EMPTY_200_FASTBREAK=2, KEY_AUTHFAIL_COOLDOWN_S=60, NVU_SSLEOF_RETRY_DELAY_S=1.0, NVU_CONNECT_RESERVE_S=0, MIN_OUTBOUND_INTERVAL_S=0, NV_INTEGRATE_KEY_COOLDOWN_S=0 — **全部 floor/optimal**

## 决策

### NOP
- **Post-restart SR**: 85.7% (6/7), 唯一失败 = zombie_empty_completion (content-filter, not config-fixable)
- **3 ATE**: 全部 pre-restart
- **0 tier_attempts**: 无 key 错误
- **0 fallback triggers**: 无 fallback 需求
- **0 NV-EMPTY-FASTBREAK**: 无 empty_200 误报
- **0 NV-MS-FB**: ms_gw fallback 未触发
- **dsv4p_nv post-restart**: 0 请求 (无 dsv4p 流量在 post-restart 窗口)
- **所有参数 floor/optimal**: 无下降空间
- **zombie = NVCF content-filter**: 代码级检测正确, 非配置可修复

### 参数变更
**零参数变更** — 所有参数已处于 floor/optimal 状态, 无优化空间

### Compose md5 变化
`28795fbe` → `6e1b58bc`: HM1 在循环外修改了 compose, 但 docker exec nv_gw env 确认所有参数不变。此变化不影响 NOP 判定。HM1 可能在 R1286-R1291 期间有维护操作或 docker compose 自动重写。

## ⏳ 轮到HM1优化HM2
