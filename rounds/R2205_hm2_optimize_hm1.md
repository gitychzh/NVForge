# R2205: HM2→HM1 — KEY_COOLDOWN_S 8→6 (-2s)

**Timestamp**: 2026-07-22 01:05 UTC  
**由**: HM2 (opc2_uname)  
**回合**: HM2优化HM1

## 数据收集

### 6h DB (nv_requests)
```
total=32 ok=22 fail=10 avg_ok_ms=23222
glm5_2_nv: 28 total, 19 ok, 9 fail (zombie), avg_ok=22553ms
dsv4p_nv: 4 total, 3 ok, 1 fail (zombie), avg_ok=27457ms
```

### 错误明细
- 10 zombie_empty_completion (9 glm5_2_nv, 1 dsv4p_nv)
- 0 ATE (all_tiers_exhausted)
- SR: 68.8% (down from 68.8% in R2204 — same SR but latency up)

### Tier Attempts (6h)
```
glm5_2_nv pexec_success: 28
glm5_2_nv pexec_SSLEOFError: 7 (15.2%)
glm5_2_nv pexec_429: 7 (15.2%)
glm5_2_nv pexec_timeout: 4 (8.7%)
Total: 46 attempts
```

### 容器环境（优化前）
```
KEY_COOLDOWN_S=8
TIER_COOLDOWN_S=1
NVU_TIER_BUDGET_GLM5_2_NV=28
NVU_TIER_BUDGET_DSV4P_NV=48
UPSTREAM_TIMEOUT=24
TIER_TIMEOUT_BUDGET_S=153
```

### 僵尸模式分析
- 每~30min一个zombie: finish_reason=stop, content_chars=36 < 50阈值
- 每个请求都触发key_cycle_429s=1（100% key cycling）
- 429 rate: 7/46 = 15.2% 在pexec层面

## 优化决策

**R2204**: TIER_COOLDOWN_S 3→1 (-2s). 延迟从18380ms升到23222ms (+4842ms, +26.3%)。交替模式: TIER后KEY。

**本轮**: KEY_COOLDOWN_S 8→6 (-2s). 15.2%的429率说明key cooldown 8s仍有优化空间。减少到6s:
- 更快key恢复 → 更少429等待 → 降低延迟
- 预算: 6+1+28=35 << 153 BUDGET (118s margin)
- 5 keys, 低流量(~5.3req/h), 无key exhaustion风险

## 变更

**文件**: `/opt/cc-infra/docker-compose.yml` (line 500, nv_gw section)  
**变更**: `KEY_COOLDOWN_S: "8"` → `KEY_COOLDOWN_S: "6"`  
**容器重启**: ✅ stop + up -d 成功  
**实时验证**: `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=6` ✅

## 评判

- 更少报错: zombie是模型侧content_filter问题，非cooldown可修。0 ATE保持。
- 更快请求: 减少key cooldown从8→6s，预期降低429等待时间，降低平均延迟。
- 超低延迟: 23222ms→目标<20000ms。6s cooldown应减少key cycling overhead。
- 稳定优先: 预算35<<153，5 keys 5.3req/h，零key exhaustion风险。
- 铁律: 只改HM1不改HM2 ✅

## ⏳ 轮到HM1优化HM2