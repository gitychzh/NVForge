# R1945 (HM2→HM1): NOP — false trigger, 0 new data, 0 config-fixable

**作者**: opc2_uname (HM2)
**类型**: HM2 优化 HM1
**铁律**: 只改HM1不改HM2

## 触发
HM1提交新commit到GitHub (b86415e: "这是我提交的, 不触发")。脚本判定HM2执行优化。

## 数据采集 (2026-07-20 00:20 UTC)

### nv_gw 日志 (最近100行, error/warn)
- 模式: 1 zombie_empty_completion (15:03:20, glm5_2_nv, input=144775c, 16331ms) + 6 peer-fb 100% OK
- 日志与R1944/R1943一致: breaker延时触发→peer-fb rescue
- 无新错误类型, 无429, 无SSLEOF, 无connect error

### DB 6h 快照
```
 total | ok | fail | sr_pct
    34 | 26 |    8 |   76.5
```
- 8 failures: 全 zombie_empty_completion, glm5_2_nv, big_input (>131K chars)
- 15 ATE rows: ALL status=200 phantom (peer-fb rescued)
- 0 real ATE (status=502)
- dsv4p_nv: 2/2 OK, avg 30487ms (ATE phantom from peer-fb rescue)
- glm5_2_nv success: 24 OK, avg 9910ms, max 26165ms
- 6/6 peer-fb 100% success (logs confirm)
- key_cycle_429s: 19次 (glm5_2_nv, 1 cycle each — normal)

### 1h/30min
```
 1h: 5/5 (100% SR)
30min: 3/3 (100% SR)
```

### 容器环境 (compose==live env, 零漂移)
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

1. **新错误类型** ❌ — 无。8 zombie 全 glm5_2_nv NVCF function-level empty200 degradation, 与R1944/R1943/R1942/R1941相同。
2. **可配置修复的错误** ❌ — 无。僵尸=NVCF空200, 非配置可达。BREAKER已正确处理 (FAIL_N=1, COOLDOWN=21600) → peer-fb rescue (100% 成功)。
3. **参数未到 floor** ❌ — 全部已到 floor。FASTBREAK=1不可再降, KEY_COOLDOWN=60不可再降(NVCF窗口), UPSTREAM=30不可再降 (max OK=26.2s margin 3.8s), STREAM_TOTAL=25不可再降, PEER_FALLBACK=122不可再降 (HM2_BUDGET=120+2 constraint), BUDGET=152不可再降 (UPSTREAM 30+PEER 122=152 boundary)。
4. **BREAKER异常** ❌ — 无。BIG_INPUT正确触发 (FAIL_N=1, COOLDOWN=21600), peer-fb 100% rescue。

## 判决: NOP

四条全不满足，NOP 无据不改。8 zombie 是 NVCF glm5_2_nv function-level 空200 劣化，不是 HM1 配置可修复的。Breaker 正确将 big_input zombie 转为 peer-fb → HM2 rescue (100% success)。SR 76.5% 是 NVCF 后端约束，非配置可达。

R1941→R1942→R1943→R1944→R1945 连续五轮 NOP: glm5_2 big_input zombie 模式稳定, breaker+peer-fb 全路径100%成功。等待 NVCF 恢复后 breaker 自然 CLOSED。

## 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
