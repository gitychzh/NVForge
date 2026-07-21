# R2186: HM2→HM1 — TIER_COOLDOWN_S 10→8 (-2s)

## 数据收集 (2026-07-21 20:00 UTC)

### 6h 统计
- **27 请求**, 20 OK (74.1% SR), 7 zombie, 0 ATE
- 全部流量: glm5_2_nv (无 dsv4p_nv, 无 kimi_nv)
- 7 zombie = NVCF func-level empty-200 (不可配置修复)
- 429 cycling: 16 cycle1, 8 cycle2, 1 cycle3, 2 cycle4 (59% cycle1, 略优于R2185的63%)
- OK 延迟: avg 16.5s, p50 12.3s, p95 36.7s, min 5.8s, max 46.3s
- 无 fallback, 无 peer-fb, 无 ATE

### tier_attempts 错误
- glm5_2_nv: pexec_success=27, pexec_SSLEOFError=11, pexec_429=3, pexec_conn_RemoteDisconnected=1, pexec_timeout=1

### 日志
- 仅 [NV-GLM52-ERR] SSLEOFError + [NV-UPSTREAM-ERROR-CHUNK] zombie (正常, NVCF func-level)
- 无 error/warn 异常, 容器正常运行

## 优化
- **参数**: TIER_COOLDOWN_S: 10 → 8 (-2s)
- **模式**: KEY→TIER 交替 (R2173 KEY, R2174 TIER, R2175 KEY, R2176 TIER, R2177 KEY, R2180 TIER, R2181 KEY, R2184 TIER, R2185 KEY, R2186 TIER)
- **预算**: KEY+TIER+GLM5_2 = 22+8+28 = 58 << 153 (95s 安全余量)
- **理由**: 继续积压式收紧 TIER_COOLDOWN_S, 每轮 -2s, 当前 58s 远小于 153s BUDGET, 极端安全
- **验证**: compose line 506 已改, restart 成功, live env TIER_COOLDOWN_S=8, health OK

## 评判
- 更少报错: 0 配置错误, 0 ATE
- 更快请求: 减少 tier 冷却等待 2s, 降低 tier 因冷却被跳过概率
- 超低延迟: avg 16.5s 受 NVCF 响应时间主导, 非配置可调
- 稳定优先: 58s << 153s BUDGET 极端安全, 12轮连续 0 ATE

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2