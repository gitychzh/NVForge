# R2281: HM2→HM1 — TIER_COOLDOWN_S 55→66 退出 429 反模式区

## TL;DR
R2279 (TIER_COOLDOWN_S 66→55) 部署后 6h 数据：glm5_2_nv 429 cycling 14/30=46.7%，进入反模式区（1-65s）。dSV4p_nv ATE 4 次（tiers_tried=1, 未触发 tier fallback）。zombie 5 次（NVCF 底层结构性衰减，无 config 可修）。介入一条：TIER_COOLDOWN_S 55→66 退回 R2126 安全边界。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R2281 部署前）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 24 | R10→24 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 275 | R2277 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | floor |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | floor |
| 5 | `TIER_COOLDOWN_S` | 55 | R2279 ← 本轮修改 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 122 | R2220→122 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | floor |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 | near floor |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R2268 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | disabled |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | floor |
| 12 | `NV_INTEGRATE_ENABLED` | (unset) | disabled |
| 13 | `NV_INTEGRATE_MODELS` | (empty) | disabled |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | floor |
| 15 | `KEY_COOLDOWN_S` | 66 | R2267 saezone boundary |

---

## 二、漂移检测（Pre-change）

### 2.1 容器状态
```
$ docker ps --filter name=nv_gw
STATUS=Up 2h (healthy)
```
无漂移。

### 2.2 关键 env vars 与上次记录一致
```
KEY_COOLDOWN_S=66     ← 一致
TIER_COOLDOWN_S=55    ← 一致（R2279 引入）
KEY_AUTHFAIL_COOLDOWN_S=0  ← 一致
TIER_TIMEOUT_BUDGET_S=275  ← 一致
NVU_EMPTY_200_FASTBREAK=2  ← 一致
UPSTREAM_TIMEOUT=24   ← 一致
```

### 2.3 代码版本
```
nv_gw: nv-gw:latest (no code changes since R2279)
```
无漂移。

---

## 三、诊断数据（6h 窗口，R2279 部署后）

### 3.1 总体统计
| 模型 | 总计 | OK | 失败 | 成功率 | 平均延迟 |
|------|------|-----|------|--------|----------|
| glm5_2_nv | 30 | 23 | 7 | 76.7% | 17264ms |
| dsv4p_nv | 16 | 12 | 4 | 75.0% | 31164ms |
| **总计** | **46** | **35** | **11** | **76.1%** | — |

### 3.2 失败明细
| 错误类型 | 次数 | 模型 |
|----------|------|------|
| zombie_empty_completion | 5 | glm5_2_nv |
| all_tiers_exhausted (502) | 4 | dsv4p_nv |
| all_tiers_exhausted (502) | 1 | glm5_2_nv |
| all_tiers_exhausted (429) | 1 | glm5_2_nv |

### 3.3 429 循环（关键指标）
```
glm5_2_nv: 14/30 = 46.7%  ← 进入反模式区！
```
KEY_COOLDOWN_S=66 + TIER_COOLDOWN_S=55 → 循环窗口 121s。55 < 66 安全边界 → 反模式（1-65s）。

### 3.4 dsv4p_nv ATE 分析
```
4 次 ATE-502，全部 tiers_tried_count=1
durations: 27s, 31s, 118s, 135s
```
tier fallback 未触发（tiers_tried=1），R2279 的 "+11s margin" 未解决 dsv4p_nv ATE 根因。

### 3.5 Peer-FB / MS-FB
```
Peer-FB events: 0（6h 内无触发）
MS-FB events: 0（6h 内无触发）
```
UPSTREAM_TIMEOUT=24 + PEER_FALLBACK_TIMEOUT=122 = 146 < 275 ✓ 公式满足但未触发。可能原因：ATE 发生在 tier 预算耗尽后，peer-fb 在 tier 层内触发，但 ATE 时 tier 已 exhaust。

### 3.6 近 30min 窗口
```
glm5_2_nv: 2/2 OK, avg 6337ms
```
近 30min 无失败。

### 3.7 当前日志
```
[07:03:22] NV-CYCLE tier=glm5_2_nv k4→429 cycling
[07:03:30] NV-SUCCESS k5 succeeded after 1 cycle
[07:03:34] NV-BIGINPUT-SUCCESS glm5_2_nv input=370828c
```
正常运行中。

---

## 四、根因分析

R2279 将 TIER_COOLDOWN_S 从 66→55 的原因是为 dsv4p_nv 提供 +11s 的 key-after-cooldown margin。但 55 落入 429 反模式区（1-65s → 过快的 tier 重试导致键在 NVCF 60s 窗口内重复命中 429）。结果：

- **glm5_2_nv 429 cycling: 46.7%** — 接近一半的请求经历 429 循环，浪费 upstream 配额和延迟
- **dsv4p_nv ATE 未改善** — 4/16=25% 失败率，tiers_tried=1 说明 tier 层 fallback 根本没触发
- **zombie 5 次** — NVCF 底层结构性衰减，非 config 可修

**结论：R2279 的 55 是个错误。66 是 R2126 验证的安全边界，应退回。**

---

## 五、本轮修改

### 变更：TIER_COOLDOWN_S 55 → 66

**文件**: `/opt/cc-infra/docker-compose.yml`  Line 511

**修改前**:
```yaml
- TIER_COOLDOWN_S=55  # R2279 (HM2->HM1): 66->55 +11s margin ...
```

**修改后**:
```yaml
- TIER_COOLDOWN_S=66  # R2281 (HM2->HM1): 55->66 escape 429 anti-pattern zone. 46.7% cycling (14/30) after R2279 reduction. Boundary: 66+66=132<275 OK. Revert to R2126 safe boundary. Single param; iron law: only HM1
```

**预算验证**:
```
KEY_COOLDOWN_S + TIER_COOLDOWN_S = 66 + 66 = 132 < 275 = TIER_TIMEOUT_BUDGET_S ✓
```
预算充足，安全。

### 部署
```
docker compose up -d nv_gw → Container nv_gw Recreated & Started
docker exec nv_gw env | grep TIER_COOLDOWN_S → TIER_COOLDOWN_S=66 ✓
docker logs nv_gw --tail 5 → 正常启动，无错误
```

---

## 六、修改后状态

| # | 参数 | 旧值 | 新值 | 来源 |
|---|------|------|------|------|
| 1 | `TIER_COOLDOWN_S` | 55 | **66** | R2281 |
| 2 | 其他所有参数 | — | **不变** | — |

---

## 七、后续观察建议

1. **429 cycling 率**：预期从 46.7% 降至 ~20-30%（66+66=132s 安全窗口）
2. **dsv4p_nv ATE**：tier cooldown 66 可能加剧 dsv4p_nv ATE（tier 重启更慢），但公式保证至少 1 个 key（160-66-90=4s → 边缘）。如果 dsv4p_nv ATE 恶化，下一轮考虑 TIER_BUDGET_DSV4P_NV 调整
3. **zombie**：非 config 可修，持续观察
4. **Peer-FB**：仍为 0 触发，如果失败率降至 0-5%，peer-fb 闲置可接受

---

## 八、介入决策记录

| 介入条 | 条件 | 满足？ | 决策 |
|--------|------|--------|------|
| 1 | zombie + 429 cycling > 40% | ✅ | 退回 TIER_COOLDOWN_S 66 |
| 2 | dsv4p_nv ATE 持续 | ✅ | 但根因非 cooldown，本次不修 |
| 3 | Peer-FB 未触发 | ✅ | 等待失败率降低后再评估 |
| 4 | 其他新错误 | ❌ | 无 |

**本轮介入**: 1 条（TIER_COOLDOWN_S 55→66）
**介入率**: 1/4 = 25%

---

*R2281 部署时间: 2026-07-23 07:18 CST (23:18 UTC)*
*HM2 模型: dsv4p_ms (hm4104 primary fallback 中)*
*铁律: 只改 HM1 不改 HM2*