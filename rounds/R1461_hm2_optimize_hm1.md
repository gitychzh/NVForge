# HM2 Optimize HM1 — Round R1461

## 触发分析

cron 脚本输出: `"这是我提交的, 不触发"` + `latest commit 0123282 R1460: fix symlink...`
- 最新 commit author = `opc2_uname` (HM2)
- 脚本正确检测到自提交 → 标记 "不触发"
- cron 仍被派遣 — 误触发 (double-dispatch, R1460→R1461)
- R1460 已提交且 symlink 已修复 → 本轮创建 R1461

## 改前数据

### 容器状态
- nv_gw: `Up 32 minutes (healthy)`, 重启于 `2026-07-15T13:09:29Z`
- compose md5: `45c1f2840ddd9e7e52dfc054f1c02eb4` (R1459 Connection:close 修复后)

### 6h 总览 (nv_requests)
- 41req/18OK/23err → 43.9% SR
- 13 zombie_empty_completion (11 glm5_2_nv integrate, 2 dsv4p_nv pexec — NVCF content-filter, ~216K input → 0-28 output tokens)
- 10 all_tiers_exhausted (9 dsv4p_nv avg 70.5s, 1 glm5_2_nv 187s)
- 0 tier_attempts, 0 fallback_occurred

### 按模型
| 模型 | 请求 | OK | 错误 | SR% | 平均延迟 |
|------|------|----|----|-----|---------|
| glm5_2_nv | 27 | 15 | 12 | 55.6% | 18.4s |
| dsv4p_nv | 14 | 3 | 11 | 21.4% | 62.7s |

### 重启后 (32min)
- 5req/3OK/2err → 60.0% SR (太薄，无统计意义)
- 2 zombie: 1 dsv4p_nv 49.5s, 1 glm5_2_nv 8.1s

### ms_gw
- 25/21 OK, 0 fail
- MS-STREAM-DONE at 2-3s → 健康

### 日志
- NV-ZOMBIE-EMPTY: dsv4p_nv content_chars=14 (<50), glm5_2_nv content_chars=28 (<50)
- 全为 NVCF 内容过滤 (大输入 → 几乎空输出)，非配置可修复

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

**原因**: 全部参数已在地板/最优值。所有错误均为服务端 (NVCF content-filter zombie + NVCF 504 ATE)，非配置可修复。

- zombie: NVCF 对大输入(>200K chars)返回空/几乎空 completion → 代码层 zombie 检测正确触发，配置无法阻止
- ATE: dsv4p_nv NVCF 504 为函数级退化，BUDGET=66=UPSTREAM=66 已是最紧地板，ms_gw 25/21 健康
- 0 tier_attempts: 无 429 循环，键池干净
- 0 fallback: 无 ms_gw 或 peer-fb 触发 — 需确认 R1459 Connection:close 修复是否生效 (重启后 5 请求中无 ATE 触发 fallback)

**零参数变更，零 compose 修改，零容器重启。**

- 铁律: 只改HM1不改HM2

## ⏳ 轮到 HM1 优化 HM2
