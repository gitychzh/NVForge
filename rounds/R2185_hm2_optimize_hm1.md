# R2185: HM2→HM1 — KEY_COOLDOWN_S 24→22 (-2s)

## 数据收集 (2026-07-21 19:33 UTC)

### 6h 统计
- **27 请求**, 21 OK (77.8% SR), 6 zombie, 0 ATE
- 全部流量: glm5_2_nv (无 dsv4p_nv, 无 kimi_nv)
- 6 zombie = NVCF func-level empty-200 (不可配置修复)
- 429 cycling: 17 req with 1 cycle, 8 with 2, 2 with 4 (63% cycle1)
- OK 延迟: avg 16.2s, min 5.8s, max 46.3s
- 无 fallback, 无 peer-fb

### tier_attempts 错误
- glm5_2_nv: pexec_success=27, pexec_SSLEOFError=10, pexec_429=2, pexec_conn_RemoteDisconnected=1, pexec_timeout=1

### 日志
- 全部 glm5_2_nv 请求经 pexec_us_rr mode chain
- UPSTREAM_TIMEOUT=24s, 每请求 ~1-2 key attempts
- 无 error/warn 日志, 正常运行

## 优化
- **参数**: KEY_COOLDOWN_S: 24 → 22 (-2s)
- **模式**: KEY→TIER 交替 (R2173 KEY, R2174 TIER, R2175 KEY, R2176 TIER, R2177 KEY, R2180 TIER, R2181 KEY, R2184 TIER, R2185 KEY)
- **预算**: KEY+TIER+GLM5_2 = 22+10+28 = 60 << 153 (93s 安全余量)
- **理由**: 减少 key 429 冷却时间, 降低 63% key_cycle_429s=1 率, 5 key pool 有充足冗余
- **验证**: compose line 500 已改, restart 成功, live env KEY_COOLDOWN_S=22

## 评判
- 更少报错: 0 配置错误
- 更快请求: 减少 key 冷却等待 2s
- 超低延迟: avg 16.2s 受 NVCF 响应时间主导, 非配置可调
- 稳定优先: 60s << 153s BUDGET 极端安全

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2