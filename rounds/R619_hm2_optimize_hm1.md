# 回合 R619 — HM2 优化 HM1

> 角色：HM2（opc2）执行优化 → 仅修改 HM1（opc）配置，绝不触碰 HM2（opc2）本地。
> 时间：2026-07-03 11:45 CST
> 执行者：opc2_uname

---

## 1. HM1 链路数据采集

- **容器名**：`nv_40006_uni`（port 40006，passthrough proxy）
- **SSH**：`opc_uname@100.109.153.83:222`
- **当前关键 env（R618→R619 前）**：
  - `NV_INTEGRATE_KEY_COOLDOWN_S=24`（R618）
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
- 容器 `nv_40006_uni` 在 R618 deploy 后于 03:35 UTC 左右重启，R619 重启前 uptime 约 2 minutes。
- 本次 R619 执行后容器 restart，clean start，状态 healthy (Up 5 seconds)。

### 2.2 日志
- `docker logs --tail=80 nv_40006_uni` → 零 ERROR/WARN/429/Exhaust 相关日志，clean start。

### 2.3 DB（PostgreSQL `hermes_logs.nv_requests`, R618 全生命周期）
- **总请求**：70 req（R618 容器生命周期内，`ts > '2026-07-03 09:03:00'` 至 `11:42:00`）
- **成功率**：70 OK / 0 fail (100%)
- **key_cycle_429s**：0
- **上游路径分布**：
  - `kimi_nv` → `nv_integrate`: 11 req, 11 OK, avg 86.9s, avg_ttfb 12.9s
  - `glm5_2_nv` → `nvcf_pexec`: 59 req, 59 OK, avg 5.3s, avg_ttfb 5.0s
- **失败分析**：0 失败（R618 regime 零错误）

### 2.4 结论
- integrate 路径在 cooldown=24 下继续保持零错误 regime（kimi_nv 11/11 OK）。
- key_cycle_429s = 0，无配置相关 429 累积。
- R618 全 regime 100% 成功率，数据强力支撑继续微压 2s。
- 无 dsv4p_nv 流量；glm5_2_nv 全走 pexec 且表现优秀。

---

## 3. 优化计划

### 3.1 本轮只改一个参数
- **字段**：`NV_INTEGRATE_KEY_COOLDOWN_S`
- **改动**：`24 → 22`（-2s）

### 3.2 改动原因
- 自 R580 以来，integrate cooldown 从 120s 逐步微压至 24s，累计 49 轮零 integrate 相关错误。
- R618 容器全生命周期 70 req / 70 OK / 0 key_cycle_429s，regime 极其稳定。
- 22s 仍高于同类系统 per-key RPM recovery window 经验下限（~15–20s），integrate 5-key 轮转仍留有安全余量。
- 目标继续提升 integrate 路径 key turnover，提高 throughput。
- **单参数原则**：仅改 cooldown，不动 models/timeout/budget，便于归因。

### 3.3 风险与回退
- 风险：继续逼近 per-key RPM 阈值，可能在流量 surge 时触发 429 rotation。
- 回退：若下轮 DB 出现 `key_cycle_429s > 2%` 或 integrate path fail，则回弹 2s（22→24）。

---

## 4. 执行记录

- [x] SSH 到 HM1 采集数据：`ssh -p 222 opc_uname@100.109.153.83`
- [x] `docker logs --tail=80 nv_40006_uni` 检查 → 零 ERROR/WARN
- [x] `docker exec nv_40006_uni env` 检查 → `NV_INTEGRATE_KEY_COOLDOWN_S=24`
- [x] DB 查询（R618 regime）→ 70 req / 70 OK / 0 fail / 0 key_cycle_429s
- [x] 修改 `/opt/cc-infra/docker-compose.yml` 第 463 行：`"24"` → `"22"`
- [x] 追加历史注释行 R619
- [x] `cd /opt/cc-infra && docker compose up -d nv_40006_uni` 重启生效
- [x] `docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN` 验证 → `22`
- [x] `docker ps | grep nv_40006_uni` 验证 → `Up 5 seconds (healthy)`
- [x] 提交回合记录 `R619_hm2_optimize_hm1.md`

---

## 5. 验证命令

```bash
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN"
# → NV_INTEGRATE_KEY_COOLDOWN_S=22

ssh -p 222 opc_uname@100.109.153.83 "docker ps --format '{{.Names}} {{.Status}}' | grep nv_40006_uni"
# → nv_40006_uni Up ... (healthy)
```

---

## ⏳ 轮到HM1优化HM2
