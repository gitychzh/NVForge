# R2253 (HM2→HM1): KEY_AUTHFAIL_COOLDOWN_S 35→25 (-10s)

## TL;DR
Reduce `KEY_AUTHFAIL_COOLDOWN_S` from 35s to 25s to further shrink per-key authfail recovery window. Per-key cost drops from 67s (35+8+24) to 49s (25+0+24). Combined with KEY_COOLDOWN_S=0 from R2252, this yields 157-49=108s margin for DSV4P_NV tier budget. 单参数少改多轮。铁律：只改 HM1 不改 HM2。

---

## 一、当前配置快照（R2253 部署后）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 24 | R2247 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | 157 | R2249 |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R2239 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | R2246 |
| 5 | `TIER_COOLDOWN_S` | 0 | R2241 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 122 | R2244 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R2243 |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 0.1 | R2248 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 66 | R2250 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | R2251 |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 1 | R2251 |
| 12 | `NV_INTEGRATE_ENABLED` | (not set) | — |
| 13 | `NV_INTEGRATE_MODELS` | (empty) | — |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R2251 |
| 15 | `KEY_COOLDOWN_S` | 0 | R2252 |
| 16 | `KEY_AUTHFAIL_COOLDOWN_S` | **25** | R2253 (this round) |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
KEY_AUTHFAIL_COOLDOWN_S: "35" → corrupted to 0 bytes by sed, then restored + rebuilt
```
**⚠️ 异常**: 部署前 sed 命令将 compose 文件损坏为 0 字节。通过 git 对象 blob 提取恢复，然后从运行容器 env 重建 compose + 应用 R2253 变更。

### 2.2 源2 — 容器 env
```
KEY_AUTHFAIL_COOLDOWN_S=35 (pre-change)
```

### 2.3 源3 — 容器启动时间
```
2026-07-22T12:38:20Z (post-redeploy)
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100
→ 正常运行中，无异常 error burst
```

**结论：文件恢复后四源通过。** 文件损坏（sed -i 模式匹配失败）已通过 git blob 恢复 + Python 重建修复。

---

## 三、数据摘要（部署前窗口）

### 3.1 Docker Logs
- 无 ERROR/WARN 突增
- 容器正常运行中
- 无 crash/restart 循环

### 3.2 上下文（R2252 遗留）
- R2252 将 KEY_COOLDOWN_S 从 8→0 消除 429 anti-pattern zone
- Per-key cost: KEY_AUTHFAIL(35) + UPSTREAM(24) = 59s
- DSV4P_NV tier budget: 157s → margin 98s (vs 旧 35s)
- 下一步：继续压缩 KEY_AUTHFAIL_COOLDOWN_S

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `KEY_AUTHFAIL_COOLDOWN_S` | 35 | **25** (-10s) | 每 key cost 从 59s→49s。配合 KEY_COOLDOWN_S=0，per-key 仅 49s。157s budget 下 margin 108s。auth-fail key 在 25s 后即可恢复，vs 旧 35s 快 10s。 | ✅ 执行 |
| `KEY_COOLDOWN_S` | 0 | — | 已是 0，无需再改 | ❌ |
| `UPSTREAM_TIMEOUT` | 24 | — | 已优化至 24s，per-key 仅 authfail(25) + upstream(24) = 49s，足够 | ❌ |

**最终决策**：仅执行 `KEY_AUTHFAIL_COOLDOWN_S` 35→25。单参数。

---

## 五、执行记录

### 5.1 文件恢复（异常处理）
1. **sed 损坏文件**: `sed -i '501s|...'` 将 `/opt/cc-infra/docker-compose.yml` 损坏为 0 字节
2. **备份无效**: `.bak` 文件也是 0 字节
3. **Git 恢复**: 从 HM1 本地 git 对象 (`/opt/cc-infra/.git/objects/`) 手动提取 blob `7849515d...` → 恢复 46,063 字节 compose 文件
4. **Python 重建**: 从运行容器 env (85 vars) 导出所有环境变量，以 R1459 版本 compose 为模板，用 Python `yaml.safe_load` + `yaml.dump` 重建完整 compose 文件，同时应用 `KEY_AUTHFAIL_COOLDOWN_S=35→25`

### 5.2 部署
```bash
ssh -p 222 opc_uname@100.109.153.83
docker compose --project-directory /opt/cc-infra -f /opt/cc-infra/docker-compose.yml up -d nv_gw
# Container nv_gw Recreated + Started
```

### 5.3 四源验证
- compose 值 = `KEY_AUTHFAIL_COOLDOWN_S=25` ✅
- 容器 env = `KEY_AUTHFAIL_COOLDOWN_S=25` ✅
- 容器 StartedAt = `2026-07-22T12:38:20Z` (更新) ✅
- 运行时日志无报错 ✅

---

## 六、验证记录（Post-change）

| 指标 | 数值 | 状态 |
|------|------|------|
| 首试成功率 | 待后续轮次验证 | ⏳ |
| 429 / rate-limit | 待观察 | ⏳ |
| empty_200 | 待观察 | ⏳ |
| ERROR/WARN | 0 | ✅ |
| peer fallback 触发 | 待观察 | ⏳ |
| 容器重启次数 | 1 (planned) | ✅ |
| KEY_AUTHFAIL_COOLDOWN_S | 25 | ✅ |
| KEY_COOLDOWN_S | 0 | ✅ |

---

## 七、结论

R2253 完成。单参数 `KEY_AUTHFAIL_COOLDOWN_S` 从 35 微调至 25（-10s），auth-fail key 恢复时间缩短 29%。Per-key cost: 25(authfail) + 0(cooldown) + 24(upstream) = 49s，157s tier budget 下 margin 108s。

**部署异常记录**: 初始 sed 命令将 compose 文件损坏为 0 字节。通过 git blob 手动提取 + 运行容器 env 重建恢复。未来轮次应使用 Python 脚本或 `yq` 编辑 compose，避免 `sed -i` 风险。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2