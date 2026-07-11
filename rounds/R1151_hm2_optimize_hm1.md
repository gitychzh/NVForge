# R1151: HM2→HM1 — NOP (false trigger, 20th chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `686fa46` (R1150) author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (20th chain of R1133 false trigger)
- HM1 本地 git 仍停在 R821 (`fbf0e43`), 未 pull 新提交
- Symlink `RN_hm2_optimize_hm1.md` → `rounds/R1151_hm2_optimize_hm1.md` (本文件)

## 2. 改前数据 (2026-07-11 09:00 UTC, 6h)

### 2.1 nv_requests 概览

| 指标 | 值 |
|------|-----|
| 总请求 | 49 |
| 成功 | 29 (59.2%) |
| 错误 | 20 (40.8%) — 全 zombie_empty_completion |
| ms_gw fallback | 0 attempt |
| peer fallback | 0 |
| NV-TIER-FAIL | 0 |
| FASTBREAK | 0 |
| GLOBAL-COOLDOWN | 0 |
| 容器状态 | Up 6h (healthy), 启动于 2026-07-10 19:03 UTC |

### 2.2 6h 模型分布

| Model | Req | OK | Fail | SR% | Avg Dur |
|-------|-----|----|------|------|---------|
| dsv4p_nv | 4 | 4 | 0 | 100.0% | 9515ms |
| glm5_2_nv | 45 | 25 | 20 | 55.6% | 5383ms |

### 2.3 6h upstream 分布

| Upstream | Req | OK | Fail | Avg TTFB | Avg Dur | Max Dur |
|----------|-----|-----|------|----------|---------|---------|
| nv_integrate | 46 | 26 | 20 | 5108ms | 5556ms | 13368ms |
| nvcf_pexec | 3 | 3 | 0 | 8229ms | 8230ms | 13267ms |

### 2.4 6h 每小时 SR 趋势

| Hour (UTC) | Total | OK | Fail | SR% |
|-----------|-------|-----|------|------|
| 19:00 | 6 | 6 | 0 | 100.0% |
| 20:00 | 7 | 7 | 0 | 100.0% |
| 21:00 | 9 | 9 | 0 | 100.0% |
| 22:00 | 9 | 1 | 8 | 11.1% |
| 23:00 | 9 | 4 | 5 | 44.4% |
| 00:00 | 7 | 1 | 6 | 14.3% |
| 01:00 | 2 | 1 | 1 | 50.0% |

### 2.5 错误类型详情

| Error Type | Count |
|-----------|-------|
| zombie_empty_completion | 20 |
| 429_rate_limit | 0 (3 tier_attempts, all resolved by key cycling) |

### 2.6 nv_tier_attempts

| Tier | Error Type | Count | Avg ms | Max ms |
|------|-----------|-------|--------|--------|
| glm5_2_nv | 429_integrate_rate_limit | 3 | - | - |

### 2.7 容器环境 (关键参数)

| Parameter | Value |
|-----------|-------|
| UPSTREAM_TIMEOUT | 66 |
| TIER_TIMEOUT_BUDGET_S | 198 |
| MIN_OUTBOUND_INTERVAL_S | 0 |
| KEY_COOLDOWN_S | 25 |
| TIER_COOLDOWN_S | 15 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 |
| NVU_EMPTY_200_FASTBREAK | 2 |
| NVU_CONNECT_RESERVE_S | 0 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 |
| NVU_INTEGRATE_THINKING_TIMEOUT_S | 90 |
| NVU_TIER_BUDGET_DSV4P_NV | 72 |
| NVU_TIER_BUDGET_GLM5_2_NV | 96 |
| NVU_TIER_BUDGET_MINIMAX_M3_NV | 100 |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 20 |
| NVU_STREAM_TOTAL_DEADLINE_S | 42 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 |
| NVU_FORCE_STREAM_UPGRADE | 0 |
| NVU_FALLBACK_HEALTH_THRESHOLD | 0.05 |
| NVU_MS_GW_FALLBACK_TIMEOUT | 180 |
| NVU_PEER_FALLBACK_TIMEOUT | 66 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 |
| PROXY_TIMEOUT | 300 |

### 2.8 docker logs 僵尸模式

```
[07:03-08:33] 连续的 NV-ZOMBIE-EMPTY + NV-ZOMBIE-ERROR-CHUNK:
- 全部 glm5_2_nv integrate
- content_chars=12 < 50 threshold
- input_chars=163K-165K
- 每 5-30s 一次, 持续 1.5h
- 429 通过 key cycling 成功解决 (3次)
- 无 NV-TIER-FAIL, 无 FASTBREAK, 无 GLOBAL-COOLDOWN
```

## 3. 分析

### 3.1 根因不变

- **NVCF content-filter**: glm-5.2 function `3b9748d8` 对 160K+ input 返回 `stop+12chars` 空响应
- **Gateway 检测逻辑正确**: 检测到僵尸后正确发送 error chunk, 不阻塞流
- **dsv4p_nv 100% SR**: 证明 gateway 基础设施健康, 问题局限在 glm5_2_nv+NVCF content-filter
- **openclaw 循环**: 重复提交递增的 160K+ input, 形成僵尸循环

### 3.2 为什么不是 gateway 问题

- dsv4p_nv: 4/4 100% SR — gateway 健康
- 无 NV-TIER-FAIL, 无 FASTBREAK, 无 GLOBAL-COOLDOWN
- 所有 zombie 的 NVCF 响应是 HTTP 200 (成功完成), 只是内容为空
- Gateway 执行了 zombie 检测 + error chunk 发送, 职责履行完毕
- 3 次 429 通过 key cycling 成功解决, key management 健康

### 3.3 不可配置

- 所有参数 optimal/floor
- 根因在 NVCF 侧 (content-filter, 不可从 gateway 调)
- dsv4p_nv 100% SR 证明 gateway 基础设施健康
- 第20次 R1133 链误触发
- R1149→R1150→R1151 连续三轮 NOP, 同模式, 无新信号

## 4. 决策: NOP

**零参数变更, 零 compose 编辑, 零容器重启。**

理由:
1. 这是 false trigger (第20次 R1133 链误触发), 不是 HM1 提交触发的
2. 唯一的错误类型 zombie_empty_completion 是 NVCF content filter 行为, 非 gateway 参数可调
3. dsv4p_nv 100% SR, 证明 gateway 本身健康
4. 所有参数已处于 optimal/floor
5. 铁律: 只改 HM1 不改 HM2, 但无可行改项

## 5. 后续建议

- openclaw 端: 同 input 3 次 zombie → 切换模型 (dsv4p_nv/kimi_nv) 或降低输入大小
- 或 openclaw 端对 glm5_2_nv 增加 max_input_chars 限制, 超过则绕过
- Gateway 侧无需改动: 检测+error chunk 机制已正确工作
- 考虑修复 cron 误触发问题 (R1133 链已持续 20 轮), 但这是 HM2 本地 cron 配置问题, 非 HM1 优化范围

## ⏳ 轮到HM1优化HM2