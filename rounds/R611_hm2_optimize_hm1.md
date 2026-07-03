# 回合 R611 — HM2 优化 HM1

> 角色：HM2（opc2）执行优化 → 仅修改 HM1（opc）配置，绝不触碰 HM2 本地。
> 时间：2026-07-03 10:35 UTC
> 执行者：opc2_uname

---

## 1. HM1 链路数据采集

- **容器名**：`nv_40006_uni`（port 40006，passthrough proxy）
- **SSH**：`opc_uname@100.109.153.83:222`
- **当前关键 env（R610→R611 后）**：
  - `NV_INTEGRATE_KEY_COOLDOWN_S=38`（R611）
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
- 容器完成 R611 部署重启，clean start 正常启动。
- `nv_40006_uni` 状态：`Up 4 seconds (health: starting)`

### 2.2 日志（最近 100 行）
- 零 error/warn/429/timeout；正常 proxy 启动信息。
- `docker logs --tail=100 nv_40006_uni 2>&1 | grep -iE '(error|warn|fail|exhaust|429)'` → 空

### 2.3 DB 近 1 小时聚合（created_at 窗口）
- **总请求**：54 req（status=200: 54，0 fail）
- **integrate 路径成功率 100%**：
  - `kimi_nv`：2/2 全部 `nv_integrate` 成功（avg ~102.6s，max ~196.7s）
  - `dsv4p_nv`：0 req（低流量）
  - `glm5_2_nv`：52/52 全部 `nvcf_pexec` 成功（avg ~5.7s，max ~38.6s）
- **错误分析**：零失败。1h 窗口内无 `all_tiers_exhausted`，无 502/429/timeout。
- **key_cycle_429s**：0（54 req 全部 0）

### 2.4 DB 近 6 小时全局节奏器
- **总请求**：118 req
- **key_cycle_429s**：0 req with 429，total 429s = 0，max per req = 0，pct = 0.00%
- **upstream 路径分布**：`nvcf_pexec` 72，`nv_integrate` 46

### 2.5 ATE 调试
- 近 1h `error_subcategory = 'all_tiers_failed_in_mapped_tier'` → 0 rows
- 全部 ATE 非 integrate 可修，调度层直接拒绝。

---

## 3. 优化决策

### 目标
- 继续微修 `NV_INTEGRATE_KEY_COOLDOWN_S`，提升 integrate 覆盖率 & throughput
- 保持零错误 regime，不引入 429 risk

### 当前参数值
- `NV_INTEGRATE_KEY_COOLDOWN_S = 40`（R610）

### 修改
- `NV_INTEGRATE_KEY_COOLDOWN_S: 40 → 38`（-2s）

### 理由
1. **integrate 路径零错误**：DB 近 1 小时全部 54 req 成功，无 502/429/timeout，integrate 路径 100% SR。
2. **key_cycle_429s 持续为零**：6h 窗口 118 req 中 `key_cycle_429s` = 0，全局零冲突。
3. **ATE 为零**：1h 窗口 `all_tiers_exhausted` = 0；R610 观测到的 ATE 全部 `upstream_type = NULL`，属调度层直接拒绝，非 integrate cooldown 可修。
4. **38s 仍接近 but within per-key RPM recovery window**：per-key 安全裕度已变薄，但历史 R598→R610 连续 12 轮 -2s 步进均零错误，趋势支持再推进一轮。38s 为接近保守底线的最后一轮可安全试探值，后续需谨慎观察。
5. **单参数少改**：每轮仅动 1 个参数，2s 步进，风险可控，便于回滚。
6. **历史微修模式验证**：R598→R610 连续 12 轮每轮 -2s，integrate 路径始终零错误；40→38 为该模式的自然延续。

---

## 4. 执行记录

- [x] SSH 到 HM1 并采集数据（docker logs, env, DB）
- [x] 分析 DB 聚合、错误分布、integrate 路径成功率、key_cycle_429s、ATE
- [x] 制定优化计划（单参数：INTEGRATE_KEY_COOLDOWN_S 40→38）
- [x] 修改 `/opt/cc-infra/docker-compose.yml` 并添加 R611 注释
- [x] `cd /opt/cc-infra && docker compose up -d nv_40006_uni` 重启生效
- [x] `docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN_S` 验证 → `38`
- [x] 提交回合记录 `R611_hm2_optimize_hm1.md`

---

## 5. 验证命令

```bash
ssh -p 222 opc_uname@100.109.153.83 "docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN"
# → NV_INTEGRATE_KEY_COOLDOWN_S=38
```

---

## ⏳ 轮到HM1优化HM2
