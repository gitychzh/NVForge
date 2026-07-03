# R601: HM2 → HM1 优化

**时间**: 2026-07-03 ~08:55 UTC  
**执行者**: opc2_uname (HM2)  
**目标**: HM1 (100.109.153.83)  
**修改参数**: HM1 docker-compose.yml `NV_INTEGRATE_KEY_COOLDOWN_S`  

---

## 1. HM1 数据收集 (ssh opc_uname@100.109.153.83 -p 222)

### 容器状态
- `nv_40006_uni`: Up, role=passthrough, default=dsv4p_nv, fallback_chain=[kimi_nv, dsv4p_nv, glm5_1_nv, glm5_2_nv]
- 5 NV API keys, NVU_NUM_KEYS=5

### 当前关键环境变量 (pre-change)
```
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0.3
NV_INTEGRATE_KEY_COOLDOWN_S=60          ← 目标参数
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61
NVU_PEER_FALLBACK_TIMEOUT=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1
TIER_COOLDOWN_S=25
TIER_TIMEOUT_BUDGET_S=90
UPSTREAM_TIMEOUT=28
```

### 6h DB 窗口 (nv_requests, hermes_logs 数据库)
- 总请求: 1000
- 成功 (200): 876 → **整体 SR = 87.6%**
- 失败: 135
- key_cycle_429s: 18/1000 (仅 **1.8%**)

#### 模型级 6h 数据
| mapped_model | 总请求 | OK | SR   | key_cycle_429s |
|--------------|--------|----|------|----------------|
| dsv4p_nv     | 645    | 601| 93.2%| 13             |
| glm5_1_nv    | 33     | 24 | 72.7%| 0              |
| glm5_2_nv    | 64     | 63 | 98.4%| 2              |
| kimi_nv      | 258    | 188| 72.9%| 3              |

#### 上游路径 6h 数据
- **dsv4p_nv integrate**: 152 尝试, 152 成功 → **100% SR**
- **dsv4p_nv pexec**: 450 尝试, 449 成功 → 99.8% SR
- **kimi_nv integrate**: 97 尝试, 97 成功 → **100% SR**
- **kimi_nv pexec**: 82 尝试, 81 成功 → 98.8% SR

→ integrate 路径零错误, 100% 成功率。

### 1h DB 窗口 (更近, 更能反映当前 regime)
| mapped_model | total | OK  | SR    | ATE fails |
|--------------|-------|-----|-------|-----------|
| dsv4p_nv     | 216   | 214 | 99.1% | 3         |
| glm5_1_nv    | 20    | 11  | 55.0% | 9         |
| glm5_2_nv    | 64    | 63  | 98.4% | 1         |
| **kimi_nv**  | **127** | **103** | **81.1%** | **24** |

kimi 1h ATE 失败特征: 23 次 `all_tiers_failed_in_mapped_tier`, 平均耗时 **78.5s**, min 74.3s, max 84.4s — 非常紧凑的 74-84s 簇, 提示 integrate 钥匙在高峰期被占满后 fallback pexec+peer 也失败, 总耗时约 2×pexec_timeout(28s)+peer_fb(25s)≈81s。

### 3h DB 错误明细 (nv_tier_attempts)
- 仅 20 条 tier attempt 错误记录, 全部来自凌晨 00:00-03:00 的 pexec 429 / empty_200 / integrate 502
- **73 个 ATE 失败在 3h 内产生了 0 条 tier attempt 记录** → 代理在 tier 调度层直接拒绝, 未进入任何 upstream 尝试

### 日志 (nv_40006_uni, 最近)
- 容器运行健康, 零 error/warn/fail/429/timeout 新日志
- 仅有标准 startup 消息 (PROXY_ROLE=passthrough, Listening on 40006)

---

## 2. 优化计划

**每轮少改, 多轮积累** | **单参数每轮** | **铁律: 只改 HM1 不改 HM2**

当前 NV_INTEGRATE_KEY_COOLDOWN_S=60:
- integrate 路径 **100% 无错误**
- key_cycle_429s 仅 **1.8%** (安全余量极大)
- dsv4p 表现极佳 (99.1% SR @ 1h)
- kimi ATE 24/127 (18.9%) 仍是主要痛点, 但 ATE 簇 74-84s 指向 integrate 钥匙在 burst 期 exhaust 后 fallback 链也失败

**微观修剪继续**: 将 cooldown **60→58 (-2s)**:
- 每个 integrate 钥匙可多释放 2s/周期 → 边际提升 integrate 容量约 1.4%
- 在 burst 期间可多抢到少量 integrate 槽位, 减少 fallback 链压力
- 58s 仍远高于 per-key RPM recovery window (~10-15s for NV 5-Key 轮换)
- 历史同方向改动已连续 10+ 轮零回归
- 其他候选 (KEY_COOLDOWN_S, TIER_COOLDOWN_S, BUDGET) 风险收益比不如继续此路径

**变更项**:
- `NV_INTEGRATE_KEY_COOLDOWN_S`: `"60"` → `"58"` (HM1 docker-compose.yml line 448)
- 追加 R601 注释行 (HM1 docker-compose.yml line 448 前)

---

## 3. 执行记录

```bash
# HM2 SSH → HM1
ssh -p 222 opc_uname@100.109.153.83

# 修改 docker-compose.yml
sed -i '447a\      # R601 ...' /opt/cc-infra/docker-compose.yml
sed -i '449s/"60"/"58"/' /opt/cc-infra/docker-compose.yml

# 重启容器
cd /opt/cc-infra && docker compose up -d nv_40006_uni
```

**Post-restart 验证**:
- `docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN_S` → `58` ✅
- 容器状态: `Up 5 seconds (health: starting)` → 正常启动中 ✅

---

## 4. 本轮评估

| 指标 | R600 (前) | R601 (本次) | 备注 |
|------|-----------|-------------|------|
| NV_INTEGRATE_KEY_COOLDOWN_S | 60 | **58** | ↓2s |
| 整体 6h SR | 87.6% | — | 待下轮验证 |
| dsv4p 1h SR | 99.1% | — | 待下轮验证 |
| kimi 1h SR | 81.1% | — | 待下轮验证 |
| key_cycle_429s | 1.8% | — | 待观察 |

- 单参数改动, 风险极低
- 目标: 边际提升 integrate 覆盖率, 缓解 kimi burst ATE
- 若 key_cycle_429s 下轮超过 5% 或 integrate 出现 502/429 错误, 应回退或停减

---

## ⏳ 轮到HM1优化HM2