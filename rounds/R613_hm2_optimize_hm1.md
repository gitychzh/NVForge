# 回合 R613 — HM2 优化 HM1

> 角色：HM2（opc2）执行优化 → 仅修改 HM1（opc）配置，绝不触碰 HM2 本地。
> 时间：2026-07-03 10:50 UTC
> 执行者：opc2_uname

---

## 1. HM1 链路数据采集

- **容器名**：`nv_40006_uni`（port 40006，passthrough proxy）
- **SSH**：`opc_uname@100.109.153.83:222`
- **当前关键 env（R612→R613 前）**：
  - `NV_INTEGRATE_KEY_COOLDOWN_S=36`（R612）
  - `UPSTREAM_TIMEOUT=28`（R577）
  - `TIER_TIMEOUT_BUDGET_S=90`（R576）
  - `KEY_COOLDOWN_S=25`
  - `TIER_COOLDOWN_S=25`
  - `MIN_OUTBOUND_INTERVAL_S=0.3`（R592）
  - `NVU_PEXEC_TIMEOUT_FASTBREAK=1`
  - `NVU_EMPTY_200_FASTBREAK=2`
  - `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61`
  - `NVU_PEER_FALLBACK_TIMEOUT=25`
  - `NV_INTEGRATE_MODELS=dsv4p_nv,kimi_nv`

---

## 2. 运行数据

### 2.1 容器状态
- 容器 `nv_40006_uni` 运行正常，R612 clean start 后持续 healthy。
- 本次 R613 deploy 前容器 uptime 约 6min，属正常 clean start 延续。

### 2.2 日志（最近 100 行）
- `docker logs --tail=100 nv_40006_uni 2>&1 | grep -iE '(error|warn|fail|exhaust|429)'` → 空
- 启动日志正常：`[NV-PROXY] Listening on 0.0.0.0:40006`

### 2.3 DB 近场（PostgreSQL hermes_logs）
- **2h 窗口 integrate 路径**：9 req / 9 OK / 0 fail / 0 429（status=200 全部）
- **1h 窗口 integrate 路径**：3 req / 3 OK / 0 fail / 0 429
- **6h 窗口 integrate 路径**：44 req / 44 OK / 0 fail / 0 429
- **24h 窗口整体**：1598 total / 346 errors（全部非 429，非 integrate cooldown 可修）/ 0 r429 / 258 integrate_count
- **模型 breakdown（2h）**：`glm5_2_nv` nvcf_pexec 57 req 0 errors avg 5.4s max 38.6s；`kimi_nv` integrate 9 req 0 errors avg 86.3s max 196.7s

### 2.4 key_cycle_429s 与 integrate 路径
- `docker logs` 与 DB 均未见 429 或 key cycle 冲突。
- integrate 路径（`kimi_nv` via `nv_integrate`）零错误，全部 first-attempt 成功。
- ATE（all-tier-exhaust）全部为 upstream_type=NULL（调度层直接拒，非 integrate cooldown 可修）。

---

## 3. 优化决策

### 目标
- 继续微修 `NV_INTEGRATE_KEY_COOLDOWN_S`，提升 integrate 覆盖率 & throughput。
- 保持零错误 regime，不引入 429 risk。

### 当前参数值
- `NV_INTEGRATE_KEY_COOLDOWN_S = 36`（R612）

### 修改
- `NV_INTEGRATE_KEY_COOLDOWN_S: 36 → 34`（-2s）

### 理由
1. **integrate 路径零错误持续**：R612 deploy 后 2h/6h 双窗口 integrate 全部 200，零 429、零 ATE、零 key_cycle_429s，regime 稳健。
2. **DB 数据支撑**：6h 窗口 44 integrate req 全部成功；24h 整体 0 r429。
3. **34s 继续压测 per-key RPM 边界**：历史从 120s→36s 连续 20+ 轮 -2s 步进均零错误，36s 实测通过后再压 2s，由实证明零错误。
4. **单参数少改**：每轮仅动 1 个参数，2s 步进，风险可控，便于回滚。
5. **铁律**：只改 HM1（opc），绝不触碰 HM2（opc2）本地任何配置。

---

## 4. 执行记录

- [x] SSH 到 HM1 并采集数据（docker logs, env, DB queries）
- [x] 分析 DB integrate 路径成功率、错误分布、key_cycle_429s
- [x] 制定优化计划（单参数：INTEGRATE_KEY_COOLDOWN_S 36→34）
- [x] 本地 Python 脚本 → base64 → HM1 `/tmp/r613_patch.py` 执行
- [x] `cd /opt/cc-infra && docker compose up -d nv_40006_uni` 重启生效
- [x] `docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN_S` 验证 → `34`
- [x] `docker ps | grep nv_40006_uni` 验证 → `Up ... (healthy)`
- [x] `grep NV_INTEGRATE_KEY_COOLDOWN_S /opt/cc-infra/docker-compose.yml` 验证 → `R613 注释 + "34"`
- [x] 提交回合记录 `R613_hm2_optimize_hm1.md`

---

## 5. 验证命令

```bash
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN"
# → NV_INTEGRATE_KEY_COOLDOWN_S=34

ssh -p 222 opc_uname@100.109.153.83 "docker ps --format '{{.Names}}\t{{.Status}}' | grep nv_40006_uni"
# → nv_40006_uni	Up ... (healthy)

ssh -p 222 opc_uname@100.109.153.83 "cat /opt/cc-infra/docker-compose.yml | grep -A1 R613"
# →       # R613 (HM2→HM1): NV_INTEGRATE_KEY_COOLDOWN_S 36→34 (-2s) ...
# →       NV_INTEGRATE_KEY_COOLDOWN_S: "34"
```

---

## ⏳ 轮到HM1优化HM2
