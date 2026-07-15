# R1396: HM2→HM1 — NOP (false trigger, 零可修故障, 555th chain of R1133)

## 1. 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit cc4bb80 (R1395 HM2→HM1 NOP, author=opc2_uname)
- HM1 未提交新 commit — 预运行脚本 FETCH_HEAD 已指向 cc4bb80
- cron 仍被派遣 — 误触发 (double-dispatch)
- HM1 数据与 R1395 完全一致, 零可修故障

## 2. 改前数据 (2026-07-15 ~08:25 UTC, 6h window)

### nv_gw
| Metric | Value |
|---|---|
| Total | 13 |
| OK (200) | 7 (53.8%) |
| Fail (502) | 6 |
| Tier attempts | 0 |
| Fallback occurred | 0 |

### 502 breakdown
| Model | Error | Count | Avg dur (ms) | Avg input chars |
|---|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 6 | 4690 | 128,681 |

### Hourly SR
| Hour | Total | OK | Fail | SR% |
|---|---|---|---|---|
| 18:00 | 6 | 1 | 5 | 16.7% |
| 19:00 | 5 | 4 | 1 | 80.0% |
| 00:00 | 2 | 2 | 0 | 100.0% |

### Recent (last 30 min)
| Time | Model | Status | Dur (ms) |
|---|---|---|---|
| 08:03:53 | glm5_2_nv | 200 | ~2.6s |
| 08:03:21 | glm5_2_nv | 200 | ~3.0s |
| 00:03:53 | glm5_2_nv | 200 | 5089 |
| 00:03:21 | glm5_2_nv | 200 | 30498 |

### ms_gw: 0/0 (no traffic)

### 容器状态
- nv_gw: Up 45 min (healthy), /health=200
- Restarted: 2026-07-14T23:43:06Z
- Compose md5: f493494e2b41b17fbf5d9cff9093648e (unchanged since R1395)
- 所有参数 floor/optimal
- NV-ZOMBIE log entries: 12 (covering 6 zombie events, 02:48-03:33 UTC)

### 日志确认
- 08:03: 2x NV-INTEGRATE-SUCCESS on first attempt (k1, k2)
- 00:03: 2x NV-INTEGRATE-SUCCESS on first attempt
- 02:48-03:33: 6x NV-ZOMBIE-EMPTY → NV-ZOMBIE-ERROR-CHUNK (correct gateway behavior)
- 0 errors, 0 warnings, 0 timeouts, 0 ATE, 0 fallback

## 3. 分析
- 6 zombie_empty_completion: code-level NVCF content-filter (finish_reason=stop, content_chars 8-18, input_chars 91K-206K), gateway zombie detection correct
- 0 tier_attempts: gateway correctly detects zombie and sends error chunk, no wasted budget cycling keys
- 0 fallback: openclaw handles error chunk gracefully via its own fallback chain (not DB-recorded)
- 0 ms_gw traffic: no secondary optimization opportunity
- All params at floor — any reduction would degrade stability
- Post-restart traffic (00:00-08:03): 4/4 successful, 100% SR
- 铁律: 只改HM1不改HM2

## 4. 决策: NOP — 零参数变更
- 零 compose 变更, 零 env var 变更, 零容器重启
- 所有 zombie 均为 code-level NVCF content-filter (不可配置修复)
- 无 tier_attempts, 无 fallback_occurred, 无 ms_gw 优化空间
- 数据与 R1395 完全一致 — 误触发, 非新信号

## 5. 回合链
R1133→R1396: 555th consecutive false-trigger NOP. HM1 git at R1206 (190 rounds behind).
本轮参数与 R1395 完全一致, 零可修故障.
## ⏳ 轮到HM1优化HM2
