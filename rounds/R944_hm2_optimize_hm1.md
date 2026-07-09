# HM2 Optimize HM1 — Round R944

## ⚠️ 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = opc2_uname (HM2)
- R943 已在 08:25 完成（上一个 NOP 回合）
- cron 仍被派遣 — 误触发（double-dispatch）
- 61st consecutive NOP

## 数据收集 (改前必有数据)

### HM1 nv_gw 容器日志 (docker logs --tail 100)
```
(grep error|warn|fail|timeout|panic|fatal → 零输出)
```
零错误，零警告。

### HM1 nv_gw 环境变量
```
UPSTREAM_TIMEOUT=64
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64
TIER_TIMEOUT_BUDGET_S=114
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_EMPTY_200_FASTBREAK=3
NVU_PEXEC_TIMEOUT_FASTBREAK=1
FALLBACK_HEALTH_THRESHOLD=0.05
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_FORCE_STREAM_UPGRADE=0
NVU_CONNECT_RESERVE_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NV_INTEGRATE_MODELS=(空)
NVU_SSLEOF_RETRY_DELAY_S=1.0
TIER_COOLDOWN_S=25
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=45
```

### nv_requests 6h 统计
```
total | ok | fail | success_pct
    39 | 39 |    0 |       100.0
```
100% 成功率，零 ATE，零错误。

### 错误分类 (6h)
```
(0 rows) — 零错误
```

### 按路径分组 (6h)
```
upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur
nvcf_pexec    |  39 | 39 |     7401 |    7402 |   67241
```
全部 glm5_2_nv via nvcf_pexec，p50=4850ms，p95=15138ms。

### nv_tier_attempts (6h)
```
(0 rows) — 零 tier 重试
```

### ms_gw (6h)
```
total | ok | fail
     0 |  0 |    0
```
零请求，无优化空间。

## 决策: NOP

无参数需要调整。系统处于完美的零错误 regime:
- 39/39 100% SR，零 ATE，零 tier_attempts
- 容器日志零错误零警告
- 所有参数已在地板（UPSTREAM=64 aligned with FORCE_STREAM=64, BUDGET=114 充裕, KEY_COOLDOWN=25 地板, MIN_OUTBOUND=0 地板）
- ms_gw 零请求，无替代优化目标
- 延迟 p50=4850ms 合理，p95 长尾来自上游 NVCF 服务端波动（不可配置）

铁律验证: 只改HM1不改HM2 ✓（未做任何修改）

## ⏳ 轮到HM1优化HM2
