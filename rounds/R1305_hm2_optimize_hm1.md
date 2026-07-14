# HM2 Optimize HM1 — Round R1305

## 触发分析
- **cron 脚本输出**: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)，R1304 为上一轮
- 确认: **false trigger, double-dispatch** (19th consecutive post-R1286)
- 脚本正确检测到自提交并标记"不触发", cron 仍被派遣

## 数据收集 (改前必有数据)

### DB 6h 窗口 (2026-07-14 01:00–09:15 UTC, 容器重启后 ~11h)
| 指标 | 值 |
|------|-----|
| 总量 | 46 req |
| 成功 | 37 OK (80.4% SR) |
| 失败 | 9 (全部 zombie_empty_completion) |
| 模型 | glm5_2_nv 100% |
| 路径 | nv_integrate only |
| 回退触发 | 0 |
| tier_attempts | 0 |
| ATE | 0 |
| IncompleteRead | 0 |

### 每小时 SR 趋势
| 小时 (UTC) | 总量 | OK | 失败 | SR% |
|-----------|------|-----|------|------|
| 2026-07-13 19:00 | 3 | 2 | 1 | 66.7 |
| 2026-07-13 20:00 | 6 | 4 | 2 | 66.7 |
| 2026-07-13 21:00 | 6 | 4 | 2 | 66.7 |
| 2026-07-13 22:00 | 7 | 5 | 2 | 71.4 |
| 2026-07-13 23:00 | 6 | 5 | 1 | 83.3 |
| 2026-07-14 00:00 | 6 | 5 | 1 | 83.3 |
| 2026-07-14 01:00 | 12 | 12 | 0 | **100.0** |

### Zombie 详情
- 9 zombie_empty_completion, glm5_2_nv integrate only
- 平均输入: 216,582 chars (NVCF content-filter 触发)
- 平均耗时: 4,888ms (gateway 3-7s 快速 abort, 非旧版 96s 超时)
- gateway zombie detection 正确: `NV-ZOMBIE-EMPTY` + `NV-ZOMBIE-ERROR-CHUNK` → openclaw fallback

### ms_gw
- 10/10 OK (100% SR), 全部 MS-STREAM-DONE
- 健康服务, 承担 zombie 触发后的 openclaw 回退请求

### 容器状态
- nv_gw: Up 3 hours (healthy), 重启于 2026-07-13T22:14:51Z
- Compose md5: 6e1b58bc (stable, 与 R1302/R1303/R1304 一致)

### 环境变量 (全部 floor/optimal)
```
UPSTREAM_TIMEOUT=66
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_SSLEOF_RETRY_DELAY_S=1.0
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FB_SKIP_MODELS= (空, dsv4p_nv peer-fb 已启用)
MIN_OUTBOUND_INTERVAL_S=0
```

## 决策: NOP ❌→

### 理由
1. **全部 9 个失败均为 zombie_empty_completion** — NVCF content-filter 触发 (216K+ 输入 → stop+12 chars), 非配置可修复 (not config-fixable)
2. **gateway zombie detection 工作正常** — 3-7s 快速 abort, 发送 error chunk 给 openclaw 触发 ms_gw 回退
3. **ms_gw 健康 (10/10 100%)** — 回退路径可靠
4. **0 tier_attempts, 0 ATE, 0 IncompleteRead** — 无下游错误需要优化
5. **所有参数 floor/optimal** — 无下调空间
6. **每小时 SR 改善中** — 最新小时 100% (12/12)
7. **Compose md5 稳定** — 与 R1302-R1304 一致，HM1 无外部变更
8. **铁律: 只改HM1不改HM2** — 无 HM1 配置优化空间

### 参数变更: 无
- 零参数修改, 零 compose 变更, 零容器重启

## ⏳ 轮到HM1优化HM2
