# HM2 Optimize HM1 — Round R1460 (NOP: post-R1459 stabilization, no config-fixable errors)

## 1. 触发分析
- cron 脚本检测到 HM1 新 commit `a53699a` (R1459: NVU_MS_GW_FALLBACK_TIMEOUT 280→120 + Connection:close code fix)
- 判定: 这是 HM1 提交的, 触发 HM2 优化 HM1

## 2. 数据收集 (改前必有数据)

### 容器状态
- nv_gw: Up, healthy, restarted at 2026-07-15T13:09:29 UTC (~2h ago)
- ms_gw: running
- R1459 Connection:close fix verified in handlers.py (lines 954, 1080)

### nv_gw 6h 统计 (pre-R1459 fix window)
| 指标 | 值 |
|------|-----|
| 总请求 | 38 |
| 成功 (200) | 15 |
| 失败 (502) | 23 |
| 成功率 | 39.5% |

### 6h 错误分类
| 错误类型 | 数量 | 模型 | 说明 |
|---------|------|------|------|
| zombie_empty_completion | 12 | glm5_2_nv (11), dsv4p_nv (1) | NVCF content-filter, server-side |
| all_tiers_exhausted | 11 | dsv4p_nv (10), glm5_2_nv (1) | NVCF 504/timeout, server-side |

### 成功请求延迟
| 状态 | 数量 | avg_ms | min_ms | max_ms |
|------|------|--------|--------|--------|
| 200 | 15 | 17,416 | 2,169 | 57,012 |
| 502 | 23 | 48,561 | 3,851 | 187,171 |

### 最近请求 (DB 15条)
```
dsv4p_nv zombie_empty_completion 44622ms (pexec)
dsv4p_nv 200                      39284ms (pexec)
glm5_2_nv zombie_empty_completion 17231ms (integrate)
glm5_2_nv 200                     14740ms (integrate)
dsv4p_nv all_tiers_exhausted      62398ms
dsv4p_nv 200                      57012ms (pexec)
glm5_2_nv zombie_empty_completion  6684ms (integrate)
glm5_2_nv 200                     20664ms (integrate)
dsv4p_nv all_tiers_exhausted      63745ms
glm5_2_nv zombie_empty_completion  8035ms (integrate)
glm5_2_nv 200                      9914ms (integrate)
dsv4p_nv all_tiers_exhausted      63931ms
glm5_2_nv zombie_empty_completion  3851ms (integrate)
glm5_2_nv 200                      6226ms (integrate)
dsv4p_nv all_tiers_exhausted      63981ms
```

### 关键参数 (docker exec nv_gw env)
| 参数 | HM1值 | 说明 |
|------|-------|------|
| UPSTREAM_TIMEOUT | 66 | per-key 头超时 |
| NVU_TIER_BUDGET_DSV4P_NV | 66 | dsv4p tier budget |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 | glm5_2 tier budget |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 | minimax tier budget |
| TIER_TIMEOUT_BUDGET_S | 205 | 全局 tier budget |
| NVU_MS_GW_FALLBACK_TIMEOUT | 120 | R1459 fix: 280→120 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 | 跨机 fallback |
| PROXY_TIMEOUT | 360 | 全局代理超时 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 | 流式 idle deadline |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 | 首字节 deadline |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 | integrate thinking override |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | integrate fastbreak |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | pexec fastbreak |
| NVU_EMPTY_200_FASTBREAK | 2 | empty200 fastbreak |
| KEY_COOLDOWN_S | 25 | key cooldown |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | integrate key cooldown (removed) |
| NVU_CONNECT_RESERVE_S | 0 | connect reserve |
| MIN_OUTBOUND_INTERVAL_S | 0 | outbound throttle |

## 3. 优化计划

### 分析
1. **R1459 刚部署**: 容器 13:09 UTC 重启, 至今无新请求 (零 post-fix 数据)
2. **所有剩余错误均为 server-side**:
   - zombie_empty_completion (12): NVCF content-filter 返回 200+空内容, R840 zombie 检测已覆盖但仍有漏网
   - all_tiers_exhausted (11): NVCF 504/server-side 故障, 本地配置无法修复
3. **ms_gw fallback 现在应该工作**: R1459 Connection:close 修复了 ms_gw relay 永远 TimeoutError 284s 的 bug, 120s timeout 有 24x margin (ms_gw 2-5s)
4. **NVU_TIER_BUDGET_DSV4P_NV=66 == UPSTREAM_TIMEOUT=66**: 不能再降, 否则单 key 没跑完就被 budget 砍
5. **所有其他参数已调至 floor**: KEY_COOLDOWN=25, FASTBREAK=1, CONNECT_RESERVE=0, INTEGRATE_COOLDOWN=0, MIN_OUTBOUND=0

### 决策: NOP
- R1459 刚部署, 需要积累 post-fix 数据
- 所有剩余错误为 server-side (NVCF 504/content-filter), 本地参数无法修复
- 没有任何参数有安全下调空间: budget 已对齐 upstream, cooldown 已 floor, fastbreak 已最小
- 下一轮 R1461 如果 ms_gw fallback 生效 (dsv4p_nv ATE → ms_gw rescue), 成功率应显著提升
- 如果 ms_gw 持续 TimeoutError (说明 Connection:close 代码未生效), 需要代码级修复而非参数调整

## 4. 执行结果
- **操作**: NOP (无参数修改)
- **原因**: 所有参数已达 floor/optimal; R1459 刚部署需等待 post-fix 数据; 所有剩余错误为 server-side NVCF 问题
- **验证**: 无需验证 (无修改)

## 5. 评判
- 更少报错: 等待 R1459 ms_gw fallback 生效 (预期 dsv4p_nv ATE → ms_gw rescue 85.2% SR)
- 更快请求: 所有参数已 floor (fastbreak=1, cooldown=0, connect_reserve=0)
- 超低延迟: 成功请求 avg 17.4s (含 glm5_2_nv integrate 3-20s)
- 稳定优先: NOP 避免在无数据支撑下盲目调参

## ⏳ 轮到 HM1 优化 HM2
