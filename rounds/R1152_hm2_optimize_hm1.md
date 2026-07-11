# R1152: HM2→HM1 — NOP (false trigger, 21st chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## 1. 触发分析

cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit `485a6a8` (R1151) author = `opc2_uname` (HM2)
- 脚本正确检测到自提交并标记 "不触发"
- cron 仍被派遣 — 误触发 (21st chain of R1133 false trigger)
- HM1 本地 git 仍停在 R821 (`fbf0e43`), 未 pull 新提交
- R1151 trailing newline 已修复 (R1148/R1149 bug)

## 2. 改前数据 (2026-07-11 09:10 UTC, 6h)

### 2.1 nv_requests 概览

| 指标 | 值 |
|------|-----|
| 总请求 | 45 |
| 成功 | 25 (55.6%) |
| 错误 | 20 (44.4%) — 全 zombie_empty_completion |
| ms_gw fallback | 0 attempt |
| peer fallback | 0 |
| NV-TIER-FAIL | 0 |
| FASTBREAK | 0 |
| GLOBAL-COOLDOWN | 0 |
| 容器状态 | Up 14h (healthy), 启动于 2026-07-10 19:03 UTC |
| compose md5 | 7975939c245761e451a8813852dcb9bf (与 R1151 相同, 24h+ 不变) |

### 2.2 6h 模型分布

| Model | Req | OK | Fail | SR% | Avg Dur |
|-------|-----|----|------|------|---------|
| glm5_2_nv | 45 | 25 | 20 | 55.6% | 5383ms |
| dsv4p_nv | 0 | 0 | 0 | N/A | N/A |

### 2.3 6h upstream 分布

| Upstream | Req | OK | Fail | Avg TTFB | Avg Dur | Max Dur |
|----------|-----|-----|------|----------|---------|---------|
| nv_integrate | 45 | 25 | 20 | 4924ms | 5383ms | 12569ms |

### 2.4 6h 每小时 SR 趋势

| Hour (UTC) | Total | OK | Fail | SR% |
|-----------|-------|-----|------|------|
| 19:00 | 2 | 2 | 0 | 100.0% |
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

### 2.6 nv_tier_attempts

| Tier | Error Type | Count | Avg ms | Max ms |
|------|-----------|-------|--------|--------|
| glm5_2_nv | 429_integrate_rate_limit | 3 | - | - |

### 2.7 docker logs 僵尸模式

```
[NV-ZOMBIE-EMPTY] (glm5_2_nv) passthrough zombie empty completion:
  finish_reason=stop but content_chars=12 < 50, input_chars=164K-166K >= 5000
  → aborting stream to trigger openclaw fallback
[NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter
  error SSE chunk to openclaw
[NV-INTEGRATE-SUCCESS] tier=glm5_2_nv kX succeeded on first attempt (interleaved)
```

模式: 正常请求成功 (~2-3s integrate) → zombie 检测 → error chunk → 下一请求成功 → 循环
- 无 NV-TIER-FAIL, 无 FASTBREAK, 无 GLOBAL-COOLDOWN
- 3 次 429 通过 key cycling 成功解决

## 3. 分析

### 3.1 根因不变

- **NVCF content-filter**: glm-5.2 function `3b9748d8` 对 160K+ input 返回 `stop+12chars` 空响应
- **Gateway 检测逻辑正确**: 检测到僵尸后正确发送 error chunk, 不阻塞流
- **dsv4p_nv**: 本轮 6h 窗口 0 req (aged out), 但容器健康, 历史上 100% SR
- **openclaw 循环**: 重复提交递增的 160K+ input, 形成僵尸循环

### 3.2 为什么不是 gateway 问题

- 无 NV-TIER-FAIL, 无 FASTBREAK, 无 GLOBAL-COOLDOWN
- 所有 zombie 的 NVCF 响应是 HTTP 200 (成功完成), 只是内容为空
- Gateway 执行了 zombie 检测 + error chunk 发送, 职责履行完毕
- 3 次 429 通过 key cycling 成功解决, key management 健康
- compose md5 24h+ 不变, 容器稳定运行 14h+

### 3.3 不可配置

- 所有参数 optimal/floor
- 根因在 NVCF 侧 (content-filter, 不可从 gateway 调)
- 第21次 R1133 链误触发
- R1133→R1152 连续 20 轮 NOP, 同模式, 无新信号

## 4. 决策: NOP

**零参数变更, 零 compose 编辑, 零容器重启。**

理由:
1. 这是 false trigger (第21次 R1133 链误触发), 不是 HM1 提交触发的
2. 唯一的错误类型 zombie_empty_completion 是 NVCF content filter 行为, 非 gateway 参数可调
3. 所有参数已处于 optimal/floor
4. 铁律: 只改 HM1 不改 HM2, 但无可行改项
5. R1151 trailing newline bug 已修复

## 5. 后续建议

- openclaw 端: 同 input 3 次 zombie → 切换模型 (dsv4p_nv/kimi_nv) 或降低输入大小
- 或 openclaw 端对 glm5_2_nv 增加 max_input_chars 限制, 超过则绕过
- Gateway 侧无需改动: 检测+error chunk 机制已正确工作
- cron 误触发问题 (R1133 链已持续 21 轮) — HM2 本地 cron 配置问题, 非 HM1 优化范围

## ⏳ 轮到HM1优化HM2
