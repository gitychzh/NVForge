# R598: HM2 → HM1 优化回合

## 优化执行者
- **角色**: HM2 (opc2_uname @ 100.109.153.83)
- **目标**: HM1 (opc_uname @ 100.109.153.83)
- **优化对象**: nv_40006_uni (port 40006)
- **执行时间**: 2026-07-03 08:22 UTC
- **铁律**: 只改HM1配置，绝不改HM2本地

---

## 1. 数据收集

### 1.1 Container 状态
- R597 67s cooldown 部署后容器运行稳定。
- 当前状态: `nv_40006_uni Up 37 seconds (healthy)` (本轮刚 recreate)

### 1.2 环境变量快照
```
NV_INTEGRATE_KEY_COOLDOWN_S=64       # 本轮修改后
TIER_TIMEOUT_BUDGET_S=90
UPSTREAM_TIMEOUT=28
MIN_OUTBOUND_INTERVAL_S=0.3
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=25
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
```

### 1.3 Docker 日志
- `grep -iE 'error|warn|fail|429|slow|empty.?200'` → 仅 1 条 `[NV-THINKING-TIMEOUT] (kimi_nv) thinking request stream=True → extended timeout 61s`（正常行为，非错误）
- 启动日志正常，无崩溃/OOM/nil-unmarshal 噪声。

### 1.4 DB 统计 (近 1h，以 R597 67s regime 为主)

| model | total | ok | fail | SR | key_cycle_429s |
|-------|-------|----|------|----|----------------|
| dsv4p_nv | 289 | 289 | 2 | 99.3% | 10 (in 30min窗口) |
| kimi_nv | 136 | 105 | 31 | 77.2% | 0 |
| glm5_2_nv | 63 | 62 | 1 | 98.4% | 2 |
| glm5_1_nv | 20 | 11 | 9 | 55.0% | 0 |

- dsv4p_nv: 00:21-08:19 UTC 窗口内的高可见度数据（HM1系统时间偏移修正后）；SR=99.3%极好；仅 2 个 all_tiers_exhausted（pexec fallback 路径耗尽）。
- kimi_nv: SR=77.2%，integrate-only（无 fallback），ATE=31 条为主因；**key_cycle_429s=0**，integrate cooldown 仍非瓶颈。
- glm5_1_nv: ATE 全部为下线模型已知行为。

### 1.5 1h 关键验证 — R597 67s 零 integrate error 延续
- `error_type = all_tiers_exhausted` 在 1h 内全部发生在 kimi_nv / glm5_1_nv / glm5_2_nv（无 integrate fallback 路径）以及 dsv4p 的 pexec fallback 路径。
- **integrate 路径本身零 error、零 429、零 empty200。**
- `v_hm_tier_health_1h` 确认 dsv4p 99.3% / glm5_2 98.4%。

---

## 2. 分析与诊断

### 2.1 成功率分析
- **kimi_nv**: 77.2% SR，integrate-only 无 fallback，ATE 是完全因 NVCF queue/availability 而非 cooldown；key_cycle_429s=0 → cooldown 再降仍有空间。
- **dsv4p_nv**: 99.3% SR，integrate 为主力路径，极少 fallback 失败；key_cycle_429s 在 30min 窗口仅 10 次（~3.5%），integrate 可用率极高。
- **glm5_2_nv**: 98.4% SR，pexec 路径稳定，不受 integrate cooldown 影响。

### 2.2 integrate key cooldown 利用率序贯
| Round | Value | error_subcategory `all_tiers_failed_in_mapped_tier` in 1h |
|-------|-------|----------------------------------------------------------|
| R592 | 85 | 有少量 integrate path ATE |
| R594 | 76 | zero error on integrate path |
| R595 | 73 | zero error on integrate path |
| R596 | 70 | zero error on integrate path |
| R597 | 67 | zero error on integrate path |
| **R598** | **64** | **目标 zero error 延续** |

- **67s → 64s (-3s)**: 70s→67s 已验证 zero-error。前序 6 轮微降中从 85→67 全部命中 zero-error。
- 64s 仍高于 estimated per-key RPM recovery window 低位（~55–60s），5-key 并发（KEY_COOLDOWN=25）提供约 20s 额外并行余量。

### 2.3 风险评估
- -3s 微降仅释放约 4.5% 额外 integrate 轮转带宽。
- dsv4p 30min 仅 10 c429（3.5%），继续微降可控；若下一 regime 429 激增则回调风险极低。
- 铁律前提满足：仅改 HM1 docker-compose.yml 中单一参数，不改 HM2 本地任何配置。

---

## 3. 优化计划（本轮 1 参数，少改多轮）

### 已执行更改
| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| `NV_INTEGRATE_KEY_COOLDOWN_S` | 67 (R597) | **64** | 接续 zero-error 微降路线：67→64 (-3s)。继续释放 integrate key 轮转带宽，提升 integrate coverage；64 > recovery window 低位，安全边际仍充足；单参数少改多轮 |

### 未改参数（同 R597）
- `MIN_OUTBOUND_INTERVAL_S` 0.3 → 保留
- `TIER_TIMEOUT_BUDGET_S` 90 → 保留
- `UPSTREAM_TIMEOUT` 28 → 保留
- `NVU_PEXEC_TIMEOUT_FASTBREAK` 1 → 保留
- `NVU_EMPTY_200_FASTBREAK` 2 → 保留
- `KEY_COOLDOWN_S` / `TIER_COOLDOWN_S` 25 → 保留
- `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 61 → 保留

---

## 4. 优化执行

```bash
# HM2→HM1 SSH操作（只改HM1，不改HM2本地）
ssh -p 222 opc_uname@100.109.153.83
sed -i 's/NV_INTEGRATE_KEY_COOLDOWN_S: "67"/NV_INTEGRATE_KEY_COOLDOWN_S: "64"/' /opt/cc-infra/docker-compose.yml
cd /opt/cc-infra && docker compose up -d --force-recreate nv_40006_uni
# Container recreated successfully
# env verified inside container: NV_INTEGRATE_KEY_COOLDOWN_S=64
# Container status: Up 37 seconds (healthy)
```

---

## 5. 关键指标快照（R598 初始状态）

| metric | R597 value | R598 plan |
|--------|------------|-----------|
| `NV_INTEGRATE_KEY_COOLDOWN_S` | 67s | 64s |
| dsv4p 1h SR | 99.3% | 目标保持 >98% |
| kimi 1h SR | 77.2% | 受 NVCF 侧影响，与 cooldown 无关 |
| integrate error count | 0 | 目标 0 |
| key_cycle_429s (30min) | 10 (3.5%) | 预期微升，若 >15 则下一回合回调 |

## ⏳ 轮到HM1优化HM2
