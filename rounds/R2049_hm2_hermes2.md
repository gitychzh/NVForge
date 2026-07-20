# R2049 (HM2 hermes2 R2): fallback 冷却期死锁修复

> 日期: 2026-07-20, HM2 hermes2 自优化链路 dsv4p_nv

## 数据依据 (改前必有数据)

- **30min dsv4p_nv**: SR 84.8% (39/46), 失败 7: zombie×4 + NVStream_IncompleteRead×2 + stream_first_byte_timeout×1
- **hm4104 断路器状态**: R1 重启后 breaker 持续 OPEN, 0 次 PRIMARY-FAIL (从未尝试 primary)
- **根因分析**: 非 R1 调参问题, 是 fallback 冷却机制自锁
  - R0 遗留: nv_gw 对大 input 返回 content_filter zombie → hm4104 fallback
  - `_mark_fallback()` 每次 fallback 成功重置 120s 计时器
  - hermes2 持续发请求 → fallback 持续重置计时器 → `_in_fallback_recover()` 永远 True
  - `should_try_primary_full()` → 永远 False → 0 次 primary 尝试
  - 死循环: 不走 primary = 永远不会 record_primary_success = breaker 永不 CLOSED

## 改动

- **文件**: `/opt/cc-infra/proxy/cc-adapter/gateway/forwarder.py`
- **函数**: `_mark_fallback()` (line 126)
- **改动**: 冷却期内不重置计时器
  - 改前: `_last_fallback_at = time.monotonic()` (每次都重置, 自锁)
  - 改后: 仅在 `_last_fallback_at == 0.0` 或已过冷却期时才设置
  - 效果: 冷却期 120s 自然到期 → `_in_fallback_recover()` 变 False → breaker 探活
- **不改 nv_gw** (zombie 本身是 nv_gw 的质量问题, 见 R0 诊断, 本轮聚焦 breaker 自锁)

## 验证

- `docker compose restart hm4104` 成功
- env 确认: PRIMARY_HEADER_TIMEOUT=120, CIRCUIT_FAILURE_THRESHOLD=8, FALLBACK_RECOVER_S=120
- 重启后首次请求成功走 primary (无 SKIP 日志), script_execution 流正在跑
- 遇到 nv_gw zombie 才 fallback, 非 breaker 自锁断
- 冷却期内 fallback 不重置计时器 (日志: 14:26 zombie fallback → 14:27 SKIP 表示冷却期内)
- 预计 120s 后 breaker 自动恢复探活

## 下一步 (R3)

- 等冷却后确认 breaker 自然恢复 (不再 SKIP)
- 若 primary 恢复但 zombie 仍高 → nv_gw R0 诊断的 dsv4p_nv zombie 问题需治理
- 大 input 导致 zombie → 可能需调 nv_gw 的 inject 参数或增长 TIER_TIMEOUT
- 或考虑 dsv4p_nv 的 R840 zombie 拦截本身是否可改: 当前 nv_gw 对 zombie 发 content_filter → hm4104 切 fallback。若 zombie 不严重(30min 4/46=8.7%)可接受