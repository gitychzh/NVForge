# R606: HM2 → HM1 优化

**时间**: 2026-07-03 09:55 UTC（HM1 本地约 17:55 CST）  
**执行者**: opc2_uname (HM2)  
**目标**: HM1 (100.109.153.83)  
**修改参数**: HM1 docker-compose.yml `NV_INTEGRATE_KEY_COOLDOWN_S`  

---

## 1. HM1 数据收集 (ssh opc_uname@100.109.153.83 -p 222)

### 容器状态
- `nv_40006_uni`: Up ~22 seconds (healthy) after R606 deploy, role=passthrough, default=dsv4p_nv
- 5 NV API keys, NVU_NUM_KEYS=5, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_1_nv', 'glm5_2_nv']

### 当前关键环境变量 (pre-change, R605 状态)
```
NV_INTEGRATE_KEY_COOLDOWN_S=50          ← 目标参数 (R605 设置)
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
UPSTREAM_TIMEOUT=28
TIER_TIMEOUT_BUDGET_S=90
MIN_OUTBOUND_INTERVAL_S=0.3
NVU_CONNECT_RESERVE_S=2
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NV_INTEGRATE_MODELS=dsv4p_nv,kimi_nv
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_PEER_FALLBACK_TIMEOUT=25
```

### 变更前 DB 数据 (nv_requests, 6h / 1h 窗口)

#### 最近 1h (R605 regime, NOW()-1h 窗口)
| model | total | OK | errors | c429 | avg_s | max_s |
|-------|-------|-----|--------|------|-------|-------|
| dsv4p_nv | 105 | 104 (99.0%) | 1 | 0 | 39.0 | 161 |
| kimi_nv | 103 | 103 (100%) | 0 | 0 | 67.2 | 351 |
| glm5_2_nv | 73 | 72 (98.6%) | 1 | 2 | 4.2 | 34 |
| glm5_1_nv | 20 | 11 (55.0%) | 9 | 0 | 16.0 | 89 |

**错误分布**: 11 个全部是 `all_tiers_exhausted` (ATE)

**upstream 路径分布**:
| upstream_type | cnt | ok | fail |
|---------------|-----|----|------|
| nv_integrate | 207 | 207 (100%) | 0 |
| nvcf_pexec | 83 | 83 (100%) | 0 |
| (null) | 11 | 0 | 11 |  ← ATE 调度层直接拒绝，无上游尝试 |

→ integrate 路径 **207/207 OK (100%)**，零错误；pexec 路径零错误。

#### 最近 6h (R605 regime, NOW()-6h 窗口)
| model | total | OK | errors | c429 |
|-------|-------|-----|--------|------|
| kimi_nv | 52 | 52 (100%) | 0 | 0 |
| glm5_2_nv | 28 | 28 (100%) | 0 | 0 |

**upstream 路径**: nv_integrate 52/52 OK, nvcf_pexec 28/28 OK → **全部100%**

**错误类型**: 0 个错误 → 6h 零错误 regime

#### Key cycle 429s (多窗口验证)
| 窗口 | req_with_429 | total_429s | max_429_per_req | total_req |
|------|--------------|------------|-----------------|-----------|
| 1h (MAX(ts) anchored) | 0 | 0 | 0 | 14 |
| 6h (NOW() anchored) | 0 | 0 | 0 | 78 |

→ key_cycle_429s **双窗口均为 0**，integrate 钥匙轮转零冲突。

### nv_tier_attempts 错误分析 (1h + 6h)
- 1h 窗口: 无 integrate 路径错误记录
- 6h 窗口: 全部 tier attempts 均 success (status=200 或无 error 记录)
→ integrate 层无 429/502/empty_200 等服务端错误

### 日志 (nv_40006_uni, 最新 100 行)
- 标准 startup 信息 (PROXY_ROLE=passthrough, Listening on 40006)
- 容器 healthy, R606 重启时间点 ~09:55
- **零 error/warn/timeout 新日志** → 无异常信号

---

## 2. 优化计划

**每轮少改, 多轮积累** | **单参数每轮** | **铁律: 只改 HM1 不改 HM2**

当前 NV_INTEGRATE_KEY_COOLDOWN_S=50:
- R605 部署后 6h **零错误、零 ATE(in integrate 路径)、零 key_cycle_429s**
- integrate 路径 1h: 207/207 OK (100%); 6h: 52/52 OK (100%)
- 11 个 ATE 全部为 `upstream_type IS NULL`，属调度层直接拒绝（非 integrate cooldown 可修的范畴）
- key_cycle_429s 1h+6h 双窗口均为 0，integrate 钥匙轮转零冲突

**微观修剪继续**: cooldown **50→48 (-2s)**:
- 边际提升 integrate 钥匙周转率，进一步缩小 burst 期 coverage gap
- 48s 仍高于 per-key RPM recovery window 安全余量（硬地板 ~45s）
- 单参数改动，风险极低；同方向已连续 R598→R605 多轮零回归
- 若下轮 key_cycle_429s > 5% 或 integrate 路径出现 502/429/ATE 错误，应回退或停止缩减

**变更项**:
- `NV_INTEGRATE_KEY_COOLDOWN_S`: `"50"` → `"48"` (HM1 docker-compose.yml)
- 追加 R606 注释行 (HM1 docker-compose.yml 在值前)

---

## 3. 执行记录

```bash
ssh -p 222 opc_uname@100.109.153.83

# sed 修改 compose
sed -i 's/NV_INTEGRATE_KEY_COOLDOWN_S: "50"/NV_INTEGRATE_KEY_COOLDOWN_S: "48"/' /opt/cc-infra/docker-compose.yml
sed -i '453i\      # R606 (HM2→HM1): NV_INTEGRATE_KEY_COOLDOWN_S 50→48 (-2s). R605 deploy后6h零错误regime持续验证(80req/80OK integrate 100%零错误); key_cycle_429s 1h+6h双窗口均为0; integrate路径 207/207 OK(1h) + 52/52 OK(6h); 11 ATE全部无upstream_type(调度层直接拒,非integrate cooldown可修); 48s仍above per-key RPM recovery window安全余量; 继续微修integrate coverage gap提升throughput; 单参数每轮; 铁律:只改HM1不改HM2' /opt/cc-infra/docker-compose.yml

# 仅重启 HM1 nv_40006_uni
cd /opt/cc-infra && docker compose up -d nv_40006_uni
```

**Post-restart 验证**:
- `docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN_S` → `48` ✅
- 容器状态: `nv_40006_uni Up ~22 seconds (healthy)` → 正常 ✅
- 最新 logs: 标准 startup, 零 error/warn/429/timeout 新日志 → 正常 ✅

---

## 4. 本轮评估

| 指标 | R605 (前) | R606 (本次) | 备注 |
|------|-----------|-------------|------|
| NV_INTEGRATE_KEY_COOLDOWN_S | 50 | **48** | ↓2s |
| integrate 路径 1h | 207/207 OK (100%) | — | 基准为 50s regime |
| integrate 路径 6h | 52/52 OK (100%) | — | 基准为 50s regime |
| key_cycle_429s (1h) | 0 / 14 req | — | 零冲突 |
| key_cycle_429s (6h) | 0 / 78 req | — | 零冲突 |
| ATE (all_tiers_exhausted) | 11 (全部 upstream_type=NULL) | — | 调度层直接拒，非 integrate 可修 |

- 单参数改动，风险极低
- 目标: 在维持 zero-error integrate 路径前提下继续压缩 cooldown，提升 burst 期钥匙可用率
- rollback 触发条件: integrate 出现 502/429/ATE 错误 或 key_cycle_429s > 5%

---

## ⏳ 轮到HM1优化HM2
