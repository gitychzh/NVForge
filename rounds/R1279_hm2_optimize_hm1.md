# HM2 Optimize HM1 — Round R1279

**状态**: NOP (false trigger, double-dispatch)

## 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author: `opc2_uname` (HM2)
- 触发类型: 双重派遣 (R1278 已由预运行脚本提交)
- HM1 git log 停留在 R821 (458 轮落后)

## 数据收集 (改前必有数据)

### 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 66 |
| 成功 | 51 |
| 失败 | 15 |
| SR | 77.3% |

### 错误分类
| 错误类型 | 数量 | 模型 |
|----------|------|------|
| zombie_empty_completion | 12 | glm5_2_nv (195K avg input, 9.1s avg dur) |
| all_tiers_exhausted | 3 | dsv4p_nv (72,020ms avg, all pre-R1275 restart) |

### 按路径
| 路径 | 请求 | 成功 | 失败 | 平均延迟 |
|------|------|------|------|----------|
| nv_integrate | 53 | 41 | 12 | 9,530ms |
| nvcf_pexec | 10 | 10 | 0 | 25,873ms |
| (ATE) | 3 | 0 | 3 | 72,019ms |

### 按模型
| 模型 | 请求 | 成功 | 失败 | SR | 平均延迟 |
|------|------|------|------|-----|----------|
| glm5_2_nv | 53 | 41 | 12 | 77.4% | 9,530ms |
| dsv4p_nv | 13 | 10 | 3 | 76.9% | 36,522ms |

### 每小时 SR
| 时次 (UTC) | 总数 | 成功 | 失败 | SR |
|------------|------|------|------|-----|
| 15:00 | 3 | 2 | 1 | 66.7% |
| 16:00 | 6 | 4 | 2 | 66.7% |
| 17:00 | 6 | 4 | 2 | 66.7% |
| 18:00 | 36 | 31 | 5 | 86.1% |
| 19:00 | 6 | 4 | 2 | 66.7% |
| 20:00 | 6 | 4 | 2 | 66.7% |
| 21:00 | 3 | 2 | 1 | 66.7% |

### 容器状态
- 容器重启: 2026-07-13T20:23:46Z (41 分钟前 — R1275 MODELMAP 部署)
- fallback_occurred: 0/66 (FALLBACK_GRAPH={} 设计, 预期)
- nv_tier_attempts: 0 行 (无 key 级错误)
- tier_chain: `['glm5_2_nv']` (no fallback, 3model) — 预期 (FALLBACK_GRAPH={})
- ms_gw: 4 req/0 OK — ms_requests 0 成功 (ms_gw 可能未被触发, 或处理中)
- compose md5: 28795fbe68f521457c09577f5da872ba (与 R1275 相同)

### 关键参数 (所有 floor/optimal)
| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | floor |
| TIER_TIMEOUT_BUDGET_S | 210 | optimal |
| NVU_TIER_BUDGET_DSV4P_NV | 72 | optimal |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | optimal |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 2 | optimal |
| TIER_COOLDOWN_S | 15 | floor |
| KEY_COOLDOWN_S | 25 | optimal |
| NVU_MS_GW_FALLBACK_TIMEOUT | 200 | optimal |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | optimal |
| NVU_MS_GW_FALLBACK_MODELMAP | glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms | R1275 新增 dsv4p |

## 决策: NOP

### 原因
1. **12 zombie = code-level**: glm5_2_nv integrate NVCF content_filter → stop + 12-36 chars → NV-ZOMBIE-EMPTY → 返回 502 error chunk。代码级检测功能, 非配置可修复。zombie 快速终止 (3-15s) 优于旧的 96s NVStream_TimeoutError。
2. **3 ATE = pre-R1275**: dsv4p_nv 3 个 ATE 全部发生在 R1275 MODELMAP 部署前的容器重启之前 (20:23 UTC)。dsv4p_nv:dsv4p_ms 刚加入 MODELMAP, 须等待 dsv4p_nv 流量验证。
3. **Post-restart 0 dsv4p_nv traffic**: 41 分钟内无 dsv4p_nv 请求。R1275 MODELMAP 修复待验证。
4. **所有参数 floor/optimal**: 无配置优化空间。UPSTREAM=66, FASTBREAK=1, BUDGET=210, TIER_BUDGET=72/96, 全部在已知最优值。
5. **dsv4p_nv pexec 100% SR**: 10/10 成功, 0 失败。仅 integrate 路径 zombie 影响 SR。
6. **ms_gw fallback 未触发**: 0 nv_gw fallback 尝试, 0 ms_gw 成功。dsv4p_nv 无 ATE 可触发 fallback。等待真实 dsv4p_nv ATE 验证 MODELMAP。

### 数据与 R1277/R1278 相同
- 66req/51OK/15fail, 12 zombie + 3 ATE (pre-restart)
- 无新流量模式, 无新错误类型
- 无参数变更理由

**铁律: 只改HM1不改HM2**

## ⏳ 轮到HM1优化HM2
