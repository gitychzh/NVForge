# R709: HM2→HM1 — NVU_PEXEC_TIMEOUT_FASTBREAK 2→1 (-1 key). ATE省60s/次

## TL;DR
R709: NVU_PEXEC_TIMEOUT_FASTBREAK 2→1 (-1 key per function). 6h数据: 128req/84OK(65.6%)/44ATE(34.4%). dsv4p_nv SR=55.4%(51/92), 全部41 failures为ATE upstream_type=NULL. 所有ATE均为双tier耗尽(dsv4p_nv+glm5_2_nv各~61s=~122s), 0 tier_attempts记录. R708 FALLBACK_HEALTH_THRESHOLD复活后fallback已生效(tiers_tried_count=2), 但NVCF双function均上游不可用. FASTBREAK=2在双tier模式下浪费第2key ~60s于已失败的NVCF function; 降为1省60s/ATE并释放BUDGET余量给peer fallback. R559-R694历史验证FASTBREAK=1稳定136轮. 单参数每轮; 铁律:只改HM1不改HM2.

---

## 一、当前配置快照（R709 部署后）

| # | 参数 | HM1 当前值 | 历史来源 | 本轮变更 |
|---|------|------------|----------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 30 | R701 | — |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 110 | R706 | — |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638 | — |
| 4 | **`NVU_PEXEC_TIMEOUT_FASTBREAK`** | **1** | **R709** | **🔄 2→1 (-1)** |
| 5 | `TIER_COOLDOWN_S` | 25 | R492 | — |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | R697 | — |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R657 | — |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R543 | — |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 40 | R694 | — |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R692 | — |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | R577 | — |
| 12 | `NV_INTEGRATE_MODELS` | "" (空) | R693 | — |
| 13 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631 | — |
| 14 | `KEY_COOLDOWN_S` | 25 | R162 | — |
| 15 | `FALLBACK_HEALTH_THRESHOLD` | 0.10 | R708 | — |

---

## 二、四源漂移检测（Pre-check）

### 2.1 源1 — Compose 文件
```
NVU_PEXEC_TIMEOUT_FASTBREAK: "2"  # R695 (line 591)
```
→ 与R708快照一致。R709将修改此行。

### 2.2 源2 — 容器 env
```
NVU_PEXEC_TIMEOUT_FASTBREAK=2
```
→ 全部匹配compose。

### 2.3 源3 — 容器状态
```
nv_gw    Up 13 minutes (healthy)   # R708 deploy
logs_db  Up 15 hours (healthy)
```
→ 稳定运行，无crash loop。

### 2.4 源4 — 日志
```
(no error/warn found) — 仅BrokenPipe(客户端断开, 无害)
```
→ 四源一致，无漂移。✅

---

## 三、Pre-optimization 数据（6h 窗口，R708 部署 13min 前）

### 3.1 Regime 快速健康度（13min）
| 指标 | 值 |
|------|-----|
| 总量 | 8 req |
| OK | 3 (37.5%) |
| Fail | 5 ATE (62.5%) |
| avg_dur_ok | 23.5s |

> 注：仅13min样本，极低流量窗口，数据不可用于决策。以下用6h窗口。

### 3.2 6h 全景
| 指标 | 值 |
|------|-----|
| 总量 | 128 req |
| OK | 84 (65.6%) |
| Fail | 44 (34.4%) |
| 含429 cycle | 27 req (21.1%) |
| 总429 cycles | 42 |
| avg_dur_ok | 29.9s |

### 3.3 6h 按模型
| Model | Total | OK | Fail | SR% | avg_dur_ok | max_dur | p95_dur |
|-------|-------|-----|------|-----|------------|---------|---------|
| dsv4p_nv | 92 | 51 | 41 | 55.4% | 40.1s | 122.3s | 121.5s |
| glm5_2_nv | 35 | 33 | 2 | 94.3% | 14.1s | 90.3s | 80.5s |
| kimi_nv | 1 | 0 | 1 | 0.0% | — | 2.7s | 2.7s |

### 3.4 6h 错误分布
| error_type | mapped_model | cnt |
|------------|-------------|-----|
| all_tiers_exhausted | dsv4p_nv | 41 |
| all_tiers_exhausted | glm5_2_nv | 2 |
| all_tiers_exhausted | kimi_nv | 1 |

→ 全部44 failures均为ATE。无其他错误类型。

### 3.5 ATE upstream_type 分析
| upstream_type | ate_cnt | avg_ate_dur |
|--------------|---------|-------------|
| NULL | 44 | 80.6s |

→ 所有44个ATE均为upstream_type=NULL（调度层直接拒绝）。0 tier_attempts记录。

### 3.6 ATE fallback 详情（最近10条）
| mapped_model | duration_ms | fallback_tiers_used | tiers_tried |
|-------------|-------------|---------------------|-------------|
| dsv4p_nv | 121838 | {dsv4p_nv,glm5_2_nv} | 2 |
| dsv4p_nv | 122312 | {dsv4p_nv,glm5_2_nv} | 2 |
| dsv4p_nv | 122066 | {dsv4p_nv,glm5_2_nv} | 2 |
| dsv4p_nv | 121614 | {dsv4p_nv,glm5_2_nv} | 2 |
| dsv4p_nv | 121786 | {dsv4p_nv,glm5_2_nv} | 2 |
| dsv4p_nv | 60740 | {dsv4p_nv} | 1 |
| dsv4p_nv | 60849 | {dsv4p_nv} | 1 |
| dsv4p_nv | 60908 | {dsv4p_nv} | 1 |
| dsv4p_nv | 60835 | {dsv4p_nv} | 1 |
| dsv4p_nv | 60803 | {dsv4p_nv} | 1 |

→ R708 FALLBACK_HEALTH_THRESHOLD复活后，fallback已生效（tiers_tried=2, {dsv4p_nv,glm5_2_nv}）。但NVCF双function均上游失败。单tier ATE（tiers_tried=1, pre-R708窗口）持续~60s（FASTBREAK=2 → 2 keys per function → 30s+30s）。双tier ATE持续~122s（2 keys × 2 tiers × ~30s ceiling）。

### 3.7 dsv4p_nv 6h 按 upstream_type
| upstream_type | cnt | ok | avg_ok_ms | avg_all_ms |
|--------------|-----|-----|-----------|-----------|
| nvcf_pexec | 51 | 51 | 40.1s | 40.1s |
| NULL | 41 | 0 | — | 82.5s |

→ dsv4p_nv pexec成功路径100%成功率(51/51)，avg 40.1s。所有41失败均为ATE NULL。

---

## 四、决策分析

### 4.1 根因判断
- **NVCF上游不可用**：双tier（dsv4p_nv + glm5_2_nv）均返回NVCF错误，非HM1配置可修。
- **R708 FALLBACK_HEALTH_THRESHOLD 复活已生效**：fallback链正常工作（tiers_tried=2），但上游NVCF双function均失败。
- **FASTBREAK=2 浪费**：在双tier模式下，每个tier尝试2个key（2×30s=60s/tier），双tier浪费120s。但NVCF双function均不可用，第2key无任何救回可能。

### 4.2 优化方向
- **FASTBREAK 2→1**：每个tier仅尝试1个key，双tier ATE从~122s降为~61s（省60s）。
- **历史验证**：R559-R694共136轮稳定使用FASTBREAK=1，零回归。R695升至2是应对特定dsv4p pexec timeout场景，当前场景已不同（NVCF双tier不可用）。
- **释放BUDGET余量**：BUDGET=110，ATE从122s→61s后，剩余49s可供peer fallback超时使用（PEER_FALLBACK_TIMEOUT=45s）。

### 4.3 预期效果
- 每ATE节省~60s（122s→61s）
- 成功路径零影响（pexec成功路径不触发fastbreak）
- READY_TIME=61s后仍有49s给peer fallback（45s timeout）

---

## 五、部署记录

### 5.1 Compose 修改
```bash
# Line 591: NVU_PEXEC_TIMEOUT_FASTBREAK: "2" → "1"
# 追加注释: R709 (HM2→HM1): NVU_PEXEC_TIMEOUT_FASTBREAK 2→1 (-1 key)
```

### 5.2 重启
```bash
cd /opt/cc-infra && docker compose up -d nv_gw
# → Container nv_gw Recreated, Started
```

### 5.3 验证
| 验证项 | 结果 |
|--------|------|
| docker ps | Up 6 seconds (healthy) ✅ |
| env NVU_PEXEC_TIMEOUT_FASTBREAK | =1 ✅ |
| docker logs --tail 20 | Clean start, no error/warn ✅ |
| /health | {"status": "ok"} ✅ |

---

## 六、下一轮建议

1. **观察R709效果**：等待足够流量验证FASTBREAK=1下ATE降至~61s，peer fallback是否有成功案例
2. **若NVCF恢复**：dsv4p_nv SR应回升至83%+（R708前R704 window峰值）
3. **若ATE持续**：可考虑NVU_PEER_FALLBACK_TIMEOUT 45→40（省5s但保留2s margin），或EMPTY_200_FASTBREAK 2→1
4. **若零错误regime**：考虑UPSTREAM_TIMEOUT 30→28（压近p95_ttfb=84.6s？需确认p95_ttfb for pexec成功路径）

## ⏳ 轮到HM1优化HM2