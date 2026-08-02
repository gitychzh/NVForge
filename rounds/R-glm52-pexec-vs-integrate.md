# R-glm52-pexec-vs-integrate: glm5_2_nv pexec vs integrate 精准对比

**日期**: 2026-08-02
**主机**: HM2 (opc2sname)
**目标**: 确定 glm5_2_nv 走 pexec 还是 integrate 更稳, 是否交替错开更优

## 路由配置

| 路径 | Host | Path | SOCKS5 代理 | 出口 IP |
|---|---|---|---|---|
| pexec | api.nvcf.nvidia.com | /v2/nvcf/pexec/functions/{func_id} | 7900-7904 | 134.195.101.180/188/194, 203.10.96.139 |
| integrate | integrate.api.nvidia.com | /v1/chat/completions | 7894-7899 | 134.195.101.193/195/180 |

- function_id: b1b22d03-1ac7-4204-be9b-84ebb009e1a2 (mn-tp8-b200, 全 3 slot 绑同一个)
- 两条路径用**不同的 SOCKS5 代理端口和不同的出口 IP**, NVCF 后端也可能不同
- 当前配置 NV_INTEGRATE_MODELS=glm5_2_nv: 全 5 key 首选 integrate, 429 后 fallback pexec

## DB 7 天数据 (7017 pexec + 39 integrate)

| upstream_type | total | ok | SR% | avg_ms | p50_ms | p90_ms |
|---|---|---|---|---|---|---|
| nvcf_pexec | 7017 | 6951 | 99.1 | 39875 | 30874 | 78773 |
| nv_integrate | 39 | 39 | 100.0 | 12682 | 9150 | 23323 |

### pexec 错误分布 (66 次失败 / 7017 总)
| error_type | cnt |
|---|---|
| zombie_empty_completion | 35 |
| client_gone_during_flush | 9 |
| buffer_exhausted | 8 |
| NVStream_IncompleteRead | 6 |
| stream_absolute_cap | 5 |
| NVAnthCollect_IncompleteRead | 1 |
| stream_first_byte_timeout | 1 |
| all_tiers_exhausted | 1 |

**关键: 0 次 429, 0 次 529.** glm5_2_nv 不存在限流问题, pexec 失败全是连接级问题.

### 时间分布
- 7/28-7/31: 全走 pexec (7017 次), SR 99.1%, avg 39.9s
- 8/01 起: 切到 integrate (39 次), SR 100%, avg 12.7s
- pexec 失败分散在每小时 1-8 次, 无集中风暴

## 直连对比测试 (5 轮 × 5 key = 25 次/路径)

| 路径 | R1 | R2 | R3 | R4 | R5 | 总 SR | avg |
|---|---|---|---|---|---|---|---|
| integrate | 5/5 | 4/5 | 5/5 | 4/5 | 5/5 | **23/25=92%** | 6.1s |
| pexec | 5/5 | 4/5 | 2/5 | 4/5 | 3/5 | **18/25=72%** | 9.0s |

### 失败模式
- integrate: 2 次 SSL EOF (k5 重复出现)
- pexec: 7 次 "Remote end closed connection" (30-55s 超时), 集中在 k1/k3/k4

## 交替使用测试 (10 轮 × 5 key = 50 次/路径)

奇偶 key 交替走 pexec/integrate:

| 路径 | 成功 | 失败 | SR | avg |
|---|---|---|---|---|
| integrate | 25/25 | 0 | **100%** | 7.4s |
| pexec | 17/25 | 8 | **68%** | 8.4s |
| 合计 | 42/50 | 8 | 84% | — |

pexec 失败模式不变: 8 次 "Remote end closed / SSL EOF" (27-46s).

## 结论: integrate 明显更稳, 不需要交替

| 维度 | integrate | pexec |
|---|---|---|
| DB 7d SR | 100% (39/39) | 99.1% (6951/7017) |
| 直连测试 SR | 92-100% | 68-72% |
| avg latency | 6-13s | 8-40s |
| p50 / p90 | 9s / 23s | 31s / 79s |
| 429 限流 | 0 | 0 |
| 失败类型 | 偶发 SSL EOF | zombie/timeout/incomplete read |
| 出口 IP | 134.195.101.193/195 (稳定) | 134.195.101.180/188/194 + 203.10.96.139 |

### 为什么不需要交替错开使用

1. **glm5_2_nv 无 429 限流** (pexec 7 天 7017 次 0 个 429, integrate 0 个 429)
   - 不存在"额度用完需要换路径"的场景
   - dsv4p_nv 的 429 风暴是 NVCF 对 deepseek-v4-pro 的账户级限流, glm5_2_nv 不受影响
2. **integrate 路径本身更稳**: 不同出口 IP, 不同 NVCF 后端, 连接更稳定
3. **pexec 失败是连接级问题** (zombie/timeout), 不是限流 — 交替不能避免
4. **integrate 更快 3x**: avg 12.7s vs 39.9s (DB), 测试 6.1s vs 9.0s
5. **当前配置已是最优**: NV_INTEGRATE_MODELS=glm5_2_nv → integrate 首选, pexec fallback
   - integrate 429 (全 key) → path 冷却 → 自动 fallback pexec
   - 但实际 integrate 0 次 429, fallback 几乎不触发

### 最终建议

**维持 integrate 首选 + pexec fallback 的现有策略.** 不需要交替错开使用.
- integrate 路径在 SR、延迟、稳定性上全面优于 pexec
- pexec 作为 fallback 仅在 integrate 全 key 429 时触发 (从未发生)
- 交替使用反而会降低整体 SR (引入 pexec 的 28-32% 失败率)
