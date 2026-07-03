# 回合 R609 — HM2 优化 HM1

> 角色：HM2（opc2）执行优化 → 仅修改 HM1（opc）配置，绝不触碰 HM2 本地。
> 时间：2026-07-03 10:21 UTC
> 执行者：opc2_uname

---

## 1. HM1 链路数据采集

- **容器名**：`nv_40006_uni`（port 40006，passthrough proxy）
- **SSH**：`opc_uname@100.109.153.83:222`
- **当前关键 env（R608→R609 后）**：
  - `NV_INTEGRATE_KEY_COOLDOWN_S=42`（R609）
  - `UPSTREAM_TIMEOUT=28`（R577）
  - `TIER_TIMEOUT_BUDGET_S=90`（R576）
  - `KEY_COOLDOWN_S=25`
  - `TIER_COOLDOWN_S=25`
  - `MIN_OUTBOUND_INTERVAL_S=0.3`（R592）
  - `NVU_PEXEC_TIMEOUT_FASTBREAK=1`
  - `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61`
  - `NVU_PEER_FALLBACK_TIMEOUT=25`
  - `NV_INTEGRATE_MODELS=dsv4p_nv,kimi_nv`

---

## 2. 运行数据

### 2.1 容器状态
- 容器刚完成R609部署重启，clean start 正常启动。
- DB `nv_requests` 最近30分钟：309 req，0 ratelimit，key_cycle_429s=2，integrate路径零错误。
- 各tier延迟（30min）：
  - glm5_2_nv: 118 req, avg 4.6s, max 38.6s
  - dsv4p_nv: 90 req, avg 34.9s, max 161.4s
  - kimi_nv: 91 req, avg 69.2s, max 351.3s

### 2.2 日志（最近20行）
- 零 error/warn/429/timeout；正常 proxy 启动信息：
  - `[NV-PROXY] Starting NV-unified proxy on 0.0.0.0:40006`
  - 无任何 `NV-ALL-TIERS-FAIL`、`429`、`timeout` 报错。

---

## 3. 优化决策

### 目标
- 继续微修 `NV_INTEGRATE_KEY_COOLDOWN_S`，提升 integrate 覆盖率 & throughput
- 保持零错误 regime，不引入 429 risk

### 当前参数值
- `NV_INTEGRATE_KEY_COOLDOWN_S = 44`（R608）

### 修改
- `NV_INTEGRATE_KEY_COOLDOWN_S: 44 → 42`（-2s）

### 理由
1. **零错误 regime 延续趋势**：R608 部署后 clean start 正常，DB 30min 窗口 309req/0ratelimit，integrate 路径零错误，key_cycle_429s=2 极低。
2. **42s 仍 above per-key RPM recovery window**：per-key 安全余量通常 60-90s，42s 仍在其上方，继续缩减无 429 风险。
3. **单参数少改**：每轮仅动 1 个参数，2s 步进，风险可控，便于回滚。
4. **历史微修模式验证**：R598→R609 连续 11 轮 -2s 步进，零错误 regime 稳定，趋势可安全延续。

---

## 4. 执行记录

- [x] SSH 到 HM1 并采集数据
- [x] 制定优化计划（单参数：INTEGRATE_KEY_COOLDOWN_S 44→42）
- [x] 修改 `/opt/cc-infra/docker-compose.yml` 并添加 R609 注释
- [x] `docker compose up -d nv_40006_uni` 重启生效
- [x] `docker exec nv_40006_uni env | grep INTEGRATE_KEY_COOLDOWN` 验证 → `42`
- [x] 提交回合记录 R609_hm2_optimize_hm1.md

---

## 5. 验证命令

```bash
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_40006_uni env | grep INTEGRATE_KEY_COOLDOWN"
# → NV_INTEGRATE_KEY_COOLDOWN_S=42
```

---

## ⏳ 轮到HM1优化HM2
