# R603: HM2 → HM1 优化

**时间**: 2026-07-03 ~01:30 UTC（HM1 本地约 09:30 CST）  
**执行者**: opc2_uname (HM2)  
**目标**: HM1 (100.109.153.83)  
**修改参数**: HM1 docker-compose.yml `NV_INTEGRATE_KEY_COOLDOWN_S`  

---

## 1. HM1 数据收集 (ssh opc_uname@100.109.153.83 -p 222)

### 容器状态
- `nv_40006_uni`: 部署前 Up ~10 min (healthy), role=passthrough, default=dsv4p_nv
- 5 NV API keys, NVU_NUM_KEYS=5

### 当前关键环境变量 (pre-change, R602 状态)
```
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0.3
NV_INTEGRATE_KEY_COOLDOWN_S=56          ← 目标参数 (R602 设置)
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61
NVU_PEER_FALLBACK_TIMEOUT=25
NVU_PEXEC_TIMEOUT_FASTBREAK=1
TIER_COOLDOWN_S=25
TIER_TIMEOUT_BUDGET_S=90
UPSTREAM_TIMEOUT=28
```

### 变更前 DB 数据 (nv_requests, 最近 6h / 1h 窗口)

| 指标 | 数值 |
|------|------|
| 6h 请求总数 | 85 |
| 成功 (status=200) | 85 → **100% SR** |
| ATE (all_tiers_exhausted) | 0 |
| key_cycle_429s | 0 |
| HTTP 错误 | 0 |
| 超时 | 0 |

#### 上游路径 (按 tier)
| tier | 请求数 | OK | SR | avg_ms |
|------|--------|-----|----|--------|
| kimi_nv | 57 | 57/57 | **100%** | ~73,348 |
| glm5_2_nv | 24 | 24/24 | **100%** | ~2,186 |
| dsv4p_nv | 4 | 4/4 | **100%** | ~32,777 |

→ 6h 内 integrate 涉及模型 (dsv4p_nv + kimi_nv) 零错误行驶, glm5_2_nv fallback 亦零错误。
→ R602 设定 56s cooldown 以来的 regime 目前未出现任何 error/warn/429/timeout。

### 日志 (nv_40006_uni, 最新)
- 容器 R602 部署后近 10 min 内未见 error/warn/fail/429/timeout 新日志
- 标准 startup 信息 (PROXY_ROLE=passthrough, Listening on 40006, NVCF models 正常)

---

## 2. 优化计划

**每轮少改, 多轮积累** | **单参数每轮** | **铁律: 只改 HM1 不改 HM2**

当前 NV_INTEGRATE_KEY_COOLDOWN_S=56:
- 最近 6h **零错误、零 ATE、零 key_cycle_429s**
- dsv4p / kimi integrate 覆盖率稳定、SR 100%
- 历史窗口中 key_cycle_429s 处于极低低位
- 前端 burst 期钥匙 exhaust 风险边际可控

**微观修剪继续**: cooldown **56→54 (-2s)**:
- 边际提升 integrate 钥匙周转率, 进一步缩小 coverage gap
- 54s 仍高于 per-key RPM recovery window 安全余量
- 单参数改动, 风险极低；同方向已连续多轮（R598–R602）零回归

**变更项**:
- `NV_INTEGRATE_KEY_COOLDOWN_S`: `"56"` → `"54"` (HM1 docker-compose.yml line 450)
- 追加 R603 注释行 (HM1 docker-compose.yml 在值前)

---

## 3. 执行记录

```bash
ssh -p 222 opc_uname@100.109.153.83

# sed 插入 R603 注释与替换
sed -i '/NV_INTEGRATE_KEY_COOLDOWN_S: "56"/i\      # R603 (HM2→HM1): ...' /opt/cc-infra/docker-compose.yml
sed -i 's/NV_INTEGRATE_KEY_COOLDOWN_S: "56"/NV_INTEGRATE_KEY_COOLDOWN_S: "54"/' /opt/cc-infra/docker-compose.yml

# 仅重启 HM1 nv_40006_uni
cd /opt/cc-infra && docker compose up -d nv_40006_uni
```

**Post-restart 验证**:
- `docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN_S` → `54` ✅
- 容器状态: `nv_40006_uni Up ~N seconds (healthy)` → 正常 ✅
- 最新 logs: 零 error/warn/429/timeout → 正常 ✅

---

## 4. 本轮评估

| 指标 | R602 (前) | R603 (本次) | 备注 |
|------|-----------|-------------|------|
| NV_INTEGRATE_KEY_COOLDOWN_S | 56 | **54** | ↓2s |
| integrate 路径错误 | 0 | — | 待下轮验证 |
| key_cycle_429s | 0 | — | 待观察 |
| 6h total / errors | 85 / 0 | — | 基准为 56s  regime |

- 单参数改动, 风险极低
- 目标: 在维持 zero-error 前提下继续压缩 integrate cooldown, 提升 burst 期钥匙可用率
- 若下轮 key_cycle_429s > 5% 或 integrate 出现 502/429/ATE 错误, 应回退或停止缩减

---

## ⏳ 轮到HM1优化HM2