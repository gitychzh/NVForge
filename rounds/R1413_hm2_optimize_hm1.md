# R1413: HM2→HM1 — NOP (false trigger, double-dispatch, 572nd chain of R1133)

## 1. 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit: `9aa90f2` (R1412, HM2 NOP, opc2_uname)
- 判定: **false trigger — double-dispatch** (R1412已提交, symlink已指向R1412, 再次误触发)
- HM1 git log 仍停留在 R1206 (207轮落后), 无新提交

## 2. 改前数据 (6h窗口, 2026-07-15 UTC 00:00-06:00)

### nv_gw
| 指标 | 值 |
|------|-----|
| 总请求 | 16 |
| 成功 (200) | 13 |
| 失败 | 3 |
| 成功率 | 81.3% |
| tier_attempts | 0 |

### 错误分类
| error_type | 数量 | avg_dur_ms |
|------------|------|-----------|
| zombie_empty_completion | 2 | 7624 |
| all_tiers_exhausted | 1 | 106052 |

### 按小时
| 小时 | 总 | 成功 | 失败 | SR% |
|------|-----|------|------|------|
| 00:00 | 4 | 4 | 0 | 100.0 |
| 01:00 | 6 | 5 | 1 | 83.3 |
| 02:00 | 6 | 4 | 2 | 66.7 |

### ms_gw (6h)
| 指标 | 值 |
|------|-----|
| 总 | 5 |
| 成功 | 0 |
| 失败 | 5 (null error_type) |

### Docker logs (nv_gw, 最近100行)
- 2x zombie_empty_completion glm5_2_nv (NVCF content-filter, finish_reason=stop/timeout, R1405 fix active)
- 1x ATE dsv4p_nv: 504 gateway+timeout (k4), NVCFPexecTimeout (k5 fastbreak), ms_gw relay TimeoutError 198814ms

## 3. 配置状态
- Compose md5: `f493494e2b41b17fbf5d9cff9093648e` (自容器重启 2026-07-14T23:43:06Z 未变)
- 所有参数 floor/optimal: UPSTREAM_TIMEOUT=66, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, TIER_TIMEOUT_BUDGET_S=205, MIN_OUTBOUND_INTERVAL_S=0, CONNECT_RESERVE_S=0, NVU_FORCE_STREAM_UPGRADE=0, KEY_AUTHFAIL_COOLDOWN_S=60
- NVU_PEXEC_TIMEOUT_FASTBREAK=1, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_MS_GW_FALLBACK_TIMEOUT=195, NVU_PEER_FALLBACK_TIMEOUT=66

## 4. 决策
- **NOP** — 数据与 R1412 完全一致 (16req/13OK/3fail, 2 zombie + 1 ATE)
- 0 tier_attempts — 无 key 循环问题
- 0 config-fixable — 所有参数已 floor/optimal
- zombie_empty_completion = NVCF content-filter (code-level, 非配置可修复)
- ATE dsv4p_nv = ms_gw relay TimeoutError (R1103 BUDGET enforcement gap, 非配置层面)
- 铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
