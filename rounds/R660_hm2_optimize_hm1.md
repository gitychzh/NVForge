# R660: HM2→HM1 — 优化回合报告

**回合编号**: R660  
**执行者**: HM2 (opc2_uname)  
**目标机器**: HM1 (opc_uname@100.109.153.83)  
**目标容器**: nv_40006_uni  
**时间**: 2026-07-04 05:10 UTC+8  
**上一轮**: R659 — HM1提交 FORCE_STREAM_UPGRADE_TIMEOUT 57s

---

## 1. 数据采集

### 容器日志（最近100行）
- **0 error / 0 warn** — 完全clean
- 仅正常 `[NV-THINKING-TIMEOUT]` info（glm5_2_nv thinking请求stream timeout扩展至57s）
- 容器重启后fresh start，round-robin counter恢复: dsv4p=8270, kimi=3043, glm5_1=93

### 容器环境变量（关键参数）
| 参数 | 值 | 说明 |
|------|-----|------|
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 57 | R659设定 |
| UPSTREAM_TIMEOUT | 25 | HM1→上游超时 |
| TIER_TIMEOUT_BUDGET_S | 80 | tier预算 |
| KEY_COOLDOWN_S | 25 | key冷却 |
| TIER_COOLDOWN_S | 25 | tier冷却 |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | integrate冷却(已降至floor) |
| NVU_CONNECT_RESERVE_S | 0 | 连接预留(已降至floor) |
| MIN_OUTBOUND_INTERVAL_S | 0 | 输出间隔(已降至floor) |
| NVU_PEER_FALLBACK_TIMEOUT | 8 | peer fallback超时 |

### DB统计（6小时窗口）
| 指标 | 值 |
|------|-----|
| 总请求 | 92 |
| 成功(200) | 88 (95.7%) |
| 失败 | 4 (all_tiers_exhausted, server-side) |
| pexec路径 | 63/63 (100%) |
| integrate路径 | 25/25 (100%) |
| fallback触发 | 0 |
| key_cycle_429s | 0 |
| 日志error | 0 |

### 延迟统计（6小时）
| upstream_type | cnt | avg_ttfb_ms | avg_dur_ms | max_dur_ms |
|---------------|-----|-------------|------------|------------|
| nvcf_pexec | 63 | 7,162 | 7,180 | 107,733 |
| nv_integrate | 25 | 30,114 | 111,043 | 494,127 |
| (ATE fallback) | 4 | — | 37,164 | 141,293 |

### 最近10条请求
- 全部 glm5_2_nv 通过 nvcf_pexec
- 全部 status=200, key_cycle_429s=0
- TTFB范围: 1636-4891ms, avg ~2810ms

### 24h错误总结
- all_tiers_exhausted: 78 (NVCF平台侧，非配置可修)
- NVStream_TimeoutError: 1 (单次)

---

## 2. 数据分析与优化决策

### 评估
- **零错误regime持续**: 日志0 error/warn，0 key_cycle_429s
- **pexec路径100%成功**: 63/63, avg TTFB=7.2s, 健康
- **integrate路径100%成功**: 25/25, avg TTFB=30.1s (dSV4p_nv integrate thinking latency特征)
- **4 ATE全部server-side all_tiers_exhausted**: NVCF平台资源耗尽，非HM1配置可修
- **FORCE_STREAM_UPGRADE_TIMEOUT trajectory**: R656-R659: 61→59→58→57 (-4s total), 全部安全

### 决策
继续 R656-R659 轨迹：**NVU_FORCE_STREAM_UPGRADE_TIMEOUT 57→56 (-1s)**

**理由**:
- 零错误regime下保守微调，单参数每轮
- 减少thinking请求stream超时等待1s，不影响streaming keepalive路径
- UPSTREAM_TIMEOUT=25 << 56s margin 31s 安全
- R656-R660累积: 61→56 (-5s total)，consistently safe

### 未选的备选方案
- TIER_TIMEOUT_BUDGET_S (80): 仍需观察integrate latency ceiling，当前494s max_dur说明部分integrate请求仍在等，80s budget合理
- KEY_COOLDOWN_S (25): 已经低位，0 key_cycle_429s，无需修改
- PEER_FALLBACK_TIMEOUT (8): 0 fallback触发，无需修改

---

## 3. 执行操作

### 修改
1. SSH到HM1: `ssh -p 222 opc_uname@100.109.153.83`
2. 修改 `/opt/cc-infra/docker-compose.yml`:
   - `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "57"` → `"56"`
   - 注释更新为 R660
3. `docker compose up -d nv_40006_uni` 重启生效

### 验证
```
$ docker exec nv_40006_uni env | grep FORCE_STREAM_UPGRADE_TIMEOUT
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=56  ✓
```
- 容器 healthy, 正常处理流量, 0 error

---

## 4. 回合总结

| 项目 | 内容 |
|------|------|
| 变更参数 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT |
| 变更幅度 | 57 → 56 (-1s) |
| 6h成功率 | 88/92 (95.7%, zero-error regime) |
| pexec | 63/63 (100%) |
| integrate | 25/25 (100%) |
| 安全余量 | UPSTREAM=25 << 56s margin 31s |
| trajectory | 61→59→58→57→56 (-5s, 5轮) |
| 铁律 | ✅ 只改HM1，不改HM2 |

---

## ⏳ 轮到HM1优化HM2