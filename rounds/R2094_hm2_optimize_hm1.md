# R2094 (HM2→HM1): NOP — insufficient post-deploy traffic, all NVCF platform-level failures

## 数据 (HM1, 6h window)
- **31 req, 19 OK (61.3% SR), 12 fail**
- 8 zombie_empty_completion (502) — glm5_2_nv, NVCF function 3b9748d8 empty200, not locally fixable
- 3 all_tiers_exhausted (502) — dsv4p_nv, NVCF function 74f02205, all at 14:39 (pre-restart)
- 1 NVStream_IncompleteRead (502) — glm5_2_nv, stream truncated
- 0 peer-fallback events, 0 ms_gw fallback
- glm5_2_nv: 28 req, 19 OK (67.9%), 24/28 with key_cycle_429s (85.7%)
- dsv4p_nv: 3 req, 0 OK, all ATE (pre-restart), avg 6ms
- 429 cycling: 24/31 reqs (77.4%), total_kc429=36

## 1h window
- 4 req, 2 OK (50.0%), 2 fail
- 2 zombie_empty_completion (glm5_2_nv, 3b9748d8)
- 429 cycling: 4/4 (100%), total_kc429=6

## Post-deploy (R2091, KEY=65, deployed 15:14 UTC)
- **仅有 2 req**, 1 OK (13293ms), 1 zombie (59245ms)
- 零 dsv4p_nv 请求 — 无法确认 DEGRADED 是否已解除
- 零 tier_attempts 在 post-deploy 窗口内

## Tier-level (6h)
- glm5_2_nv: 21 pexec_success, 10 pexec_timeout, 5 pexec_SSLEOFError
- dsv4p_nv: 0 tier_attempts (all 3 ATE pre-restart, no tier trace)

## 容器状态
- nv_gw: Up 40 min (healthy), StartedAt 2026-07-20T15:14:03Z (R2091 deploy)
- health OK, proxy_role=passthrough, 5 keys, tiers=[kimi_nv, dsv4p_nv, glm5_2_nv]
- logs_db: Up 3 days, healthy

## 当前参数 (docker exec env)
| 参数 | 值 | 说明 |
|------|-----|------|
| KEY_COOLDOWN_S | 65 | R2091: 62→65 (+3s) |
| TIER_COOLDOWN_S | 60 | |
| UPSTREAM_TIMEOUT | 24 | |
| TIER_TIMEOUT_BUDGET_S | 153 | |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 | |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | |
| NVU_TIER_BUDGET_DSV4P_NV | 20 | |
| NVU_TIER_BUDGET_GLM5_2_NV | 22 | |

## 分析
- **Post-deploy traffic 极低**: R2091 部署后 40 分钟仅 2 个请求，KEY=65 regime 仍无足够数据评估
- 所有 12 个失败均为 NVCF 平台级：
  - 8 zombie (glm5_2, 3b9748d8) — NVCF function 返回 empty200，非本地配置可修
  - 3 ATE (dsv4p, 74f02205) — 全在 pre-restart 14:39，post-deploy 无 dsv4p 请求
  - 1 IncompleteRead — stream 中断，非配置可修
- 零 peer-fallback 事件 — 无触发机会
- 429 cycling 率 77.4% (6h) / 100% (1h) — 小样本偏差，需更多数据
- Tier-level: 10 pexec_timeout vs 5 pexec_SSLEOFError — timeout 仍为主导故障模式
- KEY+TIER=65+60=125 < 153 BUDGET (28s margin)，429 故障窗口合理
- **NOP 铁律**: post-deploy 仅 2 req + 零可配置修复故障 → 禁止改动

## 决策: NOP
- 本轮不做任何参数修改
- 等待 R2091 regime (KEY=65) 产生足够数据后下一轮评估
- 若 dsv4p DEGRADED 持续，下一轮仍为 NOP（NVCF 平台问题，非本地可修）
- 若 dsv4p 恢复，重点评估 KEY=65 的 429 cycling 改善效果
- 连续 2 轮 NOP (R2093→R2094)，流量太低，排队等待数据积累
## ⏳ 轮到HM1优化HM2
