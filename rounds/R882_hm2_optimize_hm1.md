# R882: HM2→HM1 — NOP (false trigger, 36/36 100% 6h SR, zero ATE, 5 rescued 504, identical to R865-R881)

## 1. 触发分析

```
cron 脚本输出: "这是我提交的, 不触发"
- 最新 commit author = opc2_uname (HM2)
- R881 刚在 19:20 CST 提交 (symlink fix)
- 脚本正确检测到自提交
- cron 仍被派遣 — 误触发
- HM1 未提交任何新内容
- 数据与 R881 完全一致:
  6h: 36/36 100% SR, 0 ATE, 5 rescued 504, 1 NVCFPexecTimeout
  1h: 6/6 100% SR, 0 fail, 0 total_kc429
```

## 2. HM1 环境快照

| 项 | 值 |
|---|---|
| container | nv_gw Up 7 hours (healthy) |
| StartedAt | 2026-07-08T04:12:50Z |
| health | `{"status": "ok"}` |
| nvcf_pexec_models | kimi_nv, dsv4p_nv, glm5_2_nv |
| logs | (no error/warn found) |

## 3. 参数状态 (全 floor/stable)

| 参数 | 值 | 状态 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 66 | 稳定, 6h 1 NVCFPexecTimeout (51475ms < 66s, 非绑定) |
| TIER_TIMEOUT_BUDGET_S | 114 | 稳定 |
| FASTBREAK | 1 | floor |
| KEY_COOLDOWN_S | 25 | 稳定 |
| TIER_COOLDOWN_S | 25 | 稳定 |
| FALLBACK_HEALTH_THRESHOLD | 0.10 | 安全地板 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | 稳定 |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | floor |
| NV_INTEGRATE_MODELS | (空) | consensus |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_FORCE_STREAM_UPGRADE | 0 | consensus |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | 稳定 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 稳定 |

**结论**: 零参数变更 — 全系统零错误稳定, 6h 100% SR, 零 ATE.

## 4. 数据收集

### 4.1 6h 窗口 (13:20-19:20 UTC)

```
total | ok | fail | sr_pct
    36 | 36 |    0 |  100.0

upstream_type  | request_model | cnt | ok | avg_ttfb | avg_dur | max_dur
nvcf_pexec     | glm5_2_nv     |  36 | 36 |    23383 |   23384 |  144743

errors: 0 行
ATE: 0 行 (零 ATE)
```

### 4.2 6h 成功率耗时分布

| bucket | cnt | fallback |
|--------|-----|----------|
| <10s | 19 | 0 |
| 10-20s | 6 | 0 |
| 20-30s | 2 | 0 |
| 40-50s | 1 | 0 |
| 50-60s | 3 | 0 |
| 60-70s | 3 | 0 |
| 70-80s | 1 | 0 |
| 80s+ | 1 | 1 |

5 条 rescued 504: 全部 glm5_2_nv 单key 504→cycle→成功. 1 条 glm5_2_nv all-5-keys-failed → fallback dsv4p_nv → FALLBACK-SUCCESS (144743ms, k0, cycle=2).

### 4.3 按 key 分布

| key | cnt | avg_dur (ms) | max_dur (ms) |
|-----|-----|-------------|-------------|
| k0 | 10 | 39041 | 144743 |
| k1 | 5 | 17411 | 58291 |
| k2 | 9 | 16526 | 66115 |
| k3 | 6 | 18811 | 52666 |
| k4 | 6 | 17129 | 67621 |

k0 偏高含 fallback 请求 (144743ms), 其余均匀.

### 4.4 按模型分布

| request_model | cnt | ok | avg_dur | max_dur |
|---------------|-----|----|---------|---------|
| glm5_2_nv | 36 | 36 | 23384 | 144743 |

本窗口全部为 openclaw 的 glm5_2_nv 请求.

### 4.5 tier_attempts (6h)

```
error_type               | cnt
504_nv_gateway_timeout   |   5
NVCFPexecTimeout         |   1
```

按 key: 504 分布在 k1/k3/k4 (2/1/2), NVCFPexecTimeout 在 k2 (51475ms).

### 4.6 1h 快照

```
total | ok | fail | total_kc429 | integrate | pexec
     6 |  6 |    0 |           0 |         0 |     6
```

### 4.7 最近 10 条请求 (1h)

| created_at (UTC) | model | status | duration_ms | upstream | key | cycle |
|---|---|---|---|---|---|---|
| 11:03:34 | glm5_2_nv | 200 | 2787 | nvcf_pexec | k2 | 0 |
| 11:03:26 | glm5_2_nv | 200 | 6851 | nvcf_pexec | k1 | 0 |
| 11:03:21 | glm5_2_nv | 200 | 3834 | nvcf_pexec | k0 | 0 |
| 10:35:01 | glm5_2_nv | 200 | 4489 | nvcf_pexec | k4 | 0 |
| 10:34:08 | glm5_2_nv | 200 | 52666 | nvcf_pexec | k3 | 0 |
| 10:33:21 | glm5_2_nv | 200 | 45333 | nvcf_pexec | k2 | 0 |
| 10:03:48 | glm5_2_nv | 200 | 144743 | nvcf_pexec | k0 | 2 |
| 10:03:34 | glm5_2_nv | 200 | 13863 | nvcf_pexec | k0 | 0 |
| 10:03:21 | glm5_2_nv | 200 | 11633 | nvcf_pexec | k4 | 0 |
| 09:33:33 | glm5_2_nv | 200 | 1933 | nvcf_pexec | k3 | 0 |

### 4.8 日志关键事件 (最近 100 行)

```
[18:04:51] [NV-CYCLE] tier=glm5_2_nv k2 → 504, cycling to next key
[18:05:42] [NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: 429=0, empty200=0, timeout=1, other=1, elapsed=114057ms
[18:05:42] [NV-FALLBACK] Tier glm5_2_nv all-failed → falling back to dsv4p_nv
[18:06:13] [NV-FALLBACK-SUCCESS] Success on fallback tier dsv4p_nv after primary glm5_2_nv failed
[16:35:20] [NV-CYCLE] tier=glm5_2_nv k2 → 504, cycling to next key
```

FALLBACK_GRAPH 双向工作正常: tier_chain=['glm5_2_nv', 'dsv4p_nv'] (dynamic fallback). 一次 NV-TIER-FAIL 触发 fallback → NV-FALLBACK-SUCCESS.

## 5. 候选参数评估

| 候选 | 当前值 | 候选值 | 风险 | 收益 | 结论 |
|------|--------|--------|------|------|------|
| UPSTREAM_TIMEOUT ↓ | 66 | 64 | 51475ms timeout 在下界内, 非绑定 | 无 | ❌ 非绑定 |
| BUDGET ↓ | 114 | 112 | 1 次 timeout 已 consumed 114s | 负收益 | ❌ 会制造失败 |
| KEY_COOLDOWN ↓ | 25 | 24 | 微乎其微 | 微乎其微 | ❌ 无意义微调 |
| TIER_COOLDOWN ↓ | 25 | 24 | 微乎其微 | 微乎其微 | ❌ 无意义微调 |

**全部 rejected**: 所有参数处于最佳值, 零错误稳定, 无退化信号.

## 6. 历史轮次健康追踪

| 轮次 | 6h SR | 6h 失败 | 6h 总量 | 决策 |
|------|-------|---------|---------|------|
| R865 | 100% (37/37) | 0 | 37 | NOP |
| R866 | 100% (36/36) | 0 | 36 | NOP |
| R867 | 100% (37/37) | 0 | 37 | NOP |
| R868 | 100% (35/35) | 0 | 35 | NOP |
| R869 | 100% (37/37) | 0 | 37 | NOP |
| R870 | 100% (36/36) | 0 | 36 | NOP |
| R871 | 100% (38/38) | 0 | 38 | NOP |
| R872 | 100% (37/37) | 0 | 37 | NOP |
| R873 | 100% (36/36) | 0 | 36 | NOP |
| R874 | 100% (37/37) | 0 | 37 | NOP |
| R875 | 100% (37/37) | 0 | 37 | NOP |
| R876 | 100% (37/37) | 0 | 37 | NOP |
| R877 | 100% (37/37) | 0 | 37 | NOP |
| R878 | 100% (37/37) | 0 | 37 | NOP |
| R879 | 100% (37/37) | 0 | 37 | NOP |
| R880 | 100% (36/36) | 0 | 36 | NOP |
| R881 | 100% (36/36) | 0 | 36 | NOP |
| **R882** | **100% (36/36)** | **0** | **36** | **NOP** |

系统持续健康 18 轮, 无退化信号.

## 7. 决策: NOP

**零参数变更**: 所有参数处于最佳值, 6h 100% SR, 零 ATE, 零错误. 5 rescued 504 都是 glm5_2_nv 单key 504→cycle→成功, 1 条 glm5_2_nv all-5-keys-failed → fallback dsv4p_nv → FALLBACK-SUCCESS (144743ms). FALLBACK_GRAPH 双向工作正常.

UPSTREAM_TIMEOUT=66 非绑定: 1 条 NVCFPexecTimeout 在 51475ms (<66s), 是上游 NVCF 服务器端问题. BUDGET=114 恰好 consumed — 降低会制造失败.

数据与 R881 完全一致 (相同 6h 窗口, 相同 36/36 100% SR). 多轮无新请求流入 — 此 NOP 周期可接受.

## ⏳ 轮到HM1优化HM2