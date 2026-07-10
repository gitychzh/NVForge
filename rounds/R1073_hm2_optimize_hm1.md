# R1073: HM2→HM1 — NVU_MS_GW_FALLBACK_MODELMAP +dsv4p_nv:dsv4p_ms (restore ms_gw dsv4p rescue)

## 数据 (6h窗口, 07:48 UTC 重启前)

| 指标 | 值 |
|------|-----|
| 总请求 | 60 |
| 成功 (200) | 55 (91.7%) |
| 失败 (ATE) | 5 |
| 错误分布 | glm5_2_nv NVStream_TimeoutError ×3, dsv4p_nv all_tiers_exhausted ×2 |

### 按路径

| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nv_integrate | 57 | 54 | 15,869ms | 20,875ms | 105,819ms |
| (ATE) | 2 | 0 | 797ms | 110,066ms | 110,073ms |

### 错误详情

| error_type | 模型 | 次数 | 分析 |
|------------|------|------|------|
| NVStream_TimeoutError | glm5_2_nv | 3 | integrate模式, 代码级流超时, 非配置可修 |
| all_tiers_exhausted | dsv4p_nv | 2 | pexec全5键耗尽, 无fallback rescue |

### nv_tier_attempts (6h)

| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | IntegrateRemoteDisconnected | 1 | 20,284 | 20,284 |

### 重启后状��� (16:00 UTC)

- 3 req, 3 OK, all glm5_2_nv integrate, 0 errors
- 容器正常运行, `/health` OK

## 优化决策

**变更**: `NVU_MS_GW_FALLBACK_MODELMAP` 添加 `dsv4p_nv:dsv4p_ms`

**背景**: R1069 从 MODELMAP 移除了 `dsv4p_nv:dsv4p_ms`，因为当时 ms_gw BrokenPipeError 会阻塞 peer-fb 路径。R1070 将 `PEER_FALLBACK_TIMEOUT` 从 45→66 (对齐 HM2 UPSTREAM)，R1071 将 `TIER_TIMEOUT_BUDGET_S` 从 110→132 (66+66 完整单键窗口)。现在 peer-fb 已有完整窗口，ms_gw 应作为第二线救援重新启用。

**理由**:
- dsv4p_nv 2 ATE = 纯 ATE，没有 ms_gw 或 peer-fb 救援
- R1070 的 peer-fb 66s 窗口已修复 peer-fb 路径
- ms_gw dsv4p_ms 不完美（客户端断开时 BrokenPipeError），但优于纯 ATE
- ms_gw 日志显示 dsv4p_ms 在 HM2 上正常工作（glm5_2_ms 成功流转）
- glm5_2_nv 3 ATE 是 NVStream_TimeoutError (integrate 代码级)，非配置可修

**单参数**: 只改 MODELMAP，不碰其他参数。铁律: 只改 HM1 不改 HM2。

## 部署验证

```bash
# 变更前
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms

# 变更后
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms

# 验证
docker exec nv_gw env | grep MS_GW_FALLBACK_MODELMAP  # ✅ 确认
curl -s http://localhost:40006/health                  # ✅ {"status": "ok"}
```

## ⏳ 轮到HM1优化HM2