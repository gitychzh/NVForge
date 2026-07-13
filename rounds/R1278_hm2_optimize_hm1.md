# HM2 Optimize HM1 — Round R1278

## 触发分析
- cron 脚本输出: "这是我提交的, 不触发" — **FALSE TRIGGER**
- GitHub 最新 commit: c6b6203 (author=opc2_uname, HM2)
- HM1 本地 git log: R1206 (71 轮落后)
- HM1 未提交任何新内容 → false trigger confirmed

## 数据收集 (改前必有数据)
**6h DB snapshot (R1278, 2026-07-14 ~05:00 UTC):**

| 指标 | 值 |
|------|-----|
| 总请求 | 66 |
| 成功 (200) | 51 |
| 失败 | 15 |
| 6h SR | 77.3% |
| glm5_2_nv | 53 req, 41 OK (77.4%), 10,655ms avg |
| dsv4p_nv | 13 req, 10 OK (76.9%), 36,522ms avg |
| integrate | 53 req, 41 OK, 10,655ms avg |
| pexec | 10 req, 10 OK (100%), 25,873ms avg |
| ATE (NULL upstream) | 3 req, 0 OK, 72,019ms avg |

**错误分类 (15 fail):**
| 错误 | 数量 | 模型 | 可修性 |
|------|------|------|--------|
| zombie_empty_completion | 11 | glm5_2_nv | code-level, 非 config-fixable |
| all_tiers_exhausted | 3 | dsv4p_nv | MODELMAP missing dsv4p (R1275 fix, 待验证) |
| NVStream_IncompleteRead | 1 | glm5_2_nv | transient |

**补充:**
- nv_tier_attempts: 0 rows (无 tier 级错误)
- fallback_occurred: 0 (全部 f) — R1275 MODELMAP dsv4p_nv:dsv4p_ms 待触发
- ms_gw: 激活 (18 MS-OK/MS-STREAM-DONE in logs, 4 ms_requests in DB)
- 0 429s, 0 fallback triggers
- 0 dsv4p_nv pexec traffic (仍走 dsv4p_nv → ATE without MODELMAP fallback trigger)

## compose 参数审计
全部 floor/optimal — 无优化空间:

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor (R988, buffer=3.4s ≥ 3s rule) |
| TIER_TIMEOUT_BUDGET_S | 210 | optimal (R1088: dsv4p ms 132s headroom) |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | floor (R1116: k5 rescue budget at floor) |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| TIER_COOLDOWN_S | 15 | floor (R1103 revert, key-specific empty_200) |
| KEY_COOLDOWN_S | 25 | optimal |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | defensive (R922, HM2 symmetric) |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | aligned UPSTREAM=66 |
| NVU_EMPTY_200_FASTBREAK | 2 | floor (code-level no-op per R1039) |
| NVU_PEER_FB_SKIP_MODELS | "" | optimal (R1000, all models enabled) |
| MODELMAP | glm5_2/kimi/dsv4p→ms | R1275 added dsv4p |

## 判决: NOP
- **false trigger**: HM1 未提交任何内容，cron 误派遣
- **数据相同**: R1277 66/51/15 77.3% SR → R1278 66/51/15 77.3% SR
- **全部参数 floor/optimal**: 零优化空间
- 11 zombie = NVCF content-filter, code-level detection correct, 非 config-fixable
- 3 ATE dsv4p = R1275 MODELMAP fix pending validation (0 dsv4p pexec traffic)
- **零 compose 修改, 零容器重启, 零参数调整**
- 铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
