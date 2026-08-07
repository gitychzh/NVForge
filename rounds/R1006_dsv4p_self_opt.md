# R1006: dsv4f0731_nv40666 NOP 轮 — 状态健康，无参数修改

**日期**: 2026-08-07 13:40 (Asia/Shanghai)
**容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 Pro via NVCF)
**决策**: **NOP** — SR>95%, 无 fallback, 0 429, 错误分布均匀，不需要改参数

## 数据依据

### 30min 窗口 (13:10-13:40)
- **Total**: 123 | **Success**: 121 | **Failed**: 2 → **SR = 98.37%**
- **Avg**: 17,638ms | **P50**: 9,593ms | **P95**: 44,025ms | **P99**: 161,739ms
- **429 计数**: 0
- **Finish reason**: tool_calls=99, stop=22 (81.8% tool calls — 编程/工具负载)
- **upstream_type**: 全部 pexec (123/123)，无 integrate 流量

### 错误分类 (30min)
- `all_tiers_exhausted` × 1 (179,103ms)
- `stream_absolute_cap` × 1 (168,353ms)

### Per-key 延迟 (30min, 来自脚本)
| Key | Req | Avg | P95 |
|-----|-----|-----|-----|
| k0 | 23 | 12,070ms | 31,445ms |
| k1 | 25 | 13,413ms | 40,146ms |
| k2 | 21 | 10,576ms | 19,832ms |
| k3 | 26 | 12,660ms | 34,571ms |
| k4 | 26 | **25,300ms** | **136,110ms** |

k4 avg=25.3s 是其他 key 的 ~2x, P95=136s 显著偏高。但 k4 **无错误** (成功但慢)。

### Per-key 错误 (1h, nv_tier_attempts)
```
k0: pexec_success=45, RemoteDisconnected=4, Timeout=2
k1: pexec_success=42, RemoteDisconnected=6
k2: pexec_success=42, RemoteDisconnected=9, empty_200=1
k3: pexec_success=49, RemoteDisconnected=9, empty_200=2
k4: pexec_success=42, RemoteDisconnected=7
```
- 主要错误 `NVCFPexecRemoteDisconnected` (35/1h) 在各 key **均匀分布** (4/6/9/9/7) → NVCF 端普遍瞬时断连，非单 key 问题
- 30min 内 2 个失败事件 (all_tiers_exhausted, stream_absolute_cap) 均在 k0

### 趋势
- **6h**: 1657 total, 1613 success → SR=97.34%, 44 fallback (2.66%)
- **3h 逐小时**: 每时 SR≥97.5%, fallback=0
- **24h all_tiers_exhausted**: 371 (~1.5%) — 但 30min 仅 1 次，分布不均匀
- **tier_attempts**: 30min 空 — 所有请求首轮 key 循环即成功，无 tier-level 重试

### Fallback
- hm4104 最近 5min **无 fallback**
- 30min nv_requests: 126 total, 0 fallback

## 诊断结论
1. **SR 优秀 (98.37%)** — 无需调超时/冷却
2. **0 429** — 429 管理正常
3. **全部 pexec** (NV_KEY_INTEGRATE_KEYS=空) — 无 integrate 流量，无需调 integrate 参数
4. **NVCFPexecRemoteDisconnected 均匀分布** — 是 NVCF 端瞬时断连，不是单 key 代理问题，非本机可控
5. **k4 延迟偏高但无错误** — 值得下一轮观察，但不足以触发参数修改（可能为 NVCF 端/负载因素）

## 参数状态 (未修改，保持当前)
```
KEY_COOLDOWN_S=30
TIER_COOLDOWN_S=90
TIER_TIMEOUT_BUDGET_S=180
UPSTREAM_TIMEOUT=90
MIN_OUTBOUND_INTERVAL_S=5
NVU_KEYMGR_429_BASE_COOLDOWN=120
NVU_KEYMGR_429_MAX_COOLDOWN=120
NVU_KEYMGR_CONN_BASE_COOLDOWN=30
NVU_KEYMGR_CONN_MAX_COOLDOWN=60
NVU_KEYMGR_CONN_FAIL_THRESHOLD=3
NVU_KEYMGR_CONN_LONG_COOLDOWN=120
NVU_PEXEC_TIMEOUT_FASTBREAK=3
NVU_EMPTY_200_FASTBREAK=3
NVU_TIER_BUDGET_DSV4F0731_NV=180
NV_KEY_INTEGRATE_KEYS=(空)
```

## 验证
- /health: status=ok, nv_num_keys=5, nvcf_pexec_models 5 个
- 容器 Up 20 hours

## 下一步建议
1. 持续观察 k4 延迟 — 若 k4 avg 持续 >2x 且 P95>130s 保持多窗口，考虑将 k4 移出 pexec 轮转或调整其代理 mihomo 7895
2. 观察 NVCFPexecRemoteDisconnected 是否持续升高 — 若单 key 集中于某 key，则指向该 key 代理问题