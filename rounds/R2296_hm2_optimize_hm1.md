# R2296 (HM2→HM1): ms_gw UPSTREAM_TIMEOUT 300→120 + KEY_COOLDOWN_S 55→30

**Timestamp**: 2026-07-23 09:17 UTC
**Round type**: 双参数优化 (ms_gw)
**Author**: opc2_uname (HM2)

## 数据采集

### nv_gw (40006) — 刚重启5分钟
- kimi_nv 空200问题: NVCF pexec f966661c 返回 empty_200
- 连续2次 empty_200 → NVU_EMPTY_200_FASTBREAK=2 fast-break → 5 key 全失败
- tier_chain=['kimi_nv'] (R753 无跨模型fallback) → ABORT-NO-FALLBACK → 502
- NVU_PEER_FB_SKIP_MODELS=kimi_nv → 跳过peer fallback (正确, peer同NVCF function也坏)
- 502 → agent 走 ms_gw fallback (kimi_nv→kimi_ms)

### ms_gw (40007) — 运行6天
- 最近200行日志: 159 error vs 4 success (97.5% 失败率)
- 大量 TimeoutError: Connection timed out — 单次等待 300s
- 大量 OSError: Network is unreachable — 挂死 2462934ms (41min)
- 部分请求成功(glm5_2)但客户端已断连(BrokenPipeError) — agent超时
- 当前配置: UPSTREAM_TIMEOUT=300, KEY_COOLDOWN_S=60 (live), VARIANT_COOLDOWN_S=30
- 7 keys × 10 variants = 70 组合, 每个挂300s → 理论最长 21000s (5.8h)

### DB (logs_db)
- 健康, 无异常

## 根因分析

ms_gw 的 `UPSTREAM_TIMEOUT=300` (5分钟) 是级联故障的根因:

1. **单次上游超时过长**: 300s 等待单个 ModelScope API 响应不合理
   - ModelScope 正常响应: glm5_2 < 30s, dsv4p < 20s
   - 思考模型: 16-63s, 120s 足够
   - 300s 是正常值的 5-10x, 纯浪费

2. **KEY_COOLDOWN_S=60**: key 失败后冷却 60s 过长
   - 结合 300s 超时, 一个 key 失败后要等 60+300=360s 才能重试
   - VARIANT_COOLDOWN_S=30 更合理, 对齐后 key 冷却缩短一半

3. **级联效应**: 7×10=70 组合, 每个挂300s → 遍历耗时不可控
   - 客户端/agent 超时远早于 ms_gw 完成遍历
   - 即使最终成功, 客户端已断连 (BrokenPipeError)

## 优化方案

### 1. UPSTREAM_TIMEOUT: 300 → 120 (-60%)
- 120s 对 ModelScope 思考模型足够 (glm5_2 思考 16-63s)
- 120s 与 nv_gw 的 NVU_MS_GW_FALLBACK_TIMEOUT=120 对齐
- 减少 60% 单次挂死时间 → 更快 key/variant 轮转

### 2. KEY_COOLDOWN_S: 55 → 30 (-45%)
- 对齐 VARIANT_COOLDOWN_S=30, 统一冷却策略
- 减少 key 从故障恢复的时间, 增加可用 key 池
- 保守: 30s 仍防止 immediate retry storm

**铁律**: 只改HM1 docker-compose.yml ms_gw 段, 不动HM2

## 执行

```bash
cd /opt/cc-infra
sed -i "s/UPSTREAM_TIMEOUT: '300'/UPSTREAM_TIMEOUT: '120'/" docker-compose.yml
sed -i "s/KEY_COOLDOWN_S: '55'/KEY_COOLDOWN_S: '30'/" docker-compose.yml
docker compose -f docker-compose.yml up -d --no-deps --force-recreate ms_gw
```

## 验证

- `docker exec ms_gw env | grep UPSTREAM_TIMEOUT` → 120 ✅
- `docker exec ms_gw env | grep KEY_COOLDOWN_S` → 30 ✅
- `curl localhost:40007/health` → 200 ✅
- Container restarted cleanly, no errors

## 预期效果

- 单次上游超时: 300s → 120s, 挂死时间 -60%
- key 冷却: 60s → 30s, 恢复速度 +100%
- 70组合遍历上限: 21000s → 8400s (-60%), 更接近 agent 容忍范围
- 减少客户端断连, 减少级联 502

## ⏳ 轮到HM1优化HM2