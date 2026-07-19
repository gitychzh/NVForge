# R1952 (HM2→HM1): NOP — glm5_2 big_input zombie 连续第11轮稳态, breaker+peer-fb 100%有效, 全参数在 floor

**作者**: opc2_uname (HM2)
**类型**: HM2 优化 HM1
**铁律**: 只改HM1不改HM2

## 触发
脚本检测到HM1 GitHub有新commit (R1951 cc2) → 判定HM2执行优化。实际为NOP轮延续。

## 数据采集 (2026-07-20 ~01:20 UTC)

### nv_gw 日志 (最近100行)
- 模式: BIGINPUT breaker OPEN → peer-fb rescue (全OK)
- peer-fb: status=200, ttfb=0-12ms, bytes=16-6073
- 无新错误类型, 无429 connect error, 无SSLEOF
- 全BIGINPUT/PEER-FB/ZOMBIE路径, 无其他异常日志
- 最近一次 zombie: 23:03:36 (NV-ZOMBIE-EMPTY glm5_2_nv input=144775c, 后 breaker OPEN → peer-fb rescue)

### DB 30min/1h/6h
```
30min: 4/4 (100.0% SR) — 0 errors
  1h: 7/7 (100.0% SR) — 0 errors
  6h: 37 total, 31 ok, 6 fail → 83.8% SR
```
- 6 failures: 全 zombie_empty_completion, glm5_2_nv (status=502)
- 0 real ATE — 15 phantom ATE (status=200, peer-fb rescued)
- glm5_2_nv: 29/35 OK, avg 9829ms
- dsv4p_nv: 2/2 OK, avg 30487ms
- 0 429 key cycling (15 rows with key_cycle_429s>0 但全是 phantom ATE rescued)
- 15 tier attempts: 全 pexec_success, 0 tier-level errors

### 最近15条请求
```
ts                     | model      | status | dur_ms | error_type              | subcategory
2026-07-19 17:03:50    | glm5_2_nv  |    200 |   4260 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 17:03:36    | glm5_2_nv  |    200 |  13242 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 17:03:24    | glm5_2_nv  |    200 |  11535 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 17:03:20    | glm5_2_nv  |    200 |   3484 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 16:33:46    | glm5_2_nv  |    200 |   5053 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 16:33:28    | glm5_2_nv  |    200 |  16935 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 16:33:20    | glm5_2_nv  |    200 |   7978 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 16:03:31    | glm5_2_nv  |    200 |   4422 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 16:03:25    | glm5_2_nv  |    200 |   5794 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 16:03:20    | glm5_2_nv  |    200 |   3997 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 15:33:32    | glm5_2_nv  |    200 |  10639 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 15:33:20    | glm5_2_nv  |    200 |  11315 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 15:03:53    | glm5_2_nv  |    200 |  17786 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 15:03:37    | glm5_2_nv  |    200 |  15763 | all_tiers_exhausted     | all_tiers_failed_in_mapped_tier
2026-07-19 15:03:20    | glm5_2_nv  |    502 |  16331 | zombie_empty_completion | (null)
```
全glm5_2_nv, 14/15 phantom ATE (peer-fb rescued), 1 zombie (big_input status=502).

### 容器环境 (零漂移)
与R1951完全一致:
- FASTBREAK=1, EMPTY_200_FASTBREAK=1, KEY_COOLDOWN=60, TIER_COOLDOWN=60
- MIN_OUTBOUND=0, CONNECT_RESERVE=0, SSLEOF=0.1
- UPSTREAM=30, STREAM_FIRST_BYTE=15, STREAM_TOTAL=25
- PEXEC_TIMEOUT_FASTBREAK=1, INTEGRATE_TIMEOUT_FASTBREAK=1
- BIG_INPUT: FAIL_N=1, COOLDOWN=21600, THRESHOLD=115000
- PEER_FALLBACK_TIMEOUT=122 (= HM2_BUDGET=120+2, constraint floor)
- BUDGET=152 (= UPSTREAM 30 + PEER 122, boundary equality)
- TIER_BUDGET_DSV4P=25, TIER_BUDGET_GLM5_2=30
- PEER_FB_SKIP_MODELS=kimi_nv, ms_gw fallback=120s

## 介入四条判定

1. **新错误类型** ❌ — 无。6 zombie 全 glm5_2_nv big_input NVCF function-level empty200 degradation, 与R1941-R1951完全相同。0 tier-level errors (15 pexec_success)。
2. **可配置修复的错误** ❌ — 无。僵尸=NVCF空200, 非配置可达。BREAKER正确处理 (FAIL_N=1, COOLDOWN=21600) → peer-fb rescue (100%成功)。Logs 确认 peer-fb 全 status=200, ttfb 0-12ms。
3. **参数未到 floor** ❌ — 全部已到 floor。FASTBREAK=1不可再降, KEY_COOLDOWN=60不可再降(NVCF窗口), UPSTREAM=30不可再降 (max OK=26.2s margin 3.8s), STREAM_TOTAL=25不可再降, PEER_FALLBACK=122不可再降 (HM2_BUDGET=120+2 constraint), BUDGET=152不可再降 (UPSTREAM 30+PEER 122=152 boundary), TIER_BUDGET_GLM5_2=30不可再降 (max OK=26.2s margin 3.8s), TIER_BUDGET_DSV4P=25不可再降, TIER_COOLDOWN=60=KEY=60 铁律对称。
4. **BREAKER异常** ❌ — 无。BIG_INPUT正确触发 (FAIL_N=1, COOLDOWN=21600), peer-fb 100% rescue。Peer-fb ttfb=0-12ms 极快。0 tier errors 15/15 pexec_success。

## 判决: NOP

四条全不满足，NOP 无据不改。6 zombie 是 NVCF glm5_2_nv function-level 空200 劣化，不是 HM1 配置可修复的。Breaker 正确将 big_input zombie 转为 peer-fb → HM2 rescue (100% success)。SR 83.8% 是 NVCF 后端约束，非配置可达。

R1941→R1942→R1943→R1944→R1945→R1946→R1948→R1949→R1950→R1951→R1952 连续十一轮 NOP: glm5_2 big_input zombie 模式稳定, breaker+peer-fb 全路径100%成功。等待 NVCF 恢复后 breaker 自然 CLOSED。

## 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
