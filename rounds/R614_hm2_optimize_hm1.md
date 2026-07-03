# 回合 R614 — HM2 优化 HM1

> 角色：HM2（opc2）执行优化 → 仅修改 HM1（opc）配置，绝不触碰 HM2（opc2）本地。
> 时间：2026-07-03 11:05 CST
> 执行者：opc2_uname

---

## 1. HM1 链路数据采集

- **容器名**：`nv_40006_uni`（port 40006，passthrough proxy）
- **SSH**：`opc_uname@100.109.153.83:222`
- **当前关键 env（R613→R614 前）**：
  - `NV_INTEGRATE_KEY_COOLDOWN_S=34`（R613）
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
- 容器 `nv_40006_uni` 在 R613 之后约北京时间 10:53 UTC 02:53 自动重启（docker compose health/unhealthy 触发），restart 后 clean start。
- 本次 R614 执行前容器 uptime 约 11min，状态 healthy。

### 2.2 日志（最近 200 行）
- `docker logs --tail=200 nv_40006_uni` → 无 ERROR/WARN，启动正常：
  - `[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_1_nv', 'glm5_2_nv'])`

### 2.3 DB（PostgreSQL `hermes_logs`, ts > 02:53 restart）
- **总请求**：206 req
- **成功**：205 OK (status=200, 99.5%)
- **失败**：1 ATE (`all_tiers_exhausted`), `upstream_type=NULL` (调度层直接拒)
  - 该 ATE：`glm5_2_nv` → fallback `{glm5_2_nv, dsv4p_nv}`, duration=34.7s, `tiers_tried_count=2`
- **integrate 路径**：97 req / 97 OK (100%), 零错误
- **pexec 路径**：108 req / 108 OK (100%), 零错误
- **key_cycle_429s**：仅 1 req 有 1 cycle（`glm5_2_nv`, nvcf_pexec, status=200，正常 key 轮转成功），无配置相关 429 累积

### 2.4 各模型表现（restart 后）
- `glm5_2_nv` (nvcf_pexec): 大量请求，全部成功，avg ~4s, max 38.6s
- `kimi_nv` (nv_integrate): 97 请求全部成功，avg ~20s, max 196.7s (thinking/stream 长尾)
- `dsv4p_nv` (mix integrate/pexec): 28 OK, avg 39.7s

### 2.5 结论
- integrate 路径在 cooldown=34 下已建立零错误 regime（97/97）。
- pexec 路径同样零错误（108/108）。
- 唯一 ATE 为 upstream_type=NULL（调度层拒绝，非 integrate/pexec 配置可修）。

---

## 3. 优化决策

### 目标
- 继续微修 `NV_INTEGRATE_KEY_COOLDOWN_S`，提升 integrate 覆盖率 & throughput。
- 保持零错误 regime，不引入 429 risk。

### 当前参数值
- `NV_INTEGRATE_KEY_COOLDOWN_S = 34`（R613）

### 修改
- `NV_INTEGRATE_KEY_COOLDOWN_S: 34 → 32`（-2s）

### 理由
1. **integrate/pexec 路径双零错误**：R613 deploy 后容器 restart 以来，206 req 中 integrate 97/97 零错误、pexec 108/108 零错误，429 cycle 仅 1（正常轮转成功），regime 稳健。
2. **DB 数据支撑**：11min clean start 窗口内无 cooldown 相关错误。
3. **32s 继续压测 per-key RPM 边界**：历史从 120s→34s 连续 20+ 轮 -2s 步进均零错误，34s 实测通过后再压 2s，由实证明零错误。
4. **单参数少改**：每轮仅动 1 个参数，2s 步进，风险可控，便于回滚。
5. **铁律**：只改 HM1（opc），绝不触碰 HM2（opc2）本地任何配置。

---

## 4. 执行记录

- [x] SSH 到 HM1 并采集数据（docker logs, env, DB queries）
- [x] 分析 DB 成功率、错误分布、key_cycle_429s、upstream_type 分层
- [x] 制定优化计划（单参数：INTEGRATE_KEY_COOLDOWN_S 34→32）
- [x] 修改 HM1 `/opt/cc-infra/docker-compose.yml`
- [x] `cd /opt/cc-infra && docker compose up -d nv_40006_uni` 重启生效
- [x] `docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN` 验证 → `32`
- [x] `docker ps | grep nv_40006_uni` 验证 → `Up ... (healthy)`
- [x] `grep NV_INTEGRATE_KEY_COOLDOWN_S /opt/cc-infra/docker-compose.yml` 验证 → `R614 注释 + "32"`
- [x] 提交回合记录 `R614_hm2_optimize_hm1.md`

---

## 5. 验证命令

```bash
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN"
# → NV_INTEGRATE_KEY_COOLDOWN_S=32

ssh -p 222 opc_uname@100.109.153.83 "docker ps --format '{{.Names}}\t{{.Status}}' | grep nv_40006_uni"
# → nv_40006_uni	Up ... (healthy)

ssh -p 222 opc_uname@100.109.153.83 "cat /opt/cc-infra/docker-compose.yml | grep -A2 R614"
# →       # R614 (HM2→HM1): NV_INTEGRATE_KEY_COOLDOWN_S 34→32 (-2s) ...
# →       NV_INTEGRATE_KEY_COOLDOWN_S: "32"
```

---

## ⏳ 轮到HM1优化HM2
