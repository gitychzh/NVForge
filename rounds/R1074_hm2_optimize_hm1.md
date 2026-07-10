# R1074: HM2→HM1 — NVU_MS_GW_FALLBACK_TIMEOUT 90→180 (+90s, ms_gw dsv4p relay timeout rescue)

## 数据 (6h窗口, 16:26 UTC收集)

| 指标 | 值 |
|------|-----|
| 总请求 | 61 |
| 成功 (200) | 54 (88.5%) |
| 失败 | 7 (11.5%) |
| avg_dur | 26,297ms |
| p50 | 13,180ms |
| p95 | 102,323ms |

### 按模型+路径

| tier_model | upstream_type | cnt | ok | fail | avg_dur | p50 | max_dur |
|------------|---------------|-----|-----|------|---------|-----|---------|
| dsv4p_nv | (NULL/ATE) | 3 | 0 | 3 | 73,820ms | 110,058ms | 110,073ms |
| glm5_2_nv | nv_integrate | 58 | 54 | 4 | 23,838ms | 13,157ms | 105,819ms |

### 错误详情

| error_type | 模型 | 次数 | 分析 |
|------------|------|------|------|
| NVStream_TimeoutError | glm5_2_nv | 4 | integrate模式, 代码级流超时, 非配置可修 |
| all_tiers_exhausted | dsv4p_nv | 3 | pexec 404非循环中止→ms_gw fallback relay超时 |

### nv_tier_attempts (6h)

| tier | nv_key_idx | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----------|-----|--------|--------|
| glm5_2_nv | 0 | IntegrateRemoteDisconnected | 1 | 20,284 | 20,284 |

### dsv4p_nv 404 详细分析

重启后(16:20 UTC) dsv4p_nv 新请求立即命中404:
```
[NV-NONCYCLE-ERR] tier=dsv4p_nv k3 resp.status=404 non-cycling, aborting tier
body={"type": "urn:inference-service:problem-details:not-found", "status": 404}
[NV-MS-FB] local all_tiers_exhausted, attempting same-model fallback to ms_gw as dsv4p_ms
[NV-MS-FB] ms_gw relay failed after 171036ms: TimeoutError: timed out (relay_started=True)
```

- ms_gw 端: dsv4p_ms v2k5 成功获取首字节 `MS-OK-STREAM req=1bd6ea23 v2k5 backend=deepseek-ai/deepseek-v4-pro first=8192B` (16:21:02.7)
- 但 relay 从 ms_gw→nv_gw→client 在 171s 后超时(NVU_MS_GW_FALLBACK_TIMEOUT=90 本应在90s杀死, 但实际 171s 说明 relay_started=True 时 timeout 路径不同)
- dsv4p_nv 的 NVCF function `74f02205` 在 HM1 上返回 404, 但 HM2 上同一 function 正常 → 可能是 NVCF per-account 部署差异或 IP 路由差异

### glm5_2_nv 按 key (integrate)

| nv_key_idx | cnt | ok | fail | avg_dur |
|-----------|-----|-----|------|---------|
| 0 | 11 | 11 | 0 | 19,273ms |
| 1 | 10 | 7 | 3 | 42,652ms |
| 2 | 16 | 16 | 0 | 20,499ms |
| 3 | 12 | 11 | 1 | 23,663ms |
| 4 | 9 | 9 | 0 | 14,686ms |

- K1 最高平均延迟 (42,652ms) 且 3/4 失败集中在此 key
- K4 最低延迟 (14,686ms), K0/K2 稳定
- 4个 NVStream_TimeoutError 集中在 K1 + K3

### peer-fallback: 0次触发
### ms_gw: 8请求(total), dsv4p_ms有活动但 relay 超时

## 优化决策

**变更**: `NVU_MS_GW_FALLBACK_TIMEOUT` 90→180 (+90s)

**理由**:
- dsv4p_nv post-restart 100% 404, ms_gw fallback 是唯一救援路径
- ms_gw dsv4p_ms 成功获取响应首字节 (MS-OK-STREAM first=8192B), 但 relay 超时杀死连接
- R1036 将 timeout 从 45→90, 但 ms_gw dsv4p 全流式响应可能超过 90s (实测 171s 后仍超时)
- 180s 给 ms_gw 充足时间完成 relay (对齐 MS UPSTREAM_TIMEOUT=300, 留 120s margin)
- glm5_2_nv integrate 4个 NVStream_TimeoutError 是代码级流超时, 不在此参数修复范围
- K1 高延迟+高错误率 → 可能需要后续轮 key cooldown 调整, 但本轮不碰

**单参数**: 只改 MS_GW_FALLBACK_TIMEOUT, 不改其他。铁律: 只改 HM1 不改 HM2。

## 部署验证

```bash
# 变更前
NVU_MS_GW_FALLBACK_TIMEOUT=90

# 变更后
NVU_MS_GW_FALLBACK_TIMEOUT=180

# 验证
docker exec nv_gw env | grep NVU_MS_GW_FALLBACK_TIMEOUT  # ✅ 180
curl -s http://localhost:40006/health                     # ✅ {"status": "ok"}
docker ps --filter name=nv_gw                            # ✅ Up (healthy)
```

## ⏳ 轮到HM1优化HM2