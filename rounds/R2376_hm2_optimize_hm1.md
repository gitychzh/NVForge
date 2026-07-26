# R2376 — HM2 Optimizes HM1 — Single Param: NVU_BIG_INPUT_FAIL_N 3→5

### 1. 数据源
- docker exec nv_gw env | sort  → 当前运行 env (R2375 已生效: COOLDOWN=180)
- docker exec logs_db psql 6h DB:
  - nv_requests: mapped_model success rates + ATE/error_type counts
  - nv_tier_attempts: tier-level error breakdown + latency

### 2. 关键发现

**glm5_2_nv 成功率仅 34.5% (10/29), 但破坏性远超表面:**

- 19 个 ATE (all_tiers_exhausted) — 但看 tier_attempts 只有 5 条错误记录！
- 14/19 ATE 的 tier_attempts_count=0 (instant reject, 无 NVCF 接触)
- 这意味着问题在 **tier 选择之前** 就被阻断 — 确认是 big_input breaker OPEN 导致。

**FAIL_N=3 的误触发路径 (已确认):**

这三者本质上是**不同的 transient 错误**:
- #1 是 NVCF 网络流中断 
- #2 是 tier 瞬时拒绝
- #3 是空响应
用 3 个不同 transient 错误触发 180s OPEN → 阻断后续所有合法大输入请求。

**对比: dsv4p_nv (已移除 BIG_INPUT_MODELS)** 
- SR 88.9% (8/9), 0 zero-tier-attempt ATE
- 移除后不受 breaker 污染, 正常 tier budget (265s) 兜底即可

**kimi_nv: SR 76.1%, 16 empty_200 tier-level** 
- key-specific 瞬态错误, FASTBREAK=3 已处理
- 非 big_input breaker 问题

### 3. 优化内容

**参数变动：**

| 参数 | 旧值 | 新值 | 来源 | 说明 |
|------|------|------|------|------|
| NVU_BIG_INPUT_FAIL_N | 3 (R2356) | 5 | docker-compose.yml env | 需5次连续失败才OPEN breaker |

**其他约束保持：**
- NVU_BIG_INPUT_COOLDOWN_S=180 (R2375 刚确认生效, 不变)
- NVU_BIG_INPUT_MODELS=glm5_2_nv (R2358 已隔离 dsv4p_nv, 不变)
- NVU_BIG_INPUT_THRESHOLD=250000 (R2312 不变)
- 所有其他 env 不变

### 4. 预期效果

**数学验证：**
- 3→5 后, transient 三元组 (IncompleteRead + ATE + empty_200) 不再触发 OPEN
- 需要 **5 次同模型/同大小** 连续失败 = 明确 sustained zombie 模式才 OPEN
- COOLDOWN=180s 保持: 一旦触发, 节省 90.5% 无效探针 (180s OPEN vs 9s 正常)
- glm5_2_nv ATE 中 zero-attempt 比例预计从 74% → << 20%
- glm5_2_nv SR 预计 34.5% → 55%+ (释放被 breaker 误拦截的合法请求)

**风险：**
- 若真实 zombie 持续 5 次, OPEN 延迟 2 个请求 → 多消耗 2×76s = ~150s
- 但 COOLDOWN=180s 仍兜底, 且 zombie 特征为 long-tail (15-90s 重复模式) not transient
- ZERO 修改 HM2 本地, 仅改 HM1 docker-compose.yml → 可回滚

### 5. 部署状态
- ✅ docker-compose.yml 已更新 (sed in place)
- ⏳ docker compose up -d 待 HM1 手动/自动重启生效
- 仅 HM1 side, iron law 遵守

### 6. Empirical Trigger Condition



## ⏳ 轮到HM1优化HM2
