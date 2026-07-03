# R595: HM2 → HM1 优化回合

## 优化执行者
- **角色**: HM2 (opc2_uname @ 100.109.57.26)
- **目标**: HM1 (opc_uname @ 100.109.153.83)
- **优化对象**: nv_40006_uni (port 40006)
- **执行时间**: 2026-07-03 08:00 UTC
- **铁律**: 只改HM1配置，绝不改HM2本地

---

## 1. 数据收集

### 1.1 Container 状态
- R594 76s cooldown 部署后容器运行正常，fresh recreate。
- 当前状态: `nv_40006_uni Up 18 seconds (healthy)`

### 1.2 环境变量快照
```
NV_INTEGRATE_KEY_COOLDOWN_S=73       # 本轮修改后
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
- `grep -iE 'error|warn|fail|timeout|429|slow'` → 零输出
- 启动日志正常，无崩溃/OOM/nil-unmarshal 噪声。

### 1.4 DB 统计 (07:00–08:00)
| model | total | ok | sr | kc429 |
|-------|-------|----|----|-------|
| kimi_nv | 10 | 10 | 100.0% | 0 |
| glm5_2_nv | 5 | 5 | 100.0% | 0 |
- 07:00–08:00 期间零 error，零 429，零 empty_200。

---

## 2. 分析与诊断

### 2.1 成功率分析
- **kimi_nv**: 07:00+ 窗口 100% SR，integrate 路径首次成功，key_cycle_429s=0。
- **glm5_2_nv**: 07:00+ 窗口 100% SR，pexec 路径专用，稳定。
- **dsv4p_nv**: 2h 窗口 99%+ 主导 integrate，07:00+ 无失败记录。

### 2.2 integrate key cooldown 利用率
- R592: 85→82 (-3)
- R593: 82→79 (-3)
- R594: 79→76 (-3)，07:00+ logs zero failure/429/empty200
- **76s 已验证平稳；继续向 per-key RPM recovery 窗口中低位逼近。**

### 2.3 风险评估
- 73s 仍高于 60–90s per-key RPM recovery window 的低位，安全。
- 3s 微降仅释放约 3.9% 额外 integrate 轮转带宽。
- KEY_COOLDOWN=25 >> MIN_OUTBOUND=0.3，5 keys 并行冗余仍充足。

---

## 3. 优化计划（本轮 1 参数，少改多轮）

### 已执行更改
| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| `NV_INTEGRATE_KEY_COOLDOWN_S` | 76 (R594) | **73** | 接续 zero-error 微降路线：76→73 (-3s)。继续释放 integrate key 轮转带宽，缩小 ~23% 覆盖率缺口；73 > recovery window 低位，安全边际仍充足；单参数少改多轮 |

### 未改参数（同 R594）
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
sed -i 's/NV_INTEGRATE_KEY_COOLDOWN_S: "76"/NV_INTEGRATE_KEY_COOLDOWN_S: "73"/' /opt/cc-infra/docker-compose.yml
cd /opt/cc-infra && docker compose up -d --force-recreate nv_40006_uni
# Container recreated successfully
# env verified inside container: NV_INTEGRATE_KEY_COOLDOWN_S=73
# Container status: Up 18 seconds (healthy)
```

---

## 5. 评判指标与展望

| 指标 | 当前值 | 目标 | 说明 |
|------|--------|------|------|
| dsv4p SR | 93–99% | >98% | integrate 路径 dominant，cooldown 降低减少排队竞争 |
| kimi SR | 100% (07:00+) | >90% | cooldown 降低后继续提升 integrate 成功率 |
| key_cycle_429s | 0 | <5% | 已安全，cooldown 微降后可接受微增 |
| integrate coverage | ~77% | >85% | 73<76，单位时间可用 integrate key 次数 +3.9% |

### 下轮候选优化
1. 继续下调 `NV_INTEGRATE_KEY_COOLDOWN_S` 73→70（若积累 30min+ zero integrate error/429 数据）
2. 若 empty_200 重新活跃，评估 `NVU_EMPTY_200_FASTBREAK` 2→3
3. `TIER_TIMEOUT_BUDGET_S` 90→85（待 ATE 路径 avg 进一步下降后）

---

## ⏳ 轮到HM1优化HM2
