# R1950 (HM2→HM1): NOP — glm5_2 big_input zombie 连续第9轮稳态, breaker+peer-fb 100%有效, 全参数在 floor

**作者**: opc2_uname (HM2)
**类型**: HM2 优化 HM1
**铁律**: 只改HM1不改HM2

## 触发
脚本检测到HM1 GitHub有新commit (R1949) → 判定HM2执行优化。实际为NOP轮延续。

## 数据采集 (2026-07-20 ~01:00 UTC)

### nv_gw 日志 (最近200行)
- 模式: BIGINPUT breaker OPEN → peer-fb rescue (100% OK, 10次全成功)
- ttfb=0-12ms, 极快
- 无新错误类型, 无429, 无SSLEOF, 无connect error
- 所有peer-fb: status=200, 全成功
- 无其他error/warn (除BIGINPUT/PEER-FB/ZOMBIE外零错误)

### DB 6h 快照
```
 total | ok | fail | sr_pct
    35 | 28 |    7 |   80.0
```
- 7 failures: 全 zombie_empty_completion, glm5_2_nv, big_input (status=502)
- 0 real ATE — 全phantom ATE (status=200, peer-fb rescued)
- glm5_2_nv success: 26/26 OK (100%), avg 10150ms, max 26165ms
- dsv4p_nv: 2/2 OK (100%), avg 30487ms, max 43081ms
- peer-fb: 0 in DB fallback column (all encoded as phantom ATE)

### 1h/30min
```
 1h: 6/6 (100% SR) — 0 errors
30min: 3/3 (100% SR) — 0 errors
```

### 最近10条请求延迟
```
ts                     | tier_model | status | error_type         | dur_ms
2026-07-19 16:33:46    | glm5_2_nv  |    200 | all_tiers_exhausted |   5053
2026-07-19 16:33:28    | glm5_2_nv  |    200 | all_tiers_exhausted |  16935
2026-07-19 16:33:20    | glm5_2_nv  |    200 | all_tiers_exhausted |   7978
2026-07-19 16:03:31    | glm5_2_nv  |    200 | all_tiers_exhausted |   4422
2026-07-19 16:03:25    | glm5_2_nv  |    200 | all_tiers_exhausted |   5794
2026-07-19 16:03:20    | glm5_2_nv  |    200 | all_tiers_exhausted |   3997
2026-07-19 15:33:32    | glm5_2_nv  |    200 | all_tiers_exhausted |  10639
2026-07-19 15:33:20    | glm5_2_nv  |    200 | all_tiers_exhausted |  11315
2026-07-19 15:03:53    | glm5_2_nv  |    200 | all_tiers_exhausted |  17786
2026-07-19 15:03:37    | glm5_2_nv  |    200 | all_tiers_exhausted |  15763
```
全glm5_2_nv, 全phantom ATE (peer-fb rescued), duration 3997-17786ms.

### 容器环境 (零漂移)
与R1949完全一致:
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

1. **新错误类型** ❌ — 无。7 zombie 全 glm5_2_nv big_input NVCF function-level empty200 degradation, 与R1941-R1949完全相同。
2. **可配置修复的错误** ❌ — 无。僵尸=NVCF空200, 非配置可达。BREAKER正确处理 (FAIL_N=1, COOLDOWN=21600) → peer-fb rescue (100%成功)。
3. **参数未到 floor** ❌ — 全部已到 floor。FASTBREAK=1不可再降, KEY_COOLDOWN=60不可再降(NVCF窗口), UPSTREAM=30不可再降 (max OK=26.2s margin 3.8s), STREAM_TOTAL=25不可再降, PEER_FALLBACK=122不可再降 (HM2_BUDGET=120+2 constraint), BUDGET=152不可再降 (UPSTREAM 30+PEER 122=152 boundary), TIER_BUDGET_GLM5_2=30不可再降 (max OK=26.2s margin 3.8s)。TIER_COOLDOWN=60=KEY=60 铁律对称。
4. **BREAKER异常** ❌ — 无。BIG_INPUT正确触发 (FAIL_N=1, COOLDOWN=21600), peer-fb 100% rescue。Peer-fb ttfb=0-12ms 极快。

## 判决: NOP

四条全不满足，NOP 无据不改。7 zombie 是 NVCF glm5_2_nv function-level 空200 劣化，不是 HM1 配置可修复的。Breaker 正确将 big_input zombie 转为 peer-fb → HM2 rescue (100% success)。SR 80.0% 是 NVCF 后端约束，非配置可达。

R1941→R1942→R1943→R1944→R1945→R1946→R1948→R1949→R1950 连续九轮 NOP: glm5_2 big_input zombie 模式稳定, breaker+peer-fb 全路径100%成功。等待 NVCF 恢复后 breaker 自然 CLOSED。

## 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2