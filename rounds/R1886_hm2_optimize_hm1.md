# R1886 (HM2→HM1): NOP — 全 zombie_empty_completion NVCF content-filter 非 config 可修

## 触发
- Commit `cba7d70` (R1885 HM2 cc2) — false trigger, HM2 自提交，脚本正确识别"不触发"但 cron 仍派遣
- 前一 HM2→HM1 回合: R1884 (UPSTREAM_TIMEOUT 45→43)

## 改前数据

### 6h 窗口 (2026-07-19 ~06:35–12:35 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 49 |
| 成功 | 18 (36.7%) |
| 失败 | 31 (63.3%) |
| Phantom ATE (status=200 rescued) | 11 |

**Per-model:**

| Model | Total | OK | Fail | SR | avg_ok_ms |
|-------|-------|-----|------|-----|-----------|
| glm5_2_nv | 43 | 13 | 30 | 30.2% | 6780 |
| dsv4p_nv | 6 | 5 | 1 | 83.3% | 6528 |

**6h OK latency:** avg=6710ms, max=15650ms

**Error breakdown (6h):**

| Error Type | Count | Model |
|-----------|-------|-------|
| zombie_empty_completion | 31 | 30 glm5_2_nv + 1 dsv4p_nv |
| all_tiers_exhausted (phantom, status=200) | 11 | 6 glm5_2_nv + 5 dsv4p_nv |

- All 31 zombies: big_input (≥115K)
- 0 fallback, 0 SSLEOF, 0 500_nv_error, 0 breaker OPEN
- 0 peer-fb triggered (fallback_occurred=f for all 49)

### 30min 窗口

| 指标 | 值 |
|------|-----|
| 总请求 | 5 |
| 成功 | 5 (100%) |
| avg_ok_ms | 4744 |
| max_ok_ms | 7153 |

BIG_INPUT breaker 主动阻断 glm5_2_nv → 30min 窗 0 zombie

### Env
- UPSTREAM_TIMEOUT=43 (R1884: 45→43)
- TIER_TIMEOUT_BUDGET_S=178
- KEY_COOLDOWN_S=44
- TIER_COOLDOWN_S=44
- NVU_TIER_BUDGET_GLM5_2_NV=60
- NVU_TIER_BUDGET_DSV4P_NV=39
- NVU_BIG_INPUT_FAIL_N=1
- NVU_BIG_INPUT_COOLDOWN_S=21600
- NVU_PEER_FALLBACK_TIMEOUT=122
- NVU_CONNECT_RESERVE_S=0
- 所有参数与 R1884 一致，零容器漂移

### 容器
- `nv_gw`: Up 10 minutes (healthy) — R1884 改后重启
- `/health`: `{"status": "ok"}`
- 0 restart, 0 中断

## 分析

### 介入条件检查
1. **SR 连破 93%**: 36.7% — 满足（但同 R1881-R1884 已证明非 config 可修）
2. **非跳��类 fallback ≥4**: 0 — 不满足
3. **breaker OPEN**: 0 — 不满足
4. **新错误分类**: 0 — 不满足

### 可调参数穷举
| 参数 | 当前值 | 可调方向 | 对 zombie 有效？ |
|------|--------|---------|-----------------|
| UPSTREAM_TIMEOUT | 43 | 41 (margin=25.35s) | ❌ zombie 2-4s fast-fail |
| TIER_BUDGET | 178 | — | ❌ R1881 已反证（收紧→SR暴跌） |
| KEY_COOLDOWN | 44 | — | ❌ R1881 已反证 |
| TIER_COOLDOWN | 44 | — | ❌ R1881 已反证 |
| BIG_INPUT_FAIL_N | 1 | — | ❌ 已是最大攻击性 |
| BIG_INPUT_COOLDOWN | 21600 | — | ❌ 缩短无益（立即再次 zombie） |

- UPSTREAM_TIMEOUT 43→41: margin=25.35s >> 3s ✓, peer-fb 41+122=163 < 178 ✓
- 但 zombie 在 2.3-4.2s 内 abort，缩短 timeout 零实际收益
- 铁律"改前必有数据"→数据说 zombie 非 timeout 问题→不改

### 关键发现
- 全部 31 条 502 为 NVCF 侧 zombie_empty_completion（content-filter 返回空 completion）
- 30min 窗 100% SR 说明 BIG_INPUT breaker 有效阻断 glm5_2_nv
- R1881-R1884 已穷尽所有调参旋钮并反证
- 处置指向查上游 NVCF 侧（R1881-R1884 结论：查 HM2 出口 IP 段 134.195.101.0/24 + NVCF 端 TLS RST/限流策略）

## 决策：NOP — 0 改
铁律「改前必有数据」— 全部 502 为 NVCF 侧 zombie_empty_completion，非 HM1 任何 config 参数可修。无新错误分类，无 fallback 恶化，无 breaker OPEN。BIG_INPUT breaker 有效工作。不改。

## 改后验证
N/A — 零修改，零容器重启

## 提交
- R1886 回合文件: `rounds/R1886_hm2_optimize_hm1.md`
- 锚点: `RN_hm2_optimize_hm1.md` → `R1886_hm2_optimize_hm1.md`
- 铁律: 只改 HM1 不改 HM2 ✓
## ⏳ 轮到HM1优化HM2
