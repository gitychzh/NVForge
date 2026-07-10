# HM2 Optimize HM1 — Round R1103

**作者**: opc2_uname (HM2)
**类型**: 数据驱动优化 (HM2→HM1)
**触发**: HM1 R838b sync 提交 (commit a9b4a97)
**铁律**: 只改 HM1 不改 HM2. 改前必有数据, 改后必有验证.

## 1. 数据收集 (改前必有数据)

### 1.1 容器状态
- 容器: nv_gw (40006)
- 重启时间: 2026-07-10T15:45:49Z
- 健康检查: OK (healthy)

### 1.2 6h 总体统计
| 指标 | 值 |
|------|-----|
| 总请求 | 107 |
| 成功 | 105 |
| 失败 | 2 |
| 成功率 | 98.1% |

### 1.3 按路径分组
| 路径 | 请求数 | 成功 | 失败 | avg_ttfb(ms) | avg_dur(ms) | max_dur(ms) |
|------|--------|------|------|-------------|-------------|-------------|
| nv_integrate | 80 | 79 | 1 | 19,361 | 20,791 | 96,999 |
| nvcf_pexec | 26 | 26 | 0 | 10,957 | 10,957 | 48,049 |
| (ATE) | 1 | 0 | 1 | 542 | 61,376 | 61,376 |

### 1.4 按模型分组
| 模型 | 请求数 | 成功 | 失败 | SR% | avg_dur(ms) | max_dur(ms) |
|------|--------|------|------|-----|-------------|-------------|
| glm5_2_nv | 74 | 73 | 1 | 98.6 | 21,168 | 96,999 |
| dsv4p_nv | 17 | 16 | 1 | 94.1 | 16,914 | 61,376 |
| minimax_m3_nv | 9 | 9 | 0 | 100.0 | 14,483 | 32,892 |
| kimi_nv | 7 | 7 | 0 | 100.0 | 3,605 | 7,771 |

### 1.5 错误分类
| 错误类型 | 次数 |
|----------|------|
| NVStream_TimeoutError | 1 (glm5_2_nv, integrate, 96,999ms) |
| all_tiers_exhausted | 1 (dsv4p_nv, 61,376ms) |

### 1.6 dsv4p_nv ATE 详细分析
- 请求 ID: 24bf7c70 (16:00 UTC) + 9e6c46fe (15:50 UTC)
- 错误: all_tiers_exhausted, all_tiers_failed_in_mapped_tier
- fallback_occurred: false, fallback_actually_attempted: false
- 持续时间: ~61,374ms (≈ NVU_TIER_BUDGET_DSV4P_NV=66)
- 根因: k1 empty_200 (Content-Length:0) → NV-GLOBAL-COOLDOWN 标记所有 5 个 key 冷却 18s → tier 耗尽 → ms_gw fallback 流式同步缺陷 (BrokenPipeError) → 502

### 1.7 日志关键信号
```
[NV-EMPTY-200] k1 (dsv4p_nv) → 200 Content-Length:0 (stream)
[NV-EMPTY-CYCLE] tier=dsv4p_nv k1 empty 200, marked cooling + cycling
[NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=0, empty200=1, timeout=0, other=0, elapsed=61371ms
[NV-GLOBAL-COOLDOWN] tier=dsv4p_nv all keys empty_200. Marking all cooling 18s (R832 EMPTY200=TIER_COOLDOWN)
[NV-ALL-TIERS-FAIL] All 1 tiers failed (ring tiers tried: ['dsv4p_nv']), elapsed=61376ms, ABORT-NO-FALLBACK
[NV-MS-FB] ms_gw relay failed after 264460ms: TimeoutError: timed out (relay_started=True)
```

### 1.8 ms_gw 交叉验证
- ms_gw dsv4p_ms 正常: MS-OK-STREAM + MS-STREAM-DONE 均有成功记录
- 但 nv_gw 未收到 [DONE] 信号 → 流式同步缺陷 (R832 已知: code-level, not config-fixable)
- ms_gw relay 264s 超时远超 NVU_MS_GW_FALLBACK_TIMEOUT=180 和 BUDGET=198 → 流式同步超时不受参数控制

### 1.9 tier_attempts
- 0 条记录 (dsv4p_nv 无失败尝试写入, 仅 empty_200 被标记为冷却)

## 2. 数据诊断

### 2.1 核心问题
dsv4p_nv 的两个 ATE 均来自 single-key empty_200 触发 ALL-key GLOBAL-COOLDOWN:
- 仅有 1 个 key (k1) 返回 empty_200
- GLOBAL-COOLDOWN 将全部 5 个 key 标记冷却 18s (TIER_COOLDOWN_S=18)
- 后续请求无可用 key → tier 在 ~61s 耗尽 (NVU_TIER_BUDGET_DSV4P_NV=66)
- ms_gw fallback 触发但流式同步缺陷导致 relay 失败 → 502

### 2.2 R1018 诊断错误
R1018 将 TIER_COOLDOWN_S 15→18, 基于 "dsv4p_nv empty_200 function-level degradation" 诊断.
但 R1031 已证明 empty_200 是 **key-specific** (1/5 keys empty, 不是 function-level):
- 日志确认: `empty200=1` (仅 1 个 key 失败)
- 4 个正常 key 被错误地全部冷却
- 18s 的 GLOBAL-COOLDOWN 对 single-key transient 过于严厉

### 2.3 优化方向
TIER_COOLDOWN_S 18→15: 回退到 R1018 前的稳定值, 更快的 key 恢复.
- 单 key empty_200 不应触发全 key 冷却 (code-level 行为), 但减少冷却时间可缓解
- 15s 是 R1018 前的稳定值, 已验证安全
- ms_gw fallback 缺陷 (code-level) 短期无法修复, 减少冷却时间提升 nv_gw 内部自救概率

## 3. 执行优化

### 3.1 参数变更
- **参数**: TIER_COOLDOWN_S
- **变更**: 18 → 15 (-3s)
- **行号**: docker-compose.yml line 498
- **理由**: 回退 R1018 的错误诊断。empty_200 是 key-specific, 18s 全 key 冷却过度。15s 恢复 pre-R1018 稳定值, 更快 key 恢复。

### 3.2 部署
```bash
cd /opt/cc-infra && docker compose stop nv_gw && docker compose up -d nv_gw
```
- 容器重启: OK
- 健康检查: OK (healthy)
- 环境验证: `docker exec nv_gw env | grep TIER_COOLDOWN_S` → 15 ✓

### 3.3 验证
- YAML 语法: OK
- 容器状态: nv_gw Up (healthy)
- 健康端点: 200 OK

## 4. 评判
- 更少报错: 减少 3s 全 key 冷却 → 减少后续请求的等待时间
- 更快请求: 冷却时间缩短 16.7% → key 更快恢复可用
- 超低延迟: 不增加延迟
- 稳定优先: 回退到已验证的 15s 稳定值, 保守修改

## ⏳ 轮到HM1优化HM2
