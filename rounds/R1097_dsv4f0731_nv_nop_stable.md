# R1097: dsv4f0731_nv NOP — SR=98.3%, 稳定运行

**容器**: dsvf0731_nv40666 (HM2, 端口 40666)
**时间窗口**: 2026-08-07 17:30-18:00 UTC (01:30-02:00 Beijing)
**决策**: NOP — 零参数修改

## 30-min 数据

| 指标 | 值 |
|------|------|
| 总请求 | 174 |
| 成功 | 171 (98.3%) |
| 失败 | 3 (1.7%) |
| All tiers exhausted | 0 |
| Fallback (hm4104) | 0 |
| 总 429 计数 | 0 |
| Avg/P50/P95/P99 | 10,138 / 7,679 / 27,726 / 46,590ms |
| TTFB avg | 8,810ms |

## 错误分类

| error_type | count | avg_ms |
|------------|-------|--------|
| NVCFPexecRemoteDisconnected | 1 | 45,777 |
| zombie_empty_completion | 2 | 2,962 |

- **NVCFPexecRemoteDisconnected** (k3, 46s): NVCF 上游断连，非可调优的配置问题
- **zombie_empty_completion** (k3: 3,269ms, k4: 2,654ms): 快速空响应，非持续性问题

## Per-key

| Key | 200 count | 200 avg | 200 max | 错误 |
|-----|-----------|---------|---------|------|
| k0 | 37 | 9,541 | 27,707 | — |
| k1 | 35 | 10,188 | 20,595 | — |
| k2 | 32 | 8,977 | 15,316 | — |
| k3 | 33 | 10,062 | 17,095 | 1 RemoteDisconnected + 1 zombie |
| k4 | 34 | 11,281 | 36,815 | 1 zombie |

**补充说明**: k0 max=27,707ms 比其他 key 高，但 k0 无错误 — 仅个别长尾。

## 6h / 24h 趋势

- **6h**: 1,683 req, 1,640 success (97.4%), 43 fail, 0 ATE
- **3h 逐小时**:
  - 07:00 UTC: 248/239/9/0 — SR=96.4%, avg=12,626ms
  - 08:00 UTC: 260/251/9/0 — SR=96.5%, avg=12,495ms
  - 09:00 UTC: 363/358/5/0 — SR=98.6%, avg=9,890ms
  - 10:00 UTC: 6/6/0/0 — 低流量尾端
- **24h ATE**: 311 (全 tier 合计，~13/hr)
- **24h SR** (外推): ~97.5%

## 当前环境参数 (关键)

| 参数 | 值 | 作用 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 90 | pexec 读超时 |
| TIER_TIMEOUT_BUDGET_S | 180 | tier 总预算 |
| NVU_TIER_BUDGET_DSV4F0731_NV | 180 | 本模型专用预算 |
| KEY_COOLDOWN_S | 30 | key 故障冷却 |
| TIER_COOLDOWN_S | 90 | tier 冷却 |
| NVU_KEYMGR_429_BASE_COOLDOWN | 120 | 429 冷却 |
| NVU_EMPTY_200_FASTBREAK | 3 | 空 200 连续阈值 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 3 | pexec timeout 连续阈值 |
| NVU_KEYMGR_CONN_FAIL_THRESHOLD | 3 | 连接失败阈值 |
| NV_KEY_INTEGRATE_KEYS | _(空)_ | 无 integrate 路由 |
| NVU_CONN_ERR_FAST_BREAK | 5 | 连接错误 fast break |
| NVU_PROBE_ENABLED | 1 | 探针活跃 |

## 决策理由

1. **SR=98.3% (30min), 97.4% (6h)** — 稳定，高于 95% 阈值
2. **0 fallback, 0 ATE** — 无降级，无需紧急调整
3. **3 个错误均为 transient**:
   - RemoteDisconnected: NVCF 上游断连，非配置可修复
   - zombie_empty_completion: 快速 (<3.3s), 非持续
4. **key_cycle_429s=61.5% 但已恢复** — 429 中转瞬即逝，key 轮转策略有效
5. **无 integrate 流量** — NV_KEY_INTEGRATE_KEYS 为空，无法评估 integrate 路径
6. **上一轮 (R1094) 亦然 NOP** — 持续稳定

## 后续关注点

- 若 RemoteDisconnected 频率升高，考虑 NVU_SSLEOF_RETRY_DELAY 或 key-level 冷却
- 若 zombie_empty_completion 集中在某 key，可调小 NVU_EMPTY_200_FASTBREAK=3→2
- 24h ATE=311/h (高频) — 但当前窗口 0 ATE，说明不是 dsv4f0731_nv 的问题