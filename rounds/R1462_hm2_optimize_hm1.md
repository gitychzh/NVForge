# HM2 Optimize HM1 — Round R1462

## 触发分析

cron 脚本输出: `"这是我提交的, 不触发"` + `latest commit c0cf6a3 R1461: ...`
- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交 → 标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch, R1461→R1462, 42nd chain of R1395)
- R1461 已提交且 symlink 已指向 R1461 → 本轮创建 R1462

## 改前数据

### 容器状态
- nv_gw: healthy, 重启于 `2026-07-15T13:09:29Z`
- compose md5: `45c1f2840ddd9e7e52dfc054f1c02eb4` (R1459 Connection:close 修复后)

### 6h 总览 (nv_requests)
- 41req/18OK/23err → **43.9% SR** (与R1461完全一致)
- 13 zombie_empty_completion (11 glm5_2_nv integrate, 2 dsv4p_nv pexec — NVCF content-filter)
- 10 all_tiers_exhausted (9 dsv4p_nv avg 70.6s, 1 glm5_2_nv 187.2s — upstream_type=NULL, 调度层拒绝)
- 0 tier_attempts, 0 key_cycle_429s, 0 fallback_occurred

### 按模型
| 模型 | 请求 | OK | 错误 | SR% | 平均延迟 |
|------|------|----|----|-----|---------|
| glm5_2_nv | 27 | 15 | 12 | 55.6% | 12.1s |
| dsv4p_nv | 14 | 3 | 11 | 21.4% | 49.6s |

### ms_gw
- 25/21 OK, 4 fail (84.0% SR)
- MS-STREAM-DONE 正常

### 日志
- NV-ZOMBIE-ERROR-CHUNK: glm5_2_nv+dsv4p_nv timeout SSE chunks
- 全为 NVCF 内容过滤/函数退化，非配置可修复

### 当前配置 (全部低位/最优)
- UPSTREAM_TIMEOUT=66
- TIER_COOLDOWN_S=15
- NVU_TIER_BUDGET_DSV4P_NV=66 (=UPSTREAM，地板)
- NVU_PEXEC_TIMEOUT_FASTBREAK=1
- NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
- NVU_EMPTY_200_FASTBREAK=2
- NVU_PEER_FB_SKIP_MODELS= (空)
- NVU_MS_GW_FALLBACK_TIMEOUT=120 (R1459)
- NVU_PEER_FALLBACK_TIMEOUT=66

## 决策: NOP

**原因**: 数据与R1461完全一致。全部参数已在地板/最优值。所有错误均为服务端 (NVCF content-filter zombie + NVCF 504 ATE)，非配置可修复。

- zombie: NVCF 对大输入(>200K chars)返回空/几乎空 completion → 代码层 zombie 检测正确触发，配置无法阻止
- ATE: dsv4p_nv NVCF 504 为函数级退化，BUDGET=66=UPSTREAM=66 已是最紧地板
- 0 tier_attempts: 无 429 循环，键池干净
- ms_gw 25/21 OK: 健康但 ms_gw 4 fail 需关注 (非本轮优化范围)

**零参数变更，零 compose 修改，零容器重启。**

- 铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
