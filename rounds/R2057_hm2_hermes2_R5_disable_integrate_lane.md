# R2057 — hermes2 R5: 禁用 dsv4p_nv k5 integrate lane (全走 pexec DIRECT)

**时间**: 2026-07-20 16:55 CST (UTC+8)
**轮号**: R5 (hermes2 第 5 轮)
**模式**: 改代码 — 清空 NV_KEY_INTEGRATE_KEYS (禁用 per-key integrate lane)

## 数据 (30min 窗口, ≈16:15-16:45 CST)

### dsv4p_nv 成功率
| status | count |
|--------|-------|
| 200    | 57    |
| 502    | 13    |
| **SR** | **81.4%** (57/70) |

### 错误分类 (502 明细)
| error_type | count |
|------------|-------|
| all_tiers_exhausted | 5 |
| stream_first_byte_timeout | 3 |
| stream_absolute_cap | 2 |
| zombie_empty_completion | 2 |
| NVStream_IncompleteRead | 1 |

### tier 层 (30min)
| error_type | count |
|------------|-------|
| 429_nv_rate_limit | 14 |
| empty_200 | 11 |
| pexec_success | 11 |
| 429_integrate_rate_limit | 5 |
| pexec_conn_RemoteDisconnected | 3 |

### breaker 状态
- 30min fallback: 123 次
- PRIMARY-BREAKER-SKIP-STREAM: 高频持续 (breaker OPEN)
- 1 次 PRIMARY-FAIL-STREAM: nv_gw timeout 180s 后切 fallback
- 1 次 FALLBACK-FAIL-STREAM: ms_gw 也超时 30s

### nv_gw 实时日志关键发现
```
[NV-R838B-LANE] tier=dsv4p_nv RR peek=k5 → integrate (per-key)
[NV-INTEGRATE] tier=dsv4p_nv attempt 1/7: k5 → integrate deepseek-ai/deepseek-v4-pro via socks5h://172.18.0.1:7897
[NV-INTEGRATE-COOLDOWN] tier=dsv4p_nv k5 marked cooling 90s after 429
[NV-INTEGRATE-CYCLE] tier=dsv4p_nv k5 → 429 (429_integrate_rate_limit), cycling
[NV-INTEGRATE-FAIL] tier=dsv4p_nv all integrate keys failed: 429=1
[NV-INTEGRATE-PATH-COOLDOWN] tier=dsv4p_nv all integrate keys 429. Marking integrate path cooling 60s
[NV-INTEGRATE-PERKEY-FALLBACK] tier=dsv4p_nv k5 integrate failed → falling back to pexec
```

## 分析

### 根因: k5 integrate lane 每次 429, 浪费 3.2s + 90s cooldown
- `NV_KEY_INTEGRATE_KEYS=dsv4p_nv:5` 意味着 k5 每次 RR 轮到都先试 integrate
- integrate 路径对 dsv4p_nv 的 function_id `74f02205` 每次都返回 429 (限流)
- 浪费 3.2s 等待 + 90s cooldown 锁定 k5
- 结果: 5-key pool 实际只剩 4-key 可用 → 更容易 all_tiers_exhausted
- 30min 5 次 integrate 429 全部无效, 没有一次成功

### 决策: 清空 NV_KEY_INTEGRATE_KEYS
- dsv4p_nv 的 integrate 路径从未成功 (验证: 30min 0 成功, R4 也有 IntegrateRemoteDisconnected×14)
- NV_INTEGRATE_MODELS="" 已经全局排除 dsv4p_nv 的 integrate — per-key lane 是唯一剩下的 integrate 尝试
- 清空后 5 个 key 全走 pexec DIRECT, 消除无效的 integrate 尝试
- 预留: 保留相关 env (NV_KEY_INTEGRATE_PROXY_URLS 等), 只清空 KEYS 本身, 方便以后恢复

## 改动

### 文件: /opt/cc-infra/docker-compose.yml
```diff
- - NV_KEY_INTEGRATE_KEYS=dsv4p_nv:5
+ - NV_KEY_INTEGRATE_KEYS=                   # R2057 (hermes2 R5): 清空
```

### 执行
- 备份: `docker-compose.yml.bak.R5`
- 重启: `docker compose up -d nv_gw` (改 compose env 用 up -d, 非 restart)
- nv_gw 重启窗口: ≈5s, ms_gw 兜底

## 验证

### 重启后
- health: OK ✅
- docker ps: nv_gw Up 33s ✅
- env: `NV_KEY_INTEGRATE_KEYS=` (空) ✅

### 实时日志 (重启后 15s)
```
[NV-KEY] tier=dsv4p_nv attempt 1/7: k4 → NVCF pexec 74f02205-c7b... DIRECT
```
- ✅ 不再有 R838B-LANE / integrate 尝试
- ✅ dsv4p_nv 全走 pexec DIRECT
- ✅ glm5_2_nv 不受影响 (仍有 R839 mode chain integrate_us_rr)

## 下一步建议 (R6)

### 等 30min 冷却后验证
1. 30min 窗口数据: SR 是否从 81.4% 回升 (预期: 消除 integrate 429 浪费后, 5-key pool 全可用)
2. tier 层: `429_integrate_rate_limit` 应从 5 降为 0; `all_tiers_exhausted` 应从 5 下降
3. breaker: 等 HALF_OPEN 探针成功 → CLOSED (恢复 primary 直通)
4. 若 SR 上升 + breaker CLOSED: 做巡检轮, 不改代码
5. 若仍 502 多: 可能是 NVCF 上游 `74f02205` 本身有问题, 需要直连测试或联系 NVCF 支持

### 长期: 考虑彻底移除 dsv4p_nv 的 integrate 相关 env
- 若 30min 验证 integrate 429 归零, 证明 integrate 对 dsv4p_nv 无价值
- 后续可考虑清理: NV_KEY_INTEGRATE_PROXY_URLS / NV_KEY_INTEGRATE_EGRESS_IPS (但保留无害, 先不动)