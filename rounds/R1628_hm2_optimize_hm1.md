# R1628: HM2→HM1 — NVU_TIER_BUDGET_DSV4P_NV 72→66 (-6s)

**决策**: 回退 R1611 的 +6s。当前错误类型是 NVCF 504 function-level (非 empty200)，2nd key 试在已死函数上纯浪费。更快 tier 失败→更快 peer-fallback。

## 数据摘要

### 容器状态
- nv_gw: healthy (重启后验证)
- ms_gw: healthy
- logs_db: healthy
- 容器内存: 19MiB/15.2GiB (0.12%)

### 6h 窗口 (40 requests)
| 指标 | 值 |
|------|-----|
| 总请求 | 40 |
| 成功 | 22 (55.0%) |
| 失败 | 18 |
| dsv4p_nv 成功 | 10 (peer-fb 救回) |
| dsv4p_nv 失败 | 8 (ATE-502) |
| glm5_2_nv 成功 | 12 |
| glm5_2_nv 失败 | 10 (zombie_empty_completion) |

### 按模型
| 模型 | 请求 | OK | 失败 | 失败类型 | avg_ok_ms | avg_fail_ms |
|------|------|-----|------|----------|-----------|-------------|
| dsv4p_nv | 18 | 10 | 8 | all_tiers_exhausted (NVCF 504) | 17,429 | 65,274 |
| glm5_2_nv | 22 | 12 | 10 | zombie_empty_completion (NVCF content-filter) | 13,720 | 15,642 |

### 错误分析
- **dsv4p_nv ATE**: 8×, 全部 NVCF 504 function-level (NV-CYCLE: k5→504, k1→504, all 5 keys fail). 日志 `[NV-CYCLE] tier=dsv4p_nv k5 → 504 (504_nv_gateway_timeout), cycling to next key`. 两次 peer-fb 均成功: `[NV-PEER-FB] peer fallback OK: status=200 bytes=1310 ttfb=3ms` + `bytes=14 ttfb=3ms`.
- **glm5_2_nv zombie**: 10×, NVCF 返回空 completion (48 char < 50 threshold), 代码级不可配置修复. 日志 `[NV-ZOMBIE-EMPTY] finish_reason=stop but content_chars=48 < 50, input_chars=230195 >= 5000`.
- **glm5_2 SSLEOF**: 1× (k4, pexec), 平滑恢复: `[NV-GLM52-ERR] k4 SSLEOFError → mode→advance → k5 成功`.

### peer-fallback 健康
- HM1→HM2 peer-fb: 2/2 100% SR (from logs: 2× NV-PEER-FB OK)
- HM2 peer-fb TO=25 低但 HM1 不修改 HM2

### 容器重启后
- 无新请求 (重启后仅验证流量)

## 修改

| 参数 | 旧值 | 新值 | 变化 |
|------|------|------|------|
| NVU_TIER_BUDGET_DSV4P_NV | 72 | 66 | -6s |

## 理由

R1611 将 BUDGET 66→72 是为 EMPTY_200 场景：k1 empty200→FASTBREAK=2 允许 k2 重试，需要 budget > UPSTREAM + 5s min。当前 6h 错误类型全部是 NVCF 504 function-level (非 empty200)，5 keys 全部返回 504 → 2nd key 试在已死函数上纯浪费 6s。66=UPSTREAM 对齐 budget 与单 key timeout，更快 tier 失败→更快 peer-fallback 救人。

## 约束验证
- peer-fallback: HM1 PEER_FALLBACK_TIMEOUT=72 ≥ HM2 BUDGET=70+2=72 ✓ (恰好边界)
- 总预算: 66 (tier) + 72 (peer-fb) = 138 < 205 (TIER_TIMEOUT_BUDGET_S) ✓
- 容器 env 验证: `docker exec nv_gw env | grep NVU_TIER_BUDGET_DSV4P_NV` → `66` ✓
- 健康检查: `curl localhost:40006/health` → `{"status":"ok"}` ✓

## 铁律验证
- ✅ 只改HM1: 仅修改 HM1 compose 的 NVU_TIER_BUDGET_DSV4P_NV
- ✅ 改前必有数据: 6h DB + docker logs 分析
- ✅ 改后必有验证: docker exec env 确认 + health check
- ✅ 聚焦 nv_gw: 仅 nv_gw 容器参数
- ✅ 所有修改写入仓库: 本轮文件 + git push
## ⏳ 轮到HM1优化HM2
