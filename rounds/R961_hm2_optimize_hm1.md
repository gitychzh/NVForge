# HM2 Optimize HM1 — Round R961

## 触发类型: REAL TRIGGER (HM1 committed new commit)

- 最新 commit: `342a959 R960: HM2→HM1 — NVU_PEXEC_TIMEOUT_FASTBREAK 1→2 (glm5_2_nv intermittent NVCFPexecTimeout, 2nd key chance, BUDGET=114>>112s safe)`
- Author: opc_uname (HM1) → HM2 轮次
- 触发脚本正确检测到 HM1 提交, 触发 HM2 优化 HM1

## 1. 改前数据 (2026-07-09 ~12:10 UTC)

### 容器状态
- 容器: `nv_gw` (通过 `docker ps --filter name=nv_gw` 找到, 实际名 `073ab585d945_nv_gw`)
- 重启时间: 2026-07-09T04:00:39Z (R960 部署后 ~10min)
- 状态: healthy

### 当前配置 (从容器 env)
- `NVU_PEXEC_TIMEOUT_FASTBREAK=2` (R960 刚改的)
- `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64` (UPSTREAM_TIMEOUT)
- `TIER_TIMEOUT_BUDGET_S=114`
- `NVU_CONNECT_RESERVE_S=0`
- `NVU_EMPTY_200_FASTBREAK=3`
- `NVU_PEER_FALLBACK_ENABLED=1`
- `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`

### 6h 统计 (容器重启后, 仅 ~10min 数据)
- 29 req, 29 OK, **100% SR**
- 24 直接成功, 5 fallback 成功 (glm5_2_nv→dsv4p_nv)
- 0 错误, 0 ATE
- tier_chain: `['glm5_2_nv', 'dsv4p_nv']` (双向 fallback 正常)

### 24h 统计 (包含 R960 前数据)
- 190 req, 189 OK, 1 ATE → **99.5% SR**
- 188 nvcf_pexec (全部 200), 1 NULL upstream_type (ATE)
- 176 直接成功 (avg 17.3s), 13 fallback 成功 (avg 113.9s), 1 ATE (121.1s)
- glm5_2_nv: 183 req (182 OK), dsv4p_nv: 6 req (全部 OK, fallback only)

### 错误分析 (24h)
- 仅 1 ATE: `c5cd6b77`, glm5_2_nv, tiers_tried_count=2, duration=121,075ms
  - fallback_actually_attempted=false, error_subcategory=all_tiers_failed_in_mapped_tier
  - start_tier_idx=2 (glm5_2_nv), 真正双 tier 耗尽

### NVCFPexecTimeout 分析 (glm5_2_nv, 24h)
- 总计 4 次 (k0:1, k1:1, k2:1, k4:2) → 均匀分布, 小样本
- max=51,796ms << UPSTREAM=64s → **非绑定** (gap=12.2s > 3s)
- NVCF 函数内部超时在 ~52s, 远早于 UPSTREAM=64s

### key_cycle_429s 分布 (glm5_2_nv, 24h)
- k0:7, k1:3, k2:7, k3:6, k4:5 → 略不均匀但小样本
- 所有带 429 的请求最终成功 (188/188 pexec OK)

### Budget Math
- FASTBREAK=2, UPSTREAM=64, BUDGET=114
- 2×64=128 > BUDGET=114 → **第2 key 永远无法在 BUDGET 内完成** (R768 pattern)
- 实际 NVCFPexecTimeout 在 ~52s, 所以第2 key 实际浪费 ~52s (不是 64s)
- FASTBREAK=1: 1×64=64 << 114 → 50s fallback 余量充足

### 时长桶分布 (24h)
- 0-10s: 101, 10-30s: 43, 30-50s: 10, 50-70s: 18, 70-90s: 6, 90-120s: 2, >120s: 9
- 50-70s 桶 18 个全部成功, 含 fallback 请求
- >120s 桶: 8 成功 (全部 fallback), 1 ATE

## 2. 优化决策

### 问题识别
R960 将 FASTBREAK 从 1→2 给 glm5_2_nv 第2 key 机会。但当前数据显示:
1. **NVCFPexecTimeout 是函数级超时** (max=51.8s << UPSTREAM=64, 均匀分布所有 key)
2. **第2 key 浪费 ~52s** — 同一 NVCF 函数, 第2 key 遇到同样的超时天花板
3. **FASTBREAK=2 超出 BUDGET 余量** (2×64=128 > 114) — R768 pattern
4. **Fallback dsv4p_nv 100% SR** (6/6 in 24h) — 可靠救援路径
5. **429 分布基本均匀** — 非 Path B 429 瓶颈

### 决策: FASTBREAK 2→1

**依据**: R731 Pattern B (uniform function-level timeout + healthy fallback) + R768 (FASTBREAK exceeds BUDGET headroom)

- FASTBREAK=1: 1 key × ~52s NVCFPexecTimeout → 立即 fallback → 省 ~52s
- BUDGET=114 >> 64 → 50s fallback 余量充足
- dsv4p_nv fallback 100% SR → 可靠救援
- 预期: 减少 glm5_2_nv 失败路径延迟 ~52s, 无 SR 劣化

### 为何不维持 FASTBREAK=2
- R960 的动机是 glm5_2_nv intermittent NVCFPexecTimeout 给 2nd key 机会
- 但 NVCFPexecTimeout 是函数级 (uniform across keys), 2nd key 无益
- 如果失败模式是 429 驱动 (key-specific), FASTBREAK=2 才有 rescue 价值 (R766 Path B)
- 当前 429 分布基本均匀, 非 key-specific 瓶颈

### 安全边界
- NVCFPexecTimeout max=51.8s << UPSTREAM=64 (gap 12.2s, 远 > 3s)
- BUDGET=114 >> 64 (50s 余量)
- Fallback 方向 100% SR → 零风险
- 对比 R960: R960 的决策基于 "504→NVCFPexecTimeout(51s)→fast-break" 模式, 但未识别这是函数级超时而非 key 级

## 3. 执行操作

### 修改
- 参数: `NVU_PEXEC_TIMEOUT_FASTBREAK: "2"` → `"1"` (docker-compose.yml line 607)
- 新增注释: line 608 (R961 回合注释)

### 部署
```bash
cd /opt/cc-infra && docker compose stop nv_gw && docker compose up -d nv_gw
```

### 验证
- `docker exec nv_gw env | grep NVU_PEXEC_TIMEOUT_FASTBREAK` → `1` ✓
- `curl http://localhost:40006/health` → `{"status": "ok"}` ✓
- YAML 语法检查通过 ✓

## 4. 评判

- 更少报错: 24h 仅 1 ATE (0.5%), 无新错误引入 ✓
- 更快请求: 失败路径省 ~52s (2nd key 浪费消除) ✓
- 超低延迟: 直接成功 avg 17.3s, 无变化 ✓
- 稳定优先: 单参数少改, 铁律遵守 ✓

## 5. 参数变更汇总

| 参数 | 旧值 | 新值 | 变化 | 原因 |
|------|------|------|------|------|
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 | 1 | -1 | 函数级 NVCFPexecTimeout, 2nd key 浪费 ~52s, fallback 100% SR 可靠 |

单参数, 铁律: 只改 HM1, 不改 HM2.

## ⏳ 轮到 HM1 优化 HM2