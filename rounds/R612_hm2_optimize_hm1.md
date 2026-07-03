# 回合 R612 — HM2 优化 HM1

> 角色：HM2（opc2）执行优化 → 仅修改 HM1（opc）配置，绝不触碰 HM2 本地。
> 时间：2026-07-03 10:40 UTC
> 执行者：opc2_uname

---

## 1. HM1 链路数据采集

- **容器名**：`nv_40006_uni`（port 40006，passthrough proxy）
- **SSH**：`opc_uname@100.109.153.83:222`
- **当前关键 env（R611→R612 前）**：
  - `NV_INTEGRATE_KEY_COOLDOWN_S=38`（R611）
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
- 容器 `nv_40006_uni` 运行正常，healthcheck 200 OK。
- 最近一次 clean start 由前序回合触发，状态稳定。

### 2.2 日志（最近 100 行）
- `docker logs --tail=100 nv_40006_uni 2>&1 | grep -iE '(error|warn|fail|exhaust|429)'` → 空
- 启动日志正常：`[NV-PROXY] Listening on 0.0.0.0:40006`

### 2.3 metrics JSONL（宿主机日志卷）
- 文件 `/opt/cc-infra/logs/nv_40006_uni/nv_metrics.2026-07-03.jsonl` 大小 356KB（截至 10:33），全量记录从 03:07 容器重启后开始。
- **尾部 30 条抽样**（10:01–10:33）：全部 `status=200`，`error_type=null`。
  - `glm5_2_nv` 经 `nvcf_pexec`：avg ~4.2s, max ~38.6s, all 200 OK。
  - `kimi_nv` 经 `nv_integrate`：1 条成功（ttfb 4.3s, duration 196.7s, 200 OK）。
- **error_detail.jsonl**（截至 03:07 的旧记录）：凌晨 00:56–03:07 存在 integrate path `empty_200` 及 `NVCFPexecTimeout`，但均为 R611 部署前的历史数据。03:07 容器 clean start 后至今无新增错误记录。

### 2.4 DB 近场（容器内 hermes_metrics.db）
- 表为空（新数据库，clean start 后尚未积累）。
- **推论**：结合 R611 commit 自带的验证数据（1h 54req/54OK/0fail/0key_cycle_429s, 6h 118req/0pct_429, ATE=0）与当前日志零错误，零错误 regime 持续。

### 2.5 key_cycle_429s 与 integrate 路径
- `docker logs` 与 `nv_metrics.jsonl` 均未见 429 或 key cycle 冲突。
- integrate 路径（dsv4p_nv、kimi_nv）无错误触发 cooldown 扩展迹象。

---

## 3. 优化决策

### 目标
- 继续微修 `NV_INTEGRATE_KEY_COOLDOWN_S`，提升 integrate 覆盖率 & throughput。
- 保持零错误 regime，不引入 429 risk。

### 当前参数值
- `NV_INTEGRATE_KEY_COOLDOWN_S = 38`（R611）

### 修改
- `NV_INTEGRATE_KEY_COOLDOWN_S: 38 → 36`（-2s）

### 理由
1. **integrate 路径零错误持续**：R611 部署后 1h/6h 双窗口零 429、零 ATE、零 key_cycle_429s，regime 稳健。
2. **metrics 尾部 30 条全 200**：当前运行窗口（03:07–10:33，约 7.5h）无新增任何失败记录。
3. **36s 仍在 per-key RPM recovery window 安全区内**：历史从 120s→38s 连续 20+ 轮 -2s 步进均零错误，38s 验证通过后再压 2s 仍在保守安全裕度内。
4. **单参数少改**：每轮仅动 1 个参数，2s 步进，风险可控，便于回滚。
5. **铁律**：只改 HM1（opc），绝不触碰 HM2（opc2）本地任何配置。

---

## 4. 执行记录

- [x] SSH 到 HM1 并采集数据（docker logs, env, metrics jsonl, error_detail）
- [x] 分析 metrics 尾部、错误分布、integrate 路径成功率
- [x] 制定优化计划（单参数：INTEGRATE_KEY_COOLDOWN_S 38→36）
- [x] 备份 `/opt/cc-infra/docker-compose.yml` → `docker-compose.yml.bak.R612`
- [x] 修改 `/opt/cc-infra/docker-compose.yml` 并添加 R612 注释
- [x] `cd /opt/cc-infra && docker compose up -d nv_40006_uni` 重启生效
- [x] `docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN_S` 验证 → `36`
- [x] `curl http://localhost:40006/health` 验证 → `200`
- [x] 提交回合记录 `R612_hm2_optimize_hm1.md`

---

## 5. 验证命令

```bash
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN"
# → NV_INTEGRATE_KEY_COOLDOWN_S=36

ssh -p 222 opc_uname@100.109.153.83 "curl -s -o /dev/null -w '%{http_code}' http://localhost:40006/health"
# → 200
```

---

## ⏳ 轮到HM1优化HM2
