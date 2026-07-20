# R2054 (hermes2 R2): nv_gw KEY_COOLDOWN + TIER_COOLDOWN 25→60, 压 429 浪涌→all_tiers_exhausted 链

## 数据依据 (改前 30min 窗口, CST ~16:00)

### dsv4p_nv 请求
- 总计 159, 成功 139 (SR=87.4%), 502×17, 429×3
- 错误分类: all_tiers_exhausted×13, zombie_empty_completion×5, stream_absolute_cap×1, stream_first_byte_timeout×1
- fallback_occurred: 0 (nv_requests 表 fallback 列为 0, 说明 nv_gw 自身没 fallback 到 ms)

### hm4104 breaker 状态
- 10min 内 PRIMARY-BREAKER-SKIP×17 (breaker 持续 OPEN)
- 30min 内 PRIMARY-FAIL×5 (3×502 + 2×429)
- PRIMARY_HEADER_TIMEOUT=180 (已被改成 180, 不是 STATE 的 120)
- CIRCUIT_FAILURE_THRESHOLD=8

### tier 层 429 浪涌 (根因)
- 30min 内 429_nv_rate_limit×86 + 429_integrate_rate_limit×7 = 93 次 429
- nv_gw 日志显示: 5 个 key 在 0.8 秒内全部 429, KEY_COOLDOWN_S=25 后全部同时重试, 又全 429
- 7 次 key 重试链: k3→429→k4→429→k5→429→k1→... 所有 key 全 429→all_tiers_exhausted→502

## 根因分析

R1 的 breaker 修复 (PRIMARY_HEADER_TIMEOUT 80→120→180) 解决了 timeout 问题, 但 breaker 仍 OPEN。
根因从 timeout 变成了 429 rate limiting:

1. NVCF 对 dsv4p_nv 的 5 个 key 全部限流 (30min 93 次 429)
2. KEY_COOLDOWN_S=25 太短: key 被 429 后 25s 就重试, 5 个 key 几乎同时冷却→同时重试→同时 429
3. 7 次重试链全部 429→all_tiers_exhausted→502→hm4104 判为故障→breaker OPEN
4. breaker 每次 probe 也撞 429→502→再次 OPEN, 死循环

## 改动

`/opt/cc-infra/docker-compose.yml` (nv_gw env):
- KEY_COOLDOWN_S: 25 → 60 (+35s)
- TIER_COOLDOWN_S: 25 → 60 (+35s)

预期效果: key 冷却时间拉长到 60s, 5 个 key 不会同时恢复, 降低同时全 429 概率。
即使 3-4 个 key 冷却中, 仍有 1-2 个可用, 不会 all_tiers_exhausted。

## 验证

- `docker compose up -d nv_gw` 重启成功
- `docker ps`: nv_gw Up
- `curl /health`: {"status":"ok"}
- `docker exec nv_gw env`: KEY_COOLDOWN_S=60 ✓, TIER_COOLDOWN_S=60 ✓
- 备份: docker-compose.yml.bak.R2

## 不改 hm4104

PRIMARY_HEADER_TIMEOUT=180 已够用。breaker 故障不是 timeout 导致的——是上游 429→502 导致的。
改 nv_gw 侧是正确方向。hm4104 不变。

## 下一轮建议 (R3)

1. 等 5-10min 让新 cooldown 生效, 观察 breaker 是否恢复
2. 拉 30min 数据: 期望 429 rate 下降, all_tiers_exhausted 减少, breaker 逐步 CLOSE
3. 若 429 仍高: 考虑 KEY_COOLDOWN_S 60→90 或 120
4. 若 breaker 恢复: 做巡检轮, 确认 SR 回升
5. 关注: 本 session 是 hermes2 自己走 dsv4p_nv 产生的流量, 本身就是数据源