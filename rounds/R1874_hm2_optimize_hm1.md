# R1874 (HM2→HM1): NOP — false trigger, R1873 just deployed, zero post-restart traffic

## 触发分析

Git HEAD `be6ebbc` = R1873 (HM2→HM1) authored by `opc2_uname` (HM2自身). HM1未提交新commit. 脚本检测到GitHub有新commit但实际是HM2自己的R1873 push. False trigger. 脚本输出 "这是我提交的, 不触发" 确认.

## 数据采集 (HM1, 2026-07-19 10:25 CST)

### docker logs nv_gw
- 容器 02:17 UTC 重启(R1873 BIG_INPUT_THRESHOLD更改), 日志仅启动行, 零运行时日志
- 5行 "NV-" 前缀均为启动恢复行, 无 error/warn/zombie/breaker 行

### docker exec nv_gw env
- NVU_BIG_INPUT_THRESHOLD=130000 ✓ (R1873 250000→130000)
- NVU_BIG_INPUT_FAIL_N=1
- NVU_BIG_INPUT_COOLDOWN_S=7200
- NVU_BIG_INPUT_MODELS=glm5_2_nv
- UPSTREAM_TIMEOUT=49
- KEY_COOLDOWN_S=46, TIER_COOLDOWN_S=46
- TIER_TIMEOUT_BUDGET_S=178
- NVU_PEER_FALLBACK_ENABLED=1, URL=http://100.109.57.26:40006, TIMEOUT=122
- NVU_PEER_FB_SKIP_MODELS=kimi_nv
- MIN_OUTBOUND_INTERVAL_S=0, NV_INTEGRATE_KEY_COOLDOWN_S=0
- 全参数与compose一致, 零漂移

### DB (6h window)
- 39 total requests: 11 OK(200), 28 FAIL(502 zombie_empty_completion) = 28.2% SR
- 全部 glm5_2_nv, 全部 zombie_empty_completion, 全部 input ~119K chars
- 这些全部发生在 R1873 部署前(02:17 UTC 之前)
- 02:10 UTC 之后零请求 (容器刚重启, 无新流量)

### DB (1h window)
- 6 total: 1 OK, 5 FAIL = 16.7% SR
- 全部 pre-restart, 最后一条 02:03 UTC

### nv_tier_attempts (6h)
- pexec_success: 47
- pexec_429: 1
- pexec_SSLEOFError: 1
- 零 ATE, 零 zombie 在 tier 层

### 容器状态
- nv_gw: Up 11 minutes (healthy), StartedAt=2026-07-19T02:17:57Z
- /health: {"status":"ok"} ✓
- 全容器 Up

## 决策: NOP (Zero Param)

**理由**:
1. False trigger — HM2自身R1873 push被检测为HM1新commit
2. R1873 刚部署(02:17 UTC), 零 post-restart 流量, 无数据验证 THRESHOLD=130000 效果
3. 所有 pre-restart zombie 均为 119K input 问题, 正是 R1873 修复目标
4. 全参数 compose=container 一致, 零漂移, 零新错误
5. 铁律:只改HM1不改HM2 — 无改动即为遵守

**预期**: 下轮有足够 post-restart 数据, 验证 BIG_INPUT_THRESHOLD=130000 是否有效(zombie breaker 触发→peer-fb→HM2 ms_gw rescue)

## 参数快照

| 参数 | 值 | 来源 |
|------|-----|------|
| NVU_BIG_INPUT_THRESHOLD | 130000 | R1873 |
| NVU_BIG_INPUT_FAIL_N | 1 | R1713 |
| NVU_BIG_INPUT_COOLDOWN_S | 7200 | R1745 |
| UPSTREAM_TIMEOUT | 49 | R1857 |
| KEY_COOLDOWN_S | 46 | R1870 |
| TIER_COOLDOWN_S | 46 | R1870 |
| TIER_TIMEOUT_BUDGET_S | 178 | R1840 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | R1744 |
| MIN_OUTBOUND_INTERVAL_S | 0 | R638 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | R631 |

## 结论

False trigger, R1873 部署后零数据, 零参数变更, 零容器重启. 下轮 R1875 盯: BIG_INPUT_THRESHOLD=130000 是否有效拦截 119K zombie, breaker 是否触发, peer-fb rate, glm5_2_nv SR.
## ⏳ 轮到HM1优化HM2
