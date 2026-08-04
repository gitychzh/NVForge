# R-dsv4f-0731-rebuild: dsv4f0731_nv40666 容器重建 — 529 cycling + 最优 5 US IP + 动态链路故障切换

**日期**: 2026-08-04
**主机**: HM2 (100.109.57.26)
**容器**: dsvf0731_nv40666 (port 40666)
**模型**: dsv4f_nv (deepseek-ai/deepseek-v4-flash)

## 摘要

dsv4f0731_nv40666 容器重建, 修复 v4-flash 两大问题:
1. HTTP 529 (NVCF Overloaded) 不 cycling → 加入 should_cycle 列表, 529 时自动换 key+IP 重试
2. 代理端口从低 SR 的 7901-7904 换为测试最优的 7897/7904/7894/7896/7895

修复后 6/6 E2E 请求成功 (100% SR), 对比修复前 28% SR。

## 改前数据

### v4-flash 5 key × 9 proxy 全量测试

| Proxy | Egress IP | SR | Key1 | Key2 | Key3 | Key4 | Key5 |
|---|---|---|---|---|---|---|---|
| 7897 | .197 | 60% | ✓ | ✓ | ✗ | ✗ | ✓ |
| 7904 | .197 | 60% | ✓ | ✓ | ✗ | ✗ | ✓ |
| 7894 | .193 | 40% | ✗ | ✗ | ✓ | ✗ | ✓ |
| 7896 | .195 | 40% | ✓ | ✗ | ✗ | ✗ | ✓ |
| 7895 | .180 | 20% | ✗ | ✗ | ✗ | ✗ | ✓ |
| 7901 | 203.10.96 | 20% | ✗ | ✓ | ✗ | ✗ | ✗ |
| 7902 | .194 | 20% | ✗ | ✗ | ✓ | ✗ | ✗ |
| 7899 | .120 | 0% | ✗ | ✗ | ✗ | ✗ | ✗ |
| 7903 | .120 | 0% | ✗ | ✗ | ✗ | ✗ | ✗ |

总体: 13/45 = 28% SR。失败全部是 529 (NVCF Overloaded)。

### 根因: 529 不 cycling

`_try_integrate_keys()` 的 `should_cycle` 列表为 `(401, 403, 429, 408, 500, 502, 503, 504, 202)`,
**不包含 529**。v4-flash 的 529 发生率 64-72%, 一个 529 就 abort 整个 tier。
而 529 是间歇性的 — 换一个 key+IP 组合可能成功。

## 变更

### 1. upstream.py — 529 加入 should_cycle

**文件**: `/opt/cc-infra/proxy/nv-gw/gateway/upstream.py` (bind-mounted, 共享)

3 处 `should_cycle` 列表加入 529:
- `_try_integrate_keys()` (line 312): integrate 路径 — 主要修复
- `_try_dsv4p_channel_keys()` (line 1148): dsv4p channel 路径
- `_glm52_single_attempt()` (line 1594): glm52 mode chain 路径

2 处 `cycle_reason` 三元组链加入 `"529_integrate_overloaded"` / `"529_nv_overloaded"` 分支。

529 不标 per-key cooling (不像 429 那样), 只 cycle 到下一 key+IP。
5 key × 5 IP = 25 组合, 28% SR × 25 ≈ 99.6% 至少一个成功。

### 2. docker-compose.yml — 更新 dsv4f0731_nv40666 代理配置

| 字段 | 旧值 | 新值 |
|---|---|---|
| NV_INTEGRATE_PROXY_URLS | 7902,7901,7902,7903,7904 | 7897,7904,7894,7896,7895 |
| NV_INTEGRATE_EGRESS_IPS | 139,188,180,194,120 | 197,197,193,195,180 |
| NVU_PROXY_URL1-5 | 7902,7901,7902,7903,7904 | 7897,7904,7894,7896,7895 |
| NVU_EGRESS_IP1-5 | 194,188,180,139,120 | 197,197,193,195,180 |

新代理按测试 SR 从高到低排列: 7897(60%), 7904(60%), 7894(40%), 7896(40%), 7895(20%)。

### 3. 动态链路故障切换机制

修复后 `_try_integrate_keys()` 自身的 RR 轮转即动态链路故障切换:
- 5 key × 5 IP 按 RR 轮转, 每 attempt 用不同 key+IP 组合
- 529 → cycling (不 abort), 换下一 key+IP 重试
- 429 → per-key cooling 30s + cycling
- 401/403 → per-key auth-fail (cross-tier skip) + cycling
- 全 5 key 耗尽 → all_keys_exhausted → 上层可 fallback

## 验证

### E2E 测试 (6 请求)

| # | Result | Time | Notes |
|---|---|---|---|
| 1 | 200 OK | 9.2s | k1-k4 529 cycle, k5 success (4 cycles) |
| 2 | 200 OK | 1.9s | k2 first attempt |
| 3 | 200 OK | 7.0s | k3 529, k4 success (1 cycle) |
| 4 | 200 OK | 3.5s | k4 first attempt |
| 5 | 200 OK | 6.6s | k5 first attempt |
| 6 | 200 OK | 4.5s | k1 first attempt |

**6/6 = 100% SR** (对比修复前 28% SR)。

### 日志验证

```
[19:47:11.8] [NV-INTEGRATE] tier=dsv4f_nv attempt 2/7: k2 → integrate via 7904
[19:47:12.8] [NV-INTEGRATE-CYCLE] tier=dsv4f_nv k2 → 529 (529_integrate_overloaded), cycling
[19:47:12.8] [NV-INTEGRATE] tier=dsv4f_nv attempt 3/7: k3 → integrate via 7894
[19:47:13.9] [NV-INTEGRATE-CYCLE] tier=dsv4f_nv k3 → 529 (529_integrate_overloaded), cycling
[19:47:13.9] [NV-INTEGRATE] tier=dsv4f_nv attempt 4/7: k4 → integrate via 7896
[19:47:16.2] [NV-INTEGRATE-CYCLE] tier=dsv4f_nv k4 → 529 (529_integrate_overloaded), cycling
[19:47:16.2] [NV-INTEGRATE] tier=dsv4f_nv attempt 5/7: k5 → integrate via 7895
[19:47:19.6] [NV-INTEGRATE-SUCCESS] tier=dsv4f_nv k5 succeeded after 4 cycle attempts
```

529 cycling 行为符合预期: k1→529→k2→529→k3→529→k4→529→k5→SUCCESS。

## 参数表

| 参数 | 值 | 说明 |
|---|---|---|
| LISTEN_PORT | 40666 | 独立端口 |
| NV_INTEGRATE_MODELS | dsv4f_nv | 强制走 integrate |
| NV_INTEGRATE_PROXY_URLS | 7897,7904,7894,7896,7895 | 5 US IP (按 SR 排序) |
| UPSTREAM_TIMEOUT | 90 | integrate 超时 |
| TIER_TIMEOUT_BUDGET_S | 180 | 单 tier 总预算 |
| KEY_COOLDOWN_S | 30 | 429 冷却 |
| NVU_EMPTY_200_FASTBREAK | 3 | 连续 3 次 empty_200 才 break |
| NVU_DISABLE_MS_FALLBACK | 1 | 无 ms_gw 兜底 (独立容器) |

## Commit

upstream.py + docker-compose.yml.bak + round file。
