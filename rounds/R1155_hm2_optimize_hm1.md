# HM2 Optimize HM1 — Round R1155

## 1. 触发分析
- **cron 脚本输出**: "这是我提交的, 不触发"
- 最新 commit: 759c867 (R1154, opc2_uname) — HM2 自提交
- **结论: FALSE TRIGGER** — HM1 未提交新 commit，cron 误派遣
- HM1 本地 git log: 停留在 R821 (opc_uname, 333 rounds behind)

## 2. 数据收集 (改前必有数据)

### 2.1 容器状态
- 容器: nv_gw, 重启于 2026-07-10T19:03:27Z (~16h ago)
- Compose MD5: 7975939c245761e451a8813852dcb9bf (unchanged, same as R1154)
- 日志: NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK 模式 → openclaw fallback 触发

### 2.2 6h 总体
- 45req / 24OK(53.3%SR) / 21fail
- 全部 nv_integrate, 全部 glm5_2_nv
- dsv4p_nv: 0 traffic 6h

### 2.3 错误分类
- 21 zombie_empty_completion (100% of failures)
- Tier attempts: 3× 429_integrate_rate_limit (glm5_2_nv)
- Fallback: 0 occurred (FALLBACK_GRAPH={}, 预期行为)

### 2.4 僵尸详情
- glm5_2_nv integrate, NVCF content-filter 返回 stop+12chars (165K-166K input)
- avg_dur=4,374ms, max_dur=12,569ms
- Gateway 正确检测 → error-chunk → openclaw fallback

### 2.5 当前参数 (全部 floor/optimal)
- UPSTREAM_TIMEOUT=66, BUDGET=198, TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25
- FASTBREAK: pexec=1, empty200=2, integrate=1
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv
- NVU_TIER_BUDGET_DSV4P_NV=72
- NVU_MS_GW_FALLBACK_TIMEOUT=180, NVU_PEER_FALLBACK_TIMEOUT=66
- KEY_AUTHFAIL_COOLDOWN_S=60

### 2.6 ms_gw
- 6h: 0 requests (未被使用)
- ms_gw EMPTY_200_FASTBREAK_THRESHOLD=3 (floor)

## 3. 决策: NOP (Zero Param)

### 3.1 原因
1. **全部失败为 zombie_empty_completion** — NVCF content-filter 返回 stop+12chars 对 165K+ 输入
2. Gateway 检测+error-chunk 正确 → openclaw 自动 fallback
3. 所有参数已 floor/optimal — 无优化空间
4. dsv4p_nv 0 traffic — 无数据支持优化
5. ms_gw 0 traffic — 无优化机会
6. Tier attempts 仅 3× 429 rate limit (正常)

### 3.2 铁律
- 只改HM1不改HM2 ✅
- 改前必有数据 ✅
- 无参数调整

## ⏳ 轮到HM1优化HM2
