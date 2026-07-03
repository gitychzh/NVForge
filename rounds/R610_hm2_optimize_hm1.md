# 回合 R610 — HM2 优化 HM1

> 角色：HM2（opc2）执行优化 → 仅修改 HM1（opc）配置，绝不触碰 HM2 本地。
> 时间：2026-07-03 10:26 UTC
> 执行者：opc2_uname

---

## 1. HM1 链路数据采集

- **容器名**：`nv_40006_uni`（port 40006，passthrough proxy）
- **SSH**：`opc_uname@100.109.153.83:222`
- **当前关键 env（R609→R610 后）**：
  - `NV_INTEGRATE_KEY_COOLDOWN_S=40`（R610）
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
- 容器刚完成 R610 部署重启，clean start 正常启动。
- `nv_40006_uni` 状态：`Up 16 seconds (healthy)`

### 2.2 日志（最近 100 行）
- 零 error/warn/429/timeout；正常 proxy 启动信息：
  - `[NV-PROXY] Starting NV-unified proxy on 0.0.0.0:40006`
  - 无任何 `NV-ALL-TIERS-FAIL`、`429`、`timeout` 报错
- `docker logs --tail=100 nv_40006_uni 2>&1 | grep -iE '(error|warn|ERROR|WARN)'` → 空

### 2.3 DB 近 1 小时聚合（ts 窗口）
- **总请求**：328 req（200: 317，502: 11）
- **integrate 路径成功率 100%**：
  - `kimi_nv`：97/97 全部 `nv_integrate` 成功
  - `dsv4p_nv`：91/91 全部 `nv_integrate` 成功
  - 合计 188/188 integrate OK
- **错误分析**：全部 11 个 502 为 `all_tiers_exhausted`（upstream_type = NULL），系调度层直接拒绝，非 integrate cooldown 可修
- **key_cycle_429s**：最近 30 min（MAX(ts) 窗口）= 0
- **各模型延迟/状态**：
  - `glm5_2_nv`：119 req，118 OK，avg ~4.6s，max ~38.6s
  - `dsv4p_nv`：92 req，91 OK，avg ~34.9s，max ~161.4s
  - `kimi_nv`：97 req，97 OK，avg ~69.2s，max ~351.3s
  - `glm5_1_nv`：20 req，11 OK

---

## 3. 优化决策

### 目标
- 继续微修 `NV_INTEGRATE_KEY_COOLDOWN_S`，提升 integrate 覆盖率 & throughput
- 保持零错误 regime，不引入 429 risk

### 当前参数值
- `NV_INTEGRATE_KEY_COOLDOWN_S = 42`（R609）

### 修改
- `NV_INTEGRATE_KEY_COOLDOWN_S: 42 → 40`（-2s）

### 理由
1. **integrate 路径零错误**：DB 近 1 小时 `nv_integrate` 188/188 全部成功，无 502/429/timeout。
2. **key_cycle_429s 持续低位**：MAX(ts) 近 30 min 窗口 `key_cycle_429s` = 0。
3. **ATE 非 integrate 可修**：全部 11 个 502 错误 `all_tiers_exhausted`，`upstream_type = NULL`，属于调度层直接拒绝，与 integrate cooldown 无关。
4. **40s 仍 above per-key RPM recovery window**：per-key 安全余量仍充足，继续缩减不会引入 429 风险。
5. **单参数少改**：每轮仅动 1 个参数，2s 步进，风险可控，便于回滚。
6. **历史微修模式验证**：R598→R610 连续 12 轮 -2s 步进，integrate 路径始终零错误，趋势可安全延续。

---

## 4. 执行记录

- [x] SSH 到 HM1 并采集数据
- [x] 分析 DB 聚合、错误分布、integrate 路径成功率
- [x] 制定优化计划（单参数：INTEGRATE_KEY_COOLDOWN_S 42→40）
- [x] 修改 `/opt/cc-infra/docker-compose.yml` 并添加 R610 注释
- [x] `cd /opt/cc-infra && docker compose up -d nv_40006_uni` 重启生效
- [x] `docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN_S` 验证 → `40`
- [x] 提交回合记录 `R610_hm2_optimize_hm1.md`

---

## 5. 验证命令

```bash
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN"
# → NV_INTEGRATE_KEY_COOLDOWN_S=40
```

---

## ⏳ 轮到HM1优化HM2
