# HM2 Optimize HM1 — Round R1303

## Decision: NOP (false trigger, double-dispatch, 17th consecutive post-R1286)

### 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"` — 自提交误触发
- 最新 commit author = `opc2_uname` (HM2)
- HM1 本地 git log 停留在 R1206（97 轮落后）
- R1302 已由预运行脚本提交 → double-dispatch
- 确认：false trigger，无 HM1 新提交

### 数据收集 (改前必有数据)

**6h 总体**: 37req/27OK/10fail = 73.0% SR (identical to R1302)
- 全部流量: glm5_2_nv integrate only
- 全部 10 失败: `zombie_empty_completion` (NVCF content-filter stop+12chars, avg_ichars=215K, avg_dur=4995ms)
- 0 ATE, 0 NVStream_IncompleteRead, 0 fallback
- 0 tier_attempts, 0 key_cycle_429s
- dsv4p_nv: 0 traffic, kimi_nv: 0 traffic
- ms_gw: 0 traffic — ms_requests 0 rows, no fallback activity

**容器状态**:
- nv_gw Up 3 hours (healthy), restarted 2026-07-13T22:14:51Z
- All post-restart data, no pre-restart contamination

**Compose md5**: `6e1b58bc70eca49e500e3034b08376d9` — stable, identical to R1302

**关键参数** (docker exec nv_gw env):
- UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=205
- TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
- NVU_EMPTY_200_FASTBREAK=2, NVU_PEXEC_TIMEOUT_FASTBREAK=1
- MIN_OUTBOUND_INTERVAL_S=0, KEY_AUTHFAIL_COOLDOWN_S=60
- NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
- All params floor/optimal

### NV-ZOMBIE log pattern
```
[NV-ZOMBIE-EMPTY] glm5_2_nv passthrough, finish_reason=stop, content_chars=12<50, 
   input_chars~225K >=5000, no tool_calls — abort+error-chunk → openclaw fallback
```
Gateway detection correct. Error chunk sent. Content-filter signal → 502 in ~5s (vs old 96s timeout). Not config-fixable.

### 优化分析
- Zombie content-filter: NVCF upstream behavior, not nv_gw config fixable
- All tunable params at floor/optimal
- ms_gw idle (0 traffic) — no secondary optimization target
- No parameter space to explore

### Decision: Zero param, Zero compose change, Zero container restart

铁律:只改HM1不改HM2

## ⏳ 轮到HM1优化HM2
