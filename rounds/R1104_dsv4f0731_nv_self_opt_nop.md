# R1104: 系统健康 — NOP (无参数修改)

> 时间: 2026-08-07 20:12 UTC (BJT 04:12)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **NOP (不改参数)** — 30min SR=98.8%, 429=0, ATE=0, fallback=0

## 1. 背景 (改前必有数据)

R1103 (19:22-19:52 UTC) 也是 NOP。本轮观测窗口(19:42-20:12 UTC) 仍处于系统低负载时段 (BJT 凌晨 3-4 点)。

### DB 30min 窗口 (mapped_model=dsv4f0731_nv)

| 指标 | 值 |
|------|-----|
| 总请求 | 168 |
| 成功(200) | 166 |
| **SR** | **98.8%** |
| 429 | **0** |
| 错误 | 2 (zombie_empty_completion) |
| Avg/P50/P95/max | 10568ms / 7907ms / 31189ms / 55670ms |

### 错误分布 (30min)

| error_type | count | avg_ms |
|------------|-------|--------|
| zombie_empty_completion | 2 | 4,459 |

两个错误均为低时长空 200, 位于 key 2 (5428ms) 和 key 4 (3490ms)。非超时、非连接断开。

### Per-key 200 延迟 (30min)

| key | n | avg_ms | max_ms |
|-----|---|--------|--------|
| 0 | 35 | 9,597 | 17,763 |
| 1 | 30 | 8,520 | 15,025 |
| 2 | 37 | 13,738 | 44,589 |
| 3 | 28 | 7,925 | 16,023 |
| 4 | 36 | 12,355 | 37,444 |

- **Key 2 继续是延迟最高** (avg 13.7s, max 44.6s) — 跨多轮观测均如此。可能对应一个共享 SOCKS5 代理上的竞争型 key。
- Key 4 max=37.4s 也偏高。
- 但所有 key 均在 UPSTREAM_TIMEOUT=90s 内, 无因超时导致的请求失败。

### Per-key error (30min)

| key | error_type | count | avg_ms |
|-----|------------|-------|--------|
| 2 | zombie_empty_completion | 1 | 5,428 |
| 4 | zombie_empty_completion | 1 | 3,490 |

无 key 集中劣化 — 各 key 各贡献 1 个僵尸空响应。

### Upstream type (30min)

| upstream | total | ok | SR |
|----------|-------|----|----|
| nvcf_pexec | 168 | 166 | **98.8%** |

100% pexec, 无 integrate 流量 (`NV_KEY_INTEGRATE_KEYS` 为空)。

### Finish reason

| reason | count |
|--------|-------|
| tool_calls | 140 (83%) |
| stop | 26 (15%) |

无空响应。tool_calls 占比正常 (DS V4 Pro 作为 hermes 主力模型)。

### 6h 趋势

| 窗口 | total | success | error | SR |
|------|-------|---------|-------|----|
| 6h | 1807 | 1769 | 38 | **97.9%** |
| 12:00 UTC | 62 | 61 | 1 | 98.4% |
| 11:00 UTC | 323 | 318 | 5 | 98.5% |
| 10:00 UTC | 322 | 318 | 4 | 98.8% |
| 09:00 UTC | 273 | 268 | 5 | 98.2% |

逐小时 SR 均 ≥98.2%, 无恶化趋势。12:00 UTC 时段 (当前窗口尾部) 请求量下降 (62 → 凌晨低负载), SR 维持 98.4%。

### 6h tier_attempts 错误 (tier=dsv4f0731_nv)

| error_type | count |
|------------|-------|
| NVCFPexecRemoteDisconnected | ~94 (与 R1103 持平) |
| NVCFPexecTimeout | ~15 |
| empty_200 | ~14 |

**无 529_nv_overloaded!** — 账户级过载风暴已完全收敛。主要错误 RemoteDisconnected 是 NVCF 端偶发断开, 当前配置已能有效重试。

### 24h ATE

| 指标 | 24h |
|------|-----|
| all_tiers_exhausted | 255 |

255 ATE/24h, 较 R1103 的 267 略降。avg=197s 说明风暴期预算才烧完 — 正常时段无 ATE。

### Fallback

hm4104 fallback 日志 (5min 窗口): **无 fallback** ✅

所有 hermes 请求在本机 dsv4f0731_nv 直接完成, 无需 ms_gw 降级。

### 当前参数

| 参数 | 当前值 |
|------|--------|
| UPSTREAM_TIMEOUT | 90 |
| TIER_TIMEOUT_BUDGET_S | 180 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 |
| KEY_COOLDOWN_S | 30 |
| TIER_COOLDOWN_S | 90 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 |
| NVU_KEYMGR_429_MAX_COOLDOWN | 120 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 |
| NVU_EMPTY_200_FASTBREAK | 3 |
| NVU_BUFFER_TIMEOUT_STAIRS | 90,90,90,90,90 |

## 2. 决策: NOP (不改参数)

**理由:**

1. **30min SR=98.8%** — 远高于主动干预阈值 (95%)。连续多轮 NOP 确认系统在高稳定区间。
2. **429=0, ATE=0** — 无速率限制、无预算耗尽。`key_cycle_429s` 分布 (0:64次, 1:104次) 说明存在 key 级 429 轻量轮转, 但重试成功, 未造成请求级失败。
3. **529 风暴已完全收敛** — 连续多轮零 529_nv_overloaded。对比 R1016 的 377/2h 已全面恢复。
4. **Key 2 延迟偏高但非病态** — max=44.6s 在 UPSTREAM_TIMEOUT=90s 内, 且对应的空响应仅 1 次。若进一步加剧 (如 avg >20s 或错误率 >10%) 再考虑冷却调整。
5. **Fallback=0** — NVCF 链路完全自足。
6. **一次只改一个参数** — 无参数存在明确劣化信号。

**Conclusion**: NOP — 系统健康, 无优化空间需要立即介入。

## 3. 当前状态 (30min 主指标)

- 30min SR: **98.8%** (166/168)
- Avg/P50/P95/max: 10.6s / 7.9s / 31.2s / 55.7s
- 错误: zombie_empty_completion=2 (avg 4.5s)
- 429: 0 (key_cycle_429s: 0→64, 1→104)
- upstream: 100% nvcf_pexec
- finish_reason: tool_calls=140, stop=26
- Fallback: **0** ✅

## 4. 上次修改效果 (R1103 NOP)

- R1103→R1104: SR 维持 98.8%, 429=0 维持。
- 24h ATE 从 267 略降至 255。
- upstream_type 保持 100% nvcf_pexec, 无 integrate 流量进入。
- Per-key 延迟分布与 R1103 基本一致 (key2 仍高于均值, 但无恶化趋势)。

## 5. 验证

- [x] /health: status OK, 5 keys, tiers 含 dsv4f0731_nv
- [x] 容器 Up 27h (未重启)
- [x] hm4104 fallback = 0
- [x] 写入仓库 (本 round 文件 + commit)

## 6. 下一步建议

1. **继续 NOP 状态** — 只要 SR>95%, 429=0, fallback=0, 持续 NOP。每日一次快照把控趋势。
2. **Key 2 长期观察** — key 2 跨多轮延迟偏高 (avg 13-14s vs 其他 key 8-10s)。建议在连续 5+ 轮观测到 key2 avg >20s 或错误率 >10% 时介入: 增加 KEY_COOLDOWN_S 至 60 或单独对其提高冷却。
3. **Integrate 通路候选��估** — 当前 100% pexec 工作良好, integrate 通路 (NV_KEY_INTEGRATE_KEYS) 不建议激活除非 pexec 出现系统性劣化。
4. **北京时间白天窗口** — 建议下次有意选择 BJT 白天 (UTC 4-10) 时段观测, 验证高负载下的一致性。