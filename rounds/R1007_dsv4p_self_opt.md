# R1007: 降低 dsv4p_nv40066 TIER_COOLDOWN_S 180→90 (消除全 key 冷却级联)

**日期**: 2026-08-03
**容器**: dsv4p_nv40066 (port 40066, DeepSeek V4 Pro via NVCF)
**主机**: HM2 (opc2sname)
**改动类型**: 环境参数调优 (单参数)

## 修改

| 参数 | 旧值 | 新值 | 生效方式 |
|------|------|------|---------|
| `TIER_COOLDOWN_S` | 180 | 90 | docker compose up -d --force-recreate |

## 依据

### 采集窗口 (post-R1006 重启 ~53min, 16:01:05–16:54:25 UTC)
- 总请求: 188, 成功: 152, SR=80.9% (请求级)
- 错误分布: `all_tiers_exhausted` ×27, `stream_absolute_cap` ×1
- 200 avg duration: 7429ms, max 108168ms

### all_tiers_exhausted 双峰分布 (关键发现)

| 时长区间 | 数量 | avg ms | 特征 |
|----------|------|--------|------|
| 2-9ms | 19 | ~2800 | **瞬时失败** — 全 key cooling, 0 pexec 尝试 |
| 60-180s | 8 | 117000 | 真实 tier 耗尽 (NVCF 处理但全 key 失败) |

- 19/27 (70%) 的 ATE 是瞬时失败: 全 5 key 在 TIER_COOLDOWN 期间被冻结, 请求进来秒 fail 无 pexec 尝试
- 容器日志铁证 `NV-GLOBAL-COOLDOWN`: 16:52:50 全 5 key 429 → 标记全部 cooling 180s → 16:52:57 再次全 429 → 再次标记 180s
- 级联期间 (16:53:00–16:54:25) 12 个请求 2-9ms 秒 fail, tier_attempts 表 0 行 (KeyManager 层 ABORT, 未进 upstream)

### stream_absolute_cap (1 次, 边际)
- 502, 167933ms, 0 tokens, key_idx=0
- 日志: `absolute wall-clock cap 150s exceeded (elapsed=167s, content_chars=0, reasoning_chars=0, gap_limit=80.0s)`
- NVCF 接受请求但 167s 无任何内容输出 → abs_cap 截断, 单发非系统性, 暂不调参

### per-key 429 分布 (tier_attempts, post-restart)
| key_idx | 429 count | 其他错误 |
|---------|-----------|----------|
| k0 | 2 | NVCFPexecRemoteDisconnected ×2 |
| k1 | 4 | NVCFPexecRemoteDisconnected ×2 |
| k2 | 4 | - |
| k3 | 0 | empty_200 ×2 |
| k4 | 2 | NVCFPexecRemoteDisconnected ×2 |

- 429 均匀分布 (非单 key 问题), 但 16:52:50 全 5 key 同时 429 → TIER_COOLDOWN 触发

### 根因分析
1. NVCF 账户级配额波动: 某些时刻全 5 key 同时 429 (无 retry-after)
2. `TIER_COOLDOWN_S=180` 在全 key 429 时冻结全部 key 180s
3. 180s 冷却窗口内, 所有新请求秒 fail (2-9ms ATE), 无实际 pexec 尝试
4. 70% 的 ATE 错误是冷却级联的副产品, 非 NVCF 真实不可用

### R1006 上次修改效果验证
- R1006 清空 `NV_KEY_INTEGRATE_KEYS`: integrate 路径错误已归零 (0 IntegrateRemoteDisconnected, 0 429_integrate_rate_limit in post-restart window)
- pexec 成为唯一路径, 5-key pool 完整恢复 (k3 不再被 integrate lane 占用)
- SR 从 R1006 采集时 86.8% → 本轮 80.9%, 但降幅主因是 16:34/16:53 两次全局冷却级联 (非 integrate 问题复发)

## 预期效果
1. 全 key 429 后冷却窗口从 180s 减半到 90s, 级联期间的瞬时 ATE 减少 ~50%
2. 90s 仍 > 单 key 429 base cooldown (120s base, 但 429 衰减窗口 300s 内 count 会 decay), 不会导致过度重试加剧 NVCF 429
3. SR 从 80.9% → 预期 >88% (消除 70% 瞬时 ATE 的大部分)
4. 真实 tier 耗尽 (8 次 60-180s) 不受影响 — 这些是 NVCF 真实失败, 非 cooldown 问题

## 验证
- `/health`: `{"status":"ok","nv_num_keys":5,"port":40066}` ✅
- `TIER_COOLDOWN_S=90` 确认生效 (docker exec env)
- 容器 recreate 成功, 无 crash

## 下一步
- 下轮验证: 确认瞬时 ATE (2-9ms) 数量下降, SR 恢复 >88%
- 关注: 全 key 429 事件频率是否不变 (NVCF 账户级问题, 非 gateway 可控)
- 若瞬时 ATE 仍 >10/30min: 考虑进一步降到 60s, 或加 per-key staggered cooldown (避免全 key 同步冻结)
- `stream_absolute_cap` 如连续 3+ 轮单发: 评估 NVU_STREAM_ABSOLUTE_CAP_S 150→180 或调查 NVCF 慢响应根因
- hm4104 primary 下轮回 primary
