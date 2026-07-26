# R2393: HM2 → HM1 — NVU_STREAM_FIRST_BYTE_DEADLINE_S 15→18

## 本轮数据

| 指标 | 4h |
|------|-----|
| **总请求** | 42 |
| **成功率** | 73.8% (31/42) |
| **kimi_nv SR** | 78.3% (18/23) |
| **dsv4p_nv SR** | 33.3% (1/3) |
| **glm5_2_nv SR** | 75.0% (12/16) |

| 错误类型 | 4h 计数 |
|----------|---------|
| all_tiers_exhausted | 6 |
| zombie_empty_completion | 5 |
| (无错误/成功) | 31 |

### nv_tier_attempts 4h

| 错误类型 | 计数 |
|----------|------|
| empty_200 | 20 |
| NVCFPexecRemoteDisconnected | 9 |
| 429_nv_rate_limit | 2 |
| 504_nv_gateway_timeout | 1 |
| NVCFPexecTimeout | 1 |

### 延迟分布

| 模型 | 状态 | avg_duration | avg_ttfb | min | max |
|------|------|-------------|----------|-----|-----|
| kimi_nv | 200 | 104s | 103s | 7s | 269s |
| kimi_nv | 502 | 307s | 195s | 196s | 344s |
| glm5_2_nv | 200 | 10s | 10s | 3.8s | 20s |
| glm5_2_nv | 502 | 12.7s | 12.7s | 4.1s | 34s |
| dsv4p_nv | 200 | 222s | 222s | — | — |
| dsv4p_nv | 502 | 127s | — | 126s | 128s |

## 根因分析

- **nv_gw 5分钟前重启**（R2392 EMPTY_200_FASTBREAK 5→3 生效），日志无 error/warn。
- **empty_200 仍是主导 tier 级错误**（20/33 = 60.6%），R2392 的 FASTBREAK=3 尚未在 4h 窗口内充分验证（nv_gw 刚重启）。关键观察：empty_200 DOMINANCE 说明 NVCF 集群仍在返回空体，FASTBREAK=3 应能更快跳出。
- **NVU_STREAM_FIRST_BYTE_DEADLINE_S=15** 可能过紧：kimi_nv 成功请求的 avg_ttfb=103s，但还存在 15s 边界情况。thinking 模型（kimi）在 15-18s 的静默间隙很常见。15s deadline 可能截断正常 thinking 前置阶段，触发不必要的 RemoteDisconnected/empty_200。
- **RemoteDisconnected 9 次**：NVCF 端主动断开，可能是 deadline 过紧导致 upstream 在客户端 deadline 到期前被中断。
- **tiers_tried_count=1 全部**：所有 502 请求仅尝试了 1 个 tier。说明在第一个 tier 内所有 key 已被耗尽，与 empty_200 主导匹配。

## 优化计划

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| `NVU_STREAM_FIRST_BYTE_DEADLINE_S` | 15 | 18 | 15s 可能 clip kimi_nv thinking 模型正常的 15-18s 静默间隙。18s 是保守 +20% 增量，不显著增加 budget 消耗。kimi_nv 成功 avg_ttfb=103s 远高于 18s，说明正常请求不受影响。empty_200 + RemoteDisconnected 与 first-byte deadline 无关，不会被此改动恶化。单参数改动；铁律：只改HM1。 |

## 铁律声明
- **只改HM1 配置，绝不动HM2 本地。**
- **单参数微调，多轮积累，观察稳定后再扩。**
- HM1 `nv_gw` 已于 2026-07-27T04:55Z 重启生效。

## 实施验证
1. `docker-compose.yml` `NVU_STREAM_FIRST_BYTE_DEADLINE_S=15` → `18`
2. `docker compose up -d nv_gw` → 重启成功
3. `curl localhost:40006/health` → 200
4. `docker exec nv_gw env | grep FIRST_BYTE` → 18 ✓

## ⏳ 轮到HM1优化HM2