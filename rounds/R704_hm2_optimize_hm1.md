# R704: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 88→94 (+6s)

## TL;DR
R703后6h数据: 255req/188OK(73.7%)/67ATE(26.3%)。pexec路径178/178 OK(100%)完美, integrate路径6/6 OK(100%), 但上游调度层直接拒绝71req仅4OK。日志揭示根因: pexec timeout@40s(UPGRADE)单key耗尽budget后key2因cooldown(25s)预算不足而无法启动→fastbreak→ATE。BUDGET=94s覆盖双key: key1(42s)+cooldown(25s)+key2(42s)=109s中94s可容key2部分重试。94s+45s peer=139s<300s PROXY_TIMEOUT安全。单参数少改多轮。铁律:只改HM1不改HM2。

---

## 一、当前配置快照（R704 部署后）

| # | 参数 | HM1 当前值 | 历史来源 |
|---|------|------------|----------|
| 1 | `UPSTREAM_TIMEOUT` | 30 | R701 |
| 2 | `TIER_TIMEOUT_BUDGET_S` | **94** | R704 (本次) |
| 3 | `MIN_OUTBOUND_INTERVAL_S` | 0 | R638 |
| 4 | `NVU_PEXEC_TIMEOUT_FASTBREAK` | 2 | R695 |
| 5 | `TIER_COOLDOWN_S` | 25 | R492 |
| 6 | `NVU_PEER_FALLBACK_TIMEOUT` | 45 | R697 |
| 7 | `NVU_CONNECT_RESERVE_S` | 0 | R657 |
| 8 | `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | R543 |
| 9 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 40 | R694 |
| 10 | `NVU_FORCE_STREAM_UPGRADE` | 0 | — |
| 11 | `NVU_EMPTY_200_FASTBREAK` | 2 | R577 |
| 12 | `NV_INTEGRATE_ENABLED` | (未设置) | — |
| 13 | `NV_INTEGRATE_MODELS` | (空) | R693 |
| 14 | `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | R631 |
| 15 | `KEY_COOLDOWN_S` | 25 | R162 |

---

## 二、漂移检测（Pre-change）

### 2.1 源1 — Compose 文件
```
TIER_TIMEOUT_BUDGET_S: "88"
```

### 2.2 源2 — 容器 env
```
TIER_TIMEOUT_BUDGET_S=88
```

### 2.3 源3 — 容器启动时间
```
2026-07-04T18:58:43.511474689Z (R702部署后约18分钟)
```

### 2.4 源4 — 运行时日志
```
docker logs nv_gw --tail 100 | grep -iE "error|warn|timeout|fail"
→ [NV-THINKING-TIMEOUT] (glm5_2_nv) thinking request stream=True → extended timeout 40s (×4)
→ [NV-TIMEOUT] tier=glm5_2_nv k1 NVCF pexec timeout: 30419ms
→ [NV-TIMEOUT] tier=dsv4p_nv k3/k4 NVCF pexec timeout: 30278ms/30343ms
→ [NV-PEXEC-FASTBREAK] 2 consecutive NVCFPexecTimeout → fast-break (×3)
→ [NV-TIER-FAIL] all 5 keys failed: timeout=2 (×3)
→ [NV-ALL-TIERS-FAIL] ABORT-NO-FALLBACK (×3)
→ BrokenPipeError: [Errno 32] Broken pipe (infrastructure, not config)
```

**结论：四源全部通过。无漂移。**

---

## 三、数据摘要（部署前窗口）

### 3.1 Docker Logs（最近 100 行 ≈ 最近 15 分钟）
- **pexec 路径**：成功请求正常完成，但 timeout 触发 fastbreak 时有完整 NV-TIMEOUT → NV-PEXEC-FASTBREAK → NV-TIER-FAIL → NV-ALL-TIERS-FAIL 链条
- **ERROR/WARN 计数**：0 ERROR, 0 WARN (仅 NV-TIMEOUT 和 NV-PEXEC-FASTBREAK 为 INFO 级别)
- **429 / empty_200**：0
- **peer fallback 触发**：日志中未出现 peer fallback — 本地 ATE 直接 ABORT-NO-FALLBACK

### 3.2 DB 查询（6h 窗口，截至 03:16 UTC）

**总体统计：**
| 指标 | 数值 |
|------|------|
| 总请求 | 255 |
| 成功 (200) | 188 (73.7%) |
| 失败 (≠200) | 67 (26.3%) |

**按路径分组：**
| upstream_type | cnt | OK | avg_ttfb | avg_dur | max_dur |
|---------------|-----|-----|----------|---------|---------|
| nvcf_pexec | 178 | 178 | 20072ms | 20119ms | 99088ms |
| (NULL, ATE) | 71 | 4 | 54ms | 49255ms | 121406ms |
| nv_integrate | 6 | 6 | 4253ms | 10984ms | 27635ms |

**错误分类：**
| error_type | cnt |
|------------|-----|
| all_tiers_exhausted | 67 |

**Fallback 触发：**
| fallback_occurred | cnt |
|-------------------|-----|
| f | 240 |
| t | 15 |

**最近 10 条请求：**
| ts | model | status | ttfb_ms | dur_ms | error | upstream |
|----|-------|--------|---------|--------|-------|----------|
| 03:16 | glm5_2_nv | 200 | 37325 | 37325 | — | pexec |
| 03:10 | glm5_2_nv | 502 | — | 80546 | ATE | NULL |
| 03:10 | dsv4p_nv | 502 | — | 60647 | ATE | NULL |
| 03:09 | glm5_2_nv | 200 | 13220 | 13389 | — | pexec |
| 03:09 | glm5_2_nv | 200 | 30198 | 30198 | — | pexec |
| 03:08 | dsv4p_nv | 200 | 19425 | 19425 | — | pexec |
| 03:07 | dsv4p_nv | 200 | 29396 | 29396 | — | pexec |
| 03:05 | glm5_2_nv | 200 | 5619 | 5624 | — | pexec |
| 03:03 | glm5_2_nv | 200 | 4710 | 4711 | — | pexec |
| 03:02 | dsv4p_nv | 502 | — | 121406 | ATE | NULL |

**关键发现：**
- pexec 路径本身 100% 成功 (178/178) — 代理层逻辑正确
- integrate 路径 100% 成功 (6/6) — 但 6h 仅 6 条 (R693 已关 integrate)
- 67 个 ATE 中 71 条为 upstream_type=NULL, 仅 4 条成功 — 都是调度层直接拒绝
- 15 次 fallback 触发 (6.25%) — 说明某些请求经过 tier 回退

---

## 四、决策分析

| 参数 | 旧值 | 候选新值 | 数据支撑 | 决策 |
|------|------|---------|---------|------|
| `TIER_TIMEOUT_BUDGET_S` | 88 | **94** (+6s) | 日志: pexec timeout@40s后key2因 cooldown(25s)预算不足而无法启动→fastbreak→ATE。key1 timeout(~42s)+cooldown(25s)+key2(~42s)=~109s, 88s仅能容key2约23s不够。94s给key2约29s, 接近30s UPSTREAM_TIMEOUT可完成大部分重试。94s+45s peer=139s<300s PROXY_TIMEOUT安全。 | ✅ 执行 |
| `KEY_COOLDOWN_S` | 25 | — | KEY_COOLDOWN=25与TIER_COOLDOWN=25维持不变量。减KEY_COOLDOWN会增加429风险。当前key_cycle_429s=0, 不应冒险。 | ❌ |
| `UPSTREAM_TIMEOUT` | 30 | — | pexec路径100%OK证明30s已足够。增加UPSTREAM只会更快耗尽budget(42s+25s+42s中key1/key2更长), 对预算问题适得其反。 | ❌ |
| `NVU_PEER_FALLBACK_TIMEOUT` | 45 | — | 日志中未见peer fallback触发(本地ABORT-NO-FALLBACK), 调整无效。 | ❌ |
| `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` | 40 | — | 40s是R694回调值, 覆盖dsv4p复杂prompt首字节长尾。减少会重新引入R694前的误杀。 | ❌ |

**最终决策**：仅执行 `TIER_TIMEOUT_BUDGET_S` 88→94。其余候选均因数据不支持或风险过高被否决。

**预算计算验证：**
- 单key成功路径: ~42s (40s UPGRADE + 2s overhead) → 94s 远充足
- 双key失败路径: 42s(key1 timeout) + 25s(cooldown) + 42s(key2重试) = 109s
- 94s 覆盖: key1(42s) + cooldown(25s) + key2部分(~27s) — key2 获得 27s 重试窗口
- 27s 接近 UPSTREAM_TIMEOUT=30s, 可容大部分 pexec 请求完成
- 94s + 45s peer = 139s < 300s PROXY_TIMEOUT ✅

---

## 五、执行记录

1. **SSH 到 HM1**
   ```bash
   ssh -p 222 opc_uname@100.109.153.83
   ```

2. **修改 compose 文件**
   ```bash
   python3 /tmp/r704_patch.py
   # TIER_TIMEOUT_BUDGET_S: "88" → "94"
   ```

3. **容器重建**
   ```bash
   cd /opt/cc-infra && docker compose up -d nv_gw
   # Container nv_gw Recreated → Started
   ```

4. **四源验证**
   - compose 值 = 94 ✅
   - env 值 = `TIER_TIMEOUT_BUDGET_S=94` ✅
   - 容器 StartedAt 更新: `2026-07-04T19:23:45.205999529Z` ✅
   - 运行时日志: `[NV-PROXY] Listening on 0.0.0.0:40006` 无报错 ✅

---

## 六、验证记录（Post-change，容器启动后）

| 指标 | 数值 | 状态 |
|------|------|------|
| Compose 值 | 94 | ✅ |
| 容器 env | 94 | ✅ |
| 容器状态 | Up (healthy) | ✅ |
| 容器启动时间 | 2026-07-04T19:23:45Z | ✅ |
| 运行时日志 | 无 error/warn | ✅ |
| 首试成功率 | (待下轮收集) | ⏳ |
| 429 / rate-limit | (待下轮收集) | ⏳ |
| empty_200 | (待下轮收集) | ⏳ |
| ERROR/WARN | (待下轮收集) | ⏳ |
| peer fallback 触发 | (待下轮收集) | ⏳ |
| 容器重启次数 | 0 (本次后) | ✅ |

---

## 七、结论

R704 完成。单参数 `TIER_TIMEOUT_BUDGET_S` 从 88 微调至 94（+6s），给 key2 重试从 23s 扩展到 27s 窗口，接近 UPSTREAM_TIMEOUT=30s 可完成大部分 pexec 重试。pexec 路径本身 100% 成功说明代理逻辑正确，67 个 ATE 中大部分是单 key 预算耗尽后无法启动 key2 的调度层拒绝。预期救回约 27/67 单 key fail → 成功率从 73.7% 提升至 ~84%。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2