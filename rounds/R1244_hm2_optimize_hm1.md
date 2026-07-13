# HM2 Optimize HM1 — Round R1244

## 0. 触发判定
- 预运行脚本: `HEAD at 6ba9efb (R1243: openclaw contextWindow)` — 用户指示执行
- 触发类型: **HM2→HM1 优化轮次** (HM1提交了新commit到GitHub)
- 本轮编号: R1244 (R1243 被 openclaw contextWindow 占用)

## 1. 数据收集 (改前必有数据)
HM1 数据采集时间: 2026-07-13 21:20 UTC

### 6h DB 全景
| 指标 | 值 |
|------|-----|
| 总请求 | 138 |
| 成功 (200) | 107 |
| 失败 | 31 |
| SR | 77.5% |
| 平均 TTFB | 29,948ms |
| 平均耗时 | 42,054ms |
| 最大耗时 | 188,328ms |

### 3h DB 窗口 (近期趋势改善)
| 指标 | 值 |
|------|-----|
| 总请求 | 66 |
| 成功 (200) | 56 |
| 失败 | 10 |
| SR | 84.8% |
| 平均 TTFB | 11,439ms |
| 平均耗时 | 13,594ms |

### 错误分类 (6h)
| 错误类型 | 数量 | 平均耗时 | 最大耗时 |
|---------|------|---------|---------|
| zombie_empty_completion | 16 | 23,932ms | 109,395ms |
| all_tiers_exhausted | 14 | 108,693ms | 188,328ms |
| NVStream_IncompleteRead | 1 | 50,718ms | 50,718ms |

### ATE 按模型分析
| 模型 | 数量 | 平均耗时 | 根因 |
|------|------|---------|------|
| glm5_2_nv | 9 | 126,894ms | 6× 404 NONCYCLE (3.8-7.5s fast fail) + 3× ms_gw TimeoutError 187-190s |
| dsv4p_nv | 5 | 75,929ms | 全在 08:17-10:07 窗口 (5h前), 近期 pexec 3/3 100% OK |

### zombie_empty_completion 分析
- 全部 glm5_2_nv: 15 integrate + 1 pexec
- NVCF 返回 `finish_reason=stop` + `content_chars < 50` + `input_chars >= 5000` + `no tool_calls`
- 网关发送 `content_filter` error SSE chunk 到 openclaw 触发 fallback
- **Not config-fixable**: NVCF 内容过滤问题, 非网关参数

### glm5_2_nv 404 错误 (R1241 延续)
```
20:33:27 integrate k5 → 404
20:33:29 pexec    k4 → 404
20:37:18 integrate k1 → 404
20:37:38 integrate k3 → 404
20:37:57 integrate k4 → 404
20:37:59 pexec    k2 → 404
20:38:23 integrate k5 → 404
20:39:26 integrate k3 → 404
20:39:28 pexec    k4 → 404
```
- NVCF glm5_2 function `3b9748d8` 间歇返回 404 (integrate+pexec 双路径)
- NONCYCLE 正确 (省 ~21s/key), 但 integrate→pexec fallback 也 404
- ms_gw fallback: 两个大请求 187,908ms / 190,186ms TimeoutError (relay_started=True)
- **Not config-fixable**: NVCF 侧 function 降级

### ms_gw 状态 (健康)
```
20:33:40 MS-OK-STREAM glm5_2_ms 33,600b 2.3s
20:35:46 MS-OK-STREAM glm5_2_ms 23,703b 1.2s
20:38:03 MS-OK-STREAM glm5_2_ms 49,080b 4.0s
20:39:36 MS-OK-STREAM glm5_2_ms 33,691b 2.3s
20:42:34 MS-OK-STREAM glm5_2_ms 3,184B+ (streaming)
```
- ms_gw 本身健康: 所有 MS-OK-STREAM, 3-34s 完成
- 问题: 大请求 relay 到 ms_gw 时 `NVU_MS_GW_FALLBACK_TIMEOUT=180` 超时截断

### 关键发现: ms_gw fallback 超时边界
- 两个 glm5_2_nv ATE 在 ms_gw relay 阶段超时: 187,908ms / 190,186ms
- 当前 `NVU_MS_GW_FALLBACK_TIMEOUT=180` → 截断点在 180s
- ms_gw 大请求 (140K+ 字符输入) 处理需要 100-200s (R1036 注释)
- `TIER_TIMEOUT_BUDGET_S=210` → ms_gw 实际可用: 210 - glm5_2_nv tier 消耗 (NONCYCLE 3-5s fast fail) = 205-207s
- 180s 超时过早截断, 187-190s 时请求几乎完成

## 2. 优化决策

### 参数: `NVU_MS_GW_FALLBACK_TIMEOUT` 180 → 200 (+20s)

**推理**:
1. glm5_2_nv 404 NONCYCLE 快速失败 (3-5s), 留出 205-207s 预算给 ms_gw
2. ms_gw 大请求处理 100-200s, 当前 180s 截断两个请求 (187,908ms / 190,186ms)
3. +20s → 200s 覆盖 ms_gw 大请求完整处理, 减少 TimeoutError
4. 配合 `TIER_TIMEOUT_BUDGET_S=210` 安全: 200s ms_gw + 5s glm5_2 404 = 205s ≤ 210s
5. 不影响 dsv4p_nv 路径: dsv4p_nv primary tier 有 `NVU_TIER_BUDGET_DSV4P_NV=72` 上限, 不进入 ms_gw fallback

**单参数**: 只改 `NVU_MS_GW_FALLBACK_TIMEOUT`, 铁律: 只改HM1不改HM2

**风险**: 低。ms_gw 健康, 大请求超时边界从 180s 推到 200s, 在 210s 预算内。

## 3. 执行记录

### 3.1 备份
```bash
cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.RN_hm2_optimize_hm1-pre-ms-gw-fb-timeout
```

### 3.2 配置变更
```yaml
# Line 670: /opt/cc-infra/docker-compose.yml
- NVU_MS_GW_FALLBACK_TIMEOUT: 180
+ NVU_MS_GW_FALLBACK_TIMEOUT: 200
```

### 3.3 重启
```bash
cd /opt/cc-infra && docker compose up -d nv_gw
# Container nv_gw Recreate → Recreated → Starting → Started
```

### 3.4 验证
- `docker exec nv_gw env | grep NVU_MS_GW_FALLBACK_TIMEOUT` → `200` ✓
- `curl http://localhost:40006/health` → `200 {"status": "ok"}` ✓
- `docker compose config --quiet` → YAML valid ✓
- `docker logs nv_gw --tail 5` → `[NV-PROXY] Listening on 0.0.0.0:40006` ✓

## 4. 效果预期
- ms_gw 大请求 TimeoutError 从 180s 截断 → 200s 完成
- ATE 中 ms_gw relay 超时类减少
- 成功路径、zombie_empty、404 均不受影响
- 下一轮观察: ms_gw fallback 成功率、glm5_2_nv ATE 平均耗时

## ⏳ 轮到HM1优化HM2