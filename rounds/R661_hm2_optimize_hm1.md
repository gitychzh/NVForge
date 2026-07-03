# R661: HM2→HM1 — 优化回合报告

**回合编号**: R661  
**执行者**: HM2 (opc2_uname)  
**目标机器**: HM1 (opc_uname@100.109.153.83)  
**目标容器**: nv_40006_uni  
**时间**: 2026-07-04 05:25 UTC+8  
**上一轮**: R660 — HM1提交 FORCE_STREAM_UPGRADE_TIMEOUT 56s

---

## 1. 数据采集

### 容器日志（最近100行）
- **0 error / 0 warn** — 完全clean
- NO_ERRORS_FOUND — grep过滤error/warn/fail/timeout/429/502/exhausted无匹配
- 容器状态正常，零错误regime持续

### 容器环境变量（关键参数）
| 参数 | 值 | 说明 |
|------|-----|------|
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 56→55 | R661变更 |
| UPSTREAM_TIMEOUT | 25 | HM1→上游超时 |
| TIER_TIMEOUT_BUDGET_S | 80 | tier预算 |
| KEY_COOLDOWN_S | 25 | key冷却 |
| TIER_COOLDOWN_S | 25 | tier冷却 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | integrate冷却(已降至floor) |
| NVU_CONNECT_RESERVE_S | 0 | 连接预留(已降至floor) |
| MIN_OUTBOUND_INTERVAL_S | 0 | 输出间隔(已降至floor) |
| NVU_PEER_FALLBACK_TIMEOUT | 8 | peer fallback超时 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | pexec fastbreak(已降至floor) |
| NVU_EMPTY_200_FASTBREAK | 2 | empty200阈值 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | SSLEOF重试延迟 |

### DB统计（6小时窗口）
| 指标 | 值 |
|------|-----|
| 总请求 | 90 |
| 成功(200) | 86 (95.56%) |
| 失败 | 4 (all_tiers_exhausted, server-side) |
| pexec路径 | 63/63 (100%) |
| integrate路径 | 25/25 (100%) |
| key_cycle_429s | 0 |
| 日志error | 0 |
| ATE count | 4 (全部 NVCF平台侧 all_tiers_exhausted) |

### 延迟统计（6小时）
| 指标 | 值 |
|------|-----|
| avg latency | 33,833ms (含ATE+outlier拉高) |
| P50 latency | 4,675ms |
| P95 latency | 138,628ms (ATE+1 outlier 494s拉高) |
| max latency | 494,127ms (K2单次极端outlier, NVCF平台variance) |

### Per-key统计（6小时）
| Key | Total | OK | Errors | SR% | Avg ms | P50 ms | P95 ms | Max ms |
|-----|-------|-----|--------|-----|--------|--------|--------|--------|
| K0 | 19 | 19 | 0 | 100% | 23,742 | 4,268 | 97,132 | 236,597 |
| K1 | 17 | 17 | 0 | 100% | 23,195 | 4,626 | 89,613 | 107,733 |
| K2 | 17 | 17 | 0 | 100% | 48,380 | 3,430 | 199,690 | 494,127 |
| K3 | 16 | 16 | 0 | 100% | 41,518 | 5,156 | 206,296 | 419,075 |
| K4 | 17 | 17 | 0 | 100% | 33,187 | 4,287 | 131,267 | 319,381 |
| NULL | 4 | 0 | 4 | 0% | 37,164 | 3,110 | 120,815 | 141,293 |

### Tier Attempts（6小时）
| tier | key | error_type | count | avg_ms | max_ms |
|------|-----|------------|-------|--------|--------|
| dsv4p_nv | K3 | IntegrateTimeout | 1 | 61,412 | 61,412 |

- 1 IntegrateTimeout at 61.4s — 在FORCE_STREAM=56s之前的残留数据（R660部署前）

### 最近10条请求
- 全部 glm5_2_nv 通过 nvcf_pexec
- 全部 status=200
- 延迟范围: 1636-4897ms, P50 ~2634ms (近期请求延迟极低)

### Hourly趋势
- 23:00 UTC: 12req/9OK/3ATE — server-side低谷窗口
- 02:00 UTC: 19req/18OK/1ATE — 高峰窗口
- 03:00-05:00 UTC: 4req/h全OK, P50=2632-2774ms — 稳定低延迟

---

## 2. 数据分析与优化决策

### 评估
- **零错误regime持续**: 日志0 error/warn，0 key_cycle_429s
- **pexec路径100%成功**: 63/63, P50 ~2.6s (近期), 健康
- **integrate路径100%成功**: 25/25
- **4 ATE全部server-side all_tiers_exhausted**: NVCF平台资源耗尽，非HM1配置可修
- **FORCE_STREAM_UPGRADE_TIMEOUT trajectory**: R656-R660: 61→59→58→57→56 (-5s total), 全部安全
- **1 IntegrateTimeout残留**: 61.4s, 属于R660部署前数据，当前56s已覆盖

### 决策
继续 R656-R660 轨迹：**NVU_FORCE_STREAM_UPGRADE_TIMEOUT 56→55 (-1s)**

**理由**:
- 零错误regime下保守微调，单参数每轮
- 减少thinking请求stream超时等待1s，不影响streaming keepalive路径
- UPSTREAM_TIMEOUT=25 << 55s margin 30s 安全
- R656-R661累积: 61→55 (-6s total)，consistently safe
- 近期请求P50 ~2.6s远低于55s ceiling，实际极少触发

### 未选的备选方案
- TIER_TIMEOUT_BUDGET_S (80): 仍需观察integrate latency ceiling，494s max说明部分integrate请求极长，80s budget合理
- KEY_COOLDOWN_S (25): 已经低位，0 key_cycle_429s，无需修改
- PEER_FALLBACK_TIMEOUT (8): peer fallback未触发，无需修改
- NVU_EMPTY_200_FASTBREAK (2): 已优化，无需修改

---

## 3. 执行操作

### 修改
1. SSH到HM1: `ssh -p 222 opc_uname@100.109.153.83`
2. 修改 `/opt/cc-infra/docker-compose.yml`:
   - Line 492: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "56"` → `"55"` (sed)
   - Line 493: 插入R661注释 (python script via scp)
3. `cd /opt/cc-infra && docker compose up -d nv_40006_uni` 重启生效

### 验证
```
$ docker exec nv_40006_uni env | grep FORCE_STREAM_UPGRADE_TIMEOUT
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=55  ✓
```
- 容器状态: Up, health: starting → healthy
- 0 error in logs

---

## 4. 回合总结

| 项目 | 内容 |
|------|------|
| 变更参数 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT |
| 变更幅度 | 56 → 55 (-1s) |
| 6h成功率 | 86/90 (95.6%, zero-error regime) |
| pexec | 63/63 (100%) |
| integrate | 25/25 (100%) |
| 安全余量 | UPSTREAM=25 << 55s margin 30s |
| trajectory | 61→59→58→57→56→55 (-6s, 6轮) |
| 铁律 | ✅ 只改HM1，不改HM2 |

---

## ⏳ 轮到HM1优化HM2
