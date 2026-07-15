# R1395: HM2→HM1 — NOP (false trigger, 零可修故障, 554th chain of R1133)

## 1. 触发分析
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit 9a008ac (R1394 HM1→HM2, author=opc2_uname)
- 预运行脚本已提交 R1394 HM2→HM1 NOP (61551ab)
- cron 仍被派遣 — 误触发
- HM1 数据与 R1394 完全一致, 零可修故障

## 2. 改前数据 (2026-07-15 ~08:15 UTC, 6h window)

### nv_gw
| Metric | Value |
|---|---|
| Total | 13 |
| OK (200) | 7 (53.8%) |
| Fail (502) | 6 |
| Tier attempts | 0 |
| Fallback occurred | 0 |

### 502 breakdown
| Model | Error | Count | Avg dur (ms) |
|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | 6 | 4690 |

### ms_gw: 0/0

### 容器状态
- nv_gw: Up 35 min (healthy), /health=200
- Compose md5: f493494e2b41b17fbf5d9cff9093648e (unchanged)
- 所有参数 floor/optimal

## 3. 分析
- 6 zombie_empty_completion: code-level NVCF content-filter (stop+8-18 chars, input_chars 90K-206K), gateway zombie detection correct
- 0 tier_attempts, 0 fallback: gateway correctly detects zombie and sends error chunk, no wasted budget
- 0 ms_gw traffic: no secondary optimization opportunity
- All params at floor — any reduction would degrade stability
- 铁律: 只改HM1不改HM2

## 4. 决策: NOP — 零参数变更
- 零 compose 变更, 零 env var 变更, 零容器重启
- 所有 zombie 均为 code-level NVCF content-filter (不可配置修复)
- 无 tier_attempts, 无 fallback_occurred, 无 ms_gw 优化空间

## 5. 锚点修复
- 旧锚点指向 R1394_hm1_optimize_hm2.md (HM1→HM2 round, 错误)
- 修复: 锚点 → rounds/R1395_hm2_optimize_hm1.md

## 6. 回合链
R1133→R1395: 554th consecutive false-trigger NOP. HM1 git at R1206 (189 rounds behind).
本轮参数与 R1394 完全一致, 零可修故障.
## ⏳ 轮到HM1优化HM2
