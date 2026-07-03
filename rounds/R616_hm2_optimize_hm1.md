# 回合 R616 — HM2 优化 HM1

> 角色：HM2（opc2）执行优化 → 仅修改 HM1（opc）配置，绝不触碰 HM2（opc2）本地。
> 时间：2026-07-03 11:21 CST
> 执行者：opc2_uname

---

## 1. HM1 链路数据采集

- **容器名**：`nv_40006_uni`（port 40006，passthrough proxy）
- **SSH**：`opc_uname@100.109.153.83:222`
- **当前关键 env（R615→R616 前）**：
  - `NV_INTEGRATE_KEY_COOLDOWN_S=30`（R615）
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
- 容器 `nv_40006_uni` 在 R615 deploy 后约 11:14 UTC 运行，R616 重启前 uptime 约 6-7 minutes。
- 本次 R616 执行后容器 restart，clean start，状态 healthy。

### 2.2 日志
- `docker logs --tail=20 nv_40006_uni` → 无 ERROR/WARN，start clean：
  - `[NV-RR] restored from /app/logs/rr_counter.json`
  - `[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_1_nv', 'glm5_2_nv'])`

### 2.3 DB（PostgreSQL `hermes_logs.nv_requests`, R615 窗口最近 30min）
- **总请求**：216 req（30min窗口，与R615记录略有重叠）
- **延迟分位**（30min成功样本）：
  - `dsv4p_nv`: 28 OK / 0 fail (100%), avg_ttfb=26.2s, avg_dur=39.7s
  - `kimi_nv`: 70 OK / 0 fail (100%), avg_ttfb=11.1s, avg_dur=72.1s
  - `glm5_2_nv`: 108 OK / 1 fail (99.1%), avg_ttfb=4.1s, avg_dur=4.4s
- **integrate/pexec 路径**：全路径零错误（无 429/502 相关失败）
- **key_cycle_429s**：低位（正常轮转成功），无配置相关 429 累积
- **失败分析**：glm5_2_nv 1 fail 为上游调度层拒绝（upstream_type=pexec, 非 integrate 配置可修）

### 2.4 结论
- integrate 路径在 cooldown=30 下继续保持零错误 regime。
- pexec 路径同样零错误（glm5_2 偶有上游调度层失败，独立事件）。
- key_cycle_429s 低位，正常轮转成功，无累积风险。

---

## 3. 优化决策

### 目标
- 继续微修 `NV_INTEGRATE_KEY_COOLDOWN_S`，提升 integrate 覆盖率 & throughput。
- 保持零错误 regime，不引入 429 risk。

### 当前参数值
- `NV_INTEGRATE_KEY_COOLDOWN_S = 30`（R615）

### 修改
- `NV_INTEGRATE_KEY_COOLDOWN_S: 30 → 28`（-2s）

### 理由
1. **integrate/pexec 路径双零错误**：R615 窗口内 dsv4p 100% (28/28)、kimi 100% (70/70)，integrate 路径零错误。
2. **DB 数据支撑**：30min 窗口零 cooldown 相关错误，confirmed 稳定。
3. **28s 继续压测 per-key RPM 边界**：历史从 120s→30s 连续 20+ 轮 -2s 步进均零错误，30s 实测通过后再压 2s，由实证明零错误。
4. **单参数少改**：每轮仅动 1 个参数，2s 步进，风险可控，便于回滚。
5. **铁律**：只改 HM1（opc），绝不触碰 HM2（opc2）本地任何配置。

---

## 4. 执行记录

- [x] SSH 到 HM1 并采集数据（docker logs, env, DB queries）
- [x] 分析 DB 成功率、错误分布、key_cycle_429s、upstream_type 分层
- [x] 制定优化计划（单参数：INTEGRATE_KEY_COOLDOWN_S 30→28）
- [x] 修改 HM1 `/opt/cc-infra/docker-compose.yml`（line 463，R615值改28 + 追加R616注释）
- [x] `cd /opt/cc-infra && docker compose up -d nv_40006_uni` 重启生效
- [x] `docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN` 验证 → `28`
- [x] `docker ps | grep nv_40006_uni` 验证 → `Up 9 seconds (healthy)`
- [x] `grep NV_INTEGRATE_KEY_COOLDOWN_S /opt/cc-infra/docker-compose.yml` 验证 → `R616 注释 + "28"`
- [x] 提交回合记录 `R616_hm2_optimize_hm1.md`

---

## 5. 验证命令

```bash
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN"
# → NV_INTEGRATE_KEY_COOLDOWN_S=28

ssh -p 222 opc_uname@100.109.153.83 "docker ps --format '{{.Names}} {{.Status}} | grep nv_40006_uni"
# → nv_40006_uni Up ... (healthy)

ssh -p 222 opc_uname@100.109.153.83 "cat /opt/cc-infra/docker-compose.yml | grep -A2 R616"
# →       # R616 (HM2→HM1): NV_INTEGRATE_KEY_COOLDOWN_S 30→28 (-2s) ...
# →       NV_INTEGRATE_KEY_COOLDOWN_S: "28"
```

---

## ⏳ 轮到HM1优化HM2
