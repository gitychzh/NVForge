# 回合 R615 — HM2 优化 HM1

> 角色：HM2（opc2）执行优化 → 仅修改 HM1（opc）配置，绝不触碰 HM2（opc2）本地。
> 时间：2026-07-03 11:19 CST
> 执行者：opc2_uname

---

## 1. HM1 链路数据采集

- **容器名**：`nv_40006_uni`（port 40006，passthrough proxy）
- **SSH**：`opc_uname@100.109.153.83:222`
- **当前关键 env（R614→R615 前）**：
  - `NV_INTEGRATE_KEY_COOLDOWN_S=32`（R614）
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
- 容器 `nv_40006_uni` 在 R614 deploy 后约 11:15 UTC 自动重启（docker compose up -d 触发），restart 后 clean start。
- 本次 R615 执行前容器 uptime 约 6 minutes，状态 healthy。

### 2.2 日志
- `docker logs --tail=200 nv_40006_uni` → 无 ERROR/WARN，start clean：
  - `[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_1_nv', 'glm5_2_nv'])`

### 2.3 DB（PostgreSQL `hermes_logs.nv_requests`, R614 restart 后最近 30min）
- **总请求**：216 req
- **成功**：215 OK (status=200, 99.5%)
- **失败**：1 req（502, upstream_type=NULL，调度层直接拒，非 integrate cooldown 可修）
- **integrate 路径**：100 req / 100 OK (100%)，零错误
- **pexec 路径**：115 req / 115 OK (100%)，零错误
- **key_cycle_429s**：仅 2 req 有 cycle（0.9%，正常 key 轮转成功），无配置相关 429 累积
- **延迟分位**（30min 成功样本）：P50≈平均 33.3s, P95=152.0s, P99=248.5s, max=351.3s（主要 kimi 长尾 stream）
- **失败延迟**：单曲失败 502, duration=34.7s（调度层快速拒绝）

### 2.4 结论
- integrate 路径在 cooldown=32 下继续保持零错误 regime（100/100）。
- pexec 路径同样零错误（115/115）。
- 唯一非 200 为 upstream_type=NULL 的 502（调度层拒绝），非 integrate 配置可修。
- key_cycle_429s 仅 2/216（0.9%），正常轮转成功，无累积风险。

---

## 3. 优化决策

### 目标
- 继续微修 `NV_INTEGRATE_KEY_COOLDOWN_S`，提升 integrate 覆盖率 & throughput。
- 保持零错误 regime，不引入 429 risk。

### 当前参数值
- `NV_INTEGRATE_KEY_COOLDOWN_S = 32`（R614）

### 修改
- `NV_INTEGRATE_KEY_COOLDOWN_S: 32 → 30`（-2s）

### 理由
1. **integrate/pexec 路径双零错误**：R614 deploy 后 30min 窗口内，integrate 100/100 零错误、pexec 115/115 零错误，429 cycle 仅 2（正常轮转成功），regime 稳健。
2. **DB 数据支撑**：最近 30min 零 cooldown 相关错误，confirmed 稳定。
3. **30s 继续压测 per-key RPM 边界**：历史从 120s→32s 连续 20+ 轮 -2s 步进均零错误，32s 实测通过后再压 2s，由实证明零错误。
4. **单参数少改**：每轮仅动 1 个参数，2s 步进，风险可控，便于回滚。
5. **铁律**：只改 HM1（opc），绝不触碰 HM2（opc2）本地任何配置。

---

## 4. 执行记录

- [x] SSH 到 HM1 并采集数据（docker logs, env, DB queries）
- [x] 分析 DB 成功率、错误分布、key_cycle_429s、upstream_type 分层
- [x] 制定优化计划（单参数：INTEGRATE_KEY_COOLDOWN_S 32→30）
- [x] 修改 HM1 `/opt/cc-infra/docker-compose.yml`（line 463）
- [x] `cd /opt/cc-infra && docker compose up -d nv_40006_uni` 重启生效
- [x] `docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN` 验证 → `30`
- [x] `docker ps | grep nv_40006_uni` 验证 → `Up ... (healthy)`
- [x] `grep NV_INTEGRATE_KEY_COOLDOWN_S /opt/cc-infra/docker-compose.yml` 验证 → `R615 注释 + "30"`
- [x] 提交回合记录 `R615_hm2_optimize_hm1.md`

---

## 5. 验证命令

```bash
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN"
# → NV_INTEGRATE_KEY_COOLDOWN_S=30

ssh -p 222 opc_uname@100.109.153.83 "docker ps --format '{.Names}	{.Status}' | grep nv_40006_uni"
# → nv_40006_uni	Up ... (healthy)

ssh -p 222 opc_uname@100.109.153.83 "cat /opt/cc-infra/docker-compose.yml | grep -A2 R615"
# →       # R615 (HM2→HM1): NV_INTEGRATE_KEY_COOLDOWN_S 32→30 (-2s) ...
# →       NV_INTEGRATE_KEY_COOLDOWN_S: "30"
```

---

## ⏳ 轮到HM1优化HM2
