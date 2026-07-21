# R2188: HM2→HM1 — KEY_COOLDOWN_S 22→20 (-2s)

## 数据收集 (2026-07-21 20:20 UTC)

### 容器状态
- **nv_gw**: Up 18 minutes (healthy), StartedAt 2026-07-21T12:08:24Z (fresh restart)
- **logs_db**: Up, healthy
- **日志**: 0 error/warn lines (clean)

### 6h 统计
- **27 请求**, 20 OK (74.1% SR), 7 zombie, 0 ATE
- 全部流量: glm5_2_nv nvcf_pexec (无 dsv4p_nv, 无 kimi_nv)
- 7 zombie = zombie_empty_completion (NVCF func-level empty-200, FastBreak 已处理)
- OK 延迟: avg 14.7s, p50 11.9s, p95 34.7s, max 46.3s
- 无 fallback, 无 peer-fb, 0 ATE

### 24h 统计
- **144 请求**, 102 OK (70.8% SR), 26 zombie + 23 ATE + 1 IncompleteRead
- glm5_2_nv: 119/92 OK (77.3%), dsv4p_nv: 25/10 OK (40.0%)
- 23 ATE 全为 glm5_2_nv (NVCF 服务端低谷期, 非配置可修)

### Per-Key (6h)
| Key | Req | OK | Err | Avg ms | P50 ms |
|-----|-----|-----|-----|--------|--------|
| K0 | 5 | 3 | 2 | 13017 | 12165 |
| K1 | 7 | 6 | 1 | 12033 | 11863 |
| K2 | 7 | 6 | 1 | 19715 | 15491 |
| K3 | 4 | 3 | 1 | 13786 | 8939 |
| K4 | 4 | 2 | 2 | 13829 | 11168 |

### tier_attempts 错误 (6h)
- glm5_2_nv: pexec_success=27, pexec_SSLEOFError=11, pexec_429=3, pexec_conn_RemoteDisconnected=1, pexec_timeout=1

### key_cycle_429s (6h)
- cycle1=16, cycle2=8, cycle3=1, cycle4=2 (59% cycle1, 与 R2186 持平)

### 30min 窗口 (post-restart)
- 2 请求, 1 OK (50.0%), 1 zombie, avg 12.9s

## 优化
- **参数**: KEY_COOLDOWN_S: 22 → 20 (-2s)
- **模式**: KEY→TIER 交替 (R2185 KEY, R2186 TIER, R2188 KEY)
- **预算**: KEY+TIER+GLM5_2 = 20+8+28 = 56 << 153 (97s 安全余量)
- **理由**: 继续积压式收紧 KEY_COOLDOWN_S, 每轮 -2s. 当前 56s 远小于 153s BUDGET, 极端安全. 7 zombie 为 NVCF func-level empty-200, FASTBREAK=1 已正确检测, 非配置可修. 0 ATE 连续维持.
- **验证**: compose line 500 已改, restart 成功, live env KEY_COOLDOWN_S=20, health OK

## 评判
- 更少报错: 0 配置错误, 0 ATE, 容器日志 clean
- 更快请求: 减少 key 冷却等待 2s, 降低 key 轮转排队延迟
- 超低延迟: avg 14.7s 受 NVCF 响应时间主导, 非配置可调
- 稳定优先: 56s << 153s BUDGET 极端安全, 连续多轮 0 ATE

铁律: 只改HM1不改HM2

## ⏳ 轮到HM1优化HM2