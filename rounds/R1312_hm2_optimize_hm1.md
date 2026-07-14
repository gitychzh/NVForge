# HM2 Optimize HM1 — Round R1312

## 1. 触发分析
- **cron 脚本输出**: `"这是我提交的, 不触发"` (false trigger)
- **最新 commit**: f8a7912 R1311 (author=opc2_uname, HM2)
- **HM1 git log**: R1206 (106 rounds behind)
- **判定**: DOUBLE-DISPATCH false trigger (R1311 already committed, symlink already correct, 26th consecutive post-R1286)
- **dispatch 消息**: contradictory "HM1提交了新commit到GitHub" — 实际 HM1 未提交

## 2. 数据收集 (改前必有数据)
### 2.1 6h 总体
- 59req/52OK/7err, 88.1% SR
- glm5_2_nv integrate only, 0 dsv4p_nv traffic, 0 kimi_nv traffic

### 2.2 错误分类
- 7× zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop+12-36 chars, avg input_chars=213K, avg dur=4870ms)
- Gateway detection: NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK 正确触发
- 0 tier_attempts, 0 ATE, 0 IncompleteRead, 0 fallback

### 2.3 小时趋势
| Hour | Total | OK | Fail | SR% |
|------|-------|-----|------|-----|
| 21:00 | 6 | 4 | 2 | 66.7 |
| 22:00 | 7 | 5 | 2 | 71.4 |
| 23:00 | 6 | 5 | 1 | 83.3 |
| 00:00 | 6 | 5 | 1 | 83.3 |
| 01:00 | 29 | 28 | 1 | 96.6 |
| 02:00 | 5 | 5 | 0 | 100.0 |

### 2.4 ms_gw
- 13/13 100% OK — healthy, no secondary optimization opportunity

### 2.5 容器状态
- nv_gw: Up 5 hours (healthy)
- compose md5: 6e1b58bc (unchanged from R1311)

### 2.6 关键参数 (container env)
- UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_TIER_BUDGET_MINIMAX_M3_NV=100, KEY_AUTHFAIL_COOLDOWN_S=60
- NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66, NVU_FORCE_STREAM_UPGRADE=0
- NVU_EMPTY_200_FASTBREAK=2, NVU_PEER_FB_SKIP_MODELS=empty
- NVU_FALLBACK_HEALTH_THRESHOLD=0.05, MIN_OUTBOUND_INTERVAL_S=0

## 3. 决策
- **NOP** — 所有参数已在 floor/optimal，zombie_empty_completion 为 NVCF content-filter 层问题（非 config-fixable），ms_gw 100% 无优化空间
- 数据与 R1311 完全一致（59req/52OK/88.1%SR, 7 zombie, 0 tier_attempts, 0 ATE, 0 IncompleteRead, 0 fallback, ms_gw 13/13 100%）
- 零参数变更，零 compose 变更，零容器重启
- 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
