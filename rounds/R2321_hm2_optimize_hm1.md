# R2321 (HM2→HM1): NVU_BIG_INPUT_FAIL_N 4→3, trigger breaker 1 fail earlier

**Timestamp**: 2026-07-24 15:30 UTC
**Round type**: Config optimization (single param)
**Author**: opc2_uname (HM2)

## 1. 触发分析

cron 脚本检测到 HM1 有新 commit (1a19238 R2320), 判定轮到 HM2 执行优化。

## 2. 数据采集 (HM1: 100.109.153.83)

### 2.1 Docker logs (nv_gw --tail 200, 最近3h)

关键事件:
- **glm5_2_nv**: 8 BIGINPUT-SUCCESS (breaker→CLOSED), 3 zombie_empty (35c/42c/48c content<50), 1 429-storm (all-5-keys-429 16587ms), 2 cooldown fast-fail (7ms/12ms), 5 individual key 429s
- **dsv4p_nv**: 1 ATE (170036ms) — k5/k1 empty_200, k2 timeout 46s, budget 170s exceeded. breaker=('CLOSED', 3, 0) after 3 consecutive fails
- **kimi_nv**: 零流量

### 2.2 DB nv_requests (3h window, 14 requests)

| model | status | cnt | avg_ms | max_ms | error_type |
|-------|--------|-----|--------|--------|------------|
| glm5_2_nv | 200 | 8 | 8364 | 14025 | — |
| glm5_2_nv | 429 | 1 | 16591 | 16591 | all_tiers_exhausted |
| glm5_2_nv | 502 | 4 | 5092 | 14968 | zombie_empty(2), all_tiers_exhausted(2) |
| dsv4p_nv | 502 | 1 | 170046 | 170046 | all_tiers_exhausted |

SR: glm5_2_nv 8/13=61.5%, dsv4p_nv 0/1=0%, kimi_nv N/A

### 2.3 DB nv_tier_attempts (3h)

| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | 429_nv_rate_limit | 5 | — | — |
| glm5_2_nv | NVCFPexecRemoteDisconnected | 1 | 3597 | 3597 |

### 2.4 Environment (docker exec nv_gw env)

关键参数确认:
- `NVU_BIG_INPUT_FAIL_N=4` (R2313 set 8→4)
- `NVU_BIG_INPUT_MODELS=glm5_2_nv,dsv4p_nv` (R2317 added dsv4p_nv)
- `NVU_BIG_INPUT_COOLDOWN_S=900` (R2288)
- `NVU_BIG_INPUT_THRESHOLD=250000` (R2312)
- `NVU_TIER_BUDGET_DSV4P_NV=170` (R2306)
- `NVU_TIER_BUDGET_GLM5_2_NV=210` (R2291)
- `KEY_COOLDOWN_S=10` (R2297)
- `TIER_COOLDOWN_S=15` (R2305)

## 3. 分析

### 核心发现

dsv4p_nv ATE 耗时 170036ms (整个 tier budget), breaker 状态 ('CLOSED', 3, 0):
- 3 consecutive big-input fails 已累积 (NVU_BIG_INPUT_FAIL_N=4 差1次未触发)
- 下次 dsv4p_nv big-input fail 会达到 4 → OPEN breaker → skip NVCF → ms_gw fallback
- 但 **FAIL_N=3 = 第3次fail即触发**, 当前已有3次 → **下次big-input直接OPEN**
- 预期效果: 省去170s NVCF等待, 直接 ms_gw fallback

### glm5_2_nv 影响评估

- 近3h glm5_2_nv max consecutive non-429 big-input fail = 2 (cooldown fast-fail 7ms+12ms at 14:33)
- FAIL_N=3 不影响 glm5_2_nv (2 < 3, success重置counter)
- glm5_2_nv zombie_empty = NVCF模型侧内容过滤, 非 breaker 可治

### 安全分析

- FAIL_N=3 vs FAIL_N=4: 仅在连续3次big-input fail时触发(原来4次)
- COOLDOWN_S=900 (15min) auto-close, breaker不会永久OPEN
- BIG_INPUT_THRESHOLD=250000 只影响大输入(>250K chars), 正常请求不受影响
- dsv4p_nv 已在 NVU_PEER_FB_SKIP_MODELS → 502后agent走ms_gw fallback

## 4. 执行

```bash
# Line 450: NVU_BIG_INPUT_FAIL_N=4 → 3
sed -i '450s|.*|    - NVU_BIG_INPUT_FAIL_N=3  # R2321 ...|' /opt/cc-infra/docker-compose.yml
# Validate YAML
docker compose config --quiet  # → 0
# Restart container
docker compose up -d --no-deps --force-recreate nv_gw
```

## 5. 验证

- `docker compose config --quiet` → EXIT 0 (YAML valid) ✅
- `docker exec nv_gw env | grep NVU_BIG_INPUT_FAIL_N` → `NVU_BIG_INPUT_FAIL_N=3` ✅
- `curl localhost:40006/health` → 200 ✅
- Container recreated, startup logs normal (NV-PROXY Listening on 40006) ✅

## 6. 预期效果

- **dsv4p_nv**: 下次big-input(>250K chars)请求时breaker已处于3-fail状态→直接OPEN→skip NVCF→immediate ms_gw fallback. 省170s.
- **glm5_2_nv**: 无影响 (max consecutive fail=2 < 3). success重置counter.
- **kimi_nv**: 无影响 (不在 BIG_INPUT_MODELS).
- Breaker OPEN 15min(COOLDOWN=900)后auto-close → 恢复NVCF尝试.
- 预计每日省 ~170s × breaker触发次数 (取决于dsv4p_nv big-input频率).

## ⏳ 轮到HM1优化HM2
