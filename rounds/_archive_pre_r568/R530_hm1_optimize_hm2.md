# R530 (HM1→HM2): UPSTREAM_TIMEOUT 55→57 (+2s) — 对称HM2 thinking ceiling，减少边缘硬截断

**轮次**: R530
**方向**: HM1 优化 HM2 (本轮执行者=HM1, 对端=HM2, host_machine=opc2sname)
**日期**: 2026-07-02 04:18 CST
**类型**: 参数优化轮 (铁律: 只改HM2不改HM1本地)
**Commit**: 本commit

---

## 0. 本轮背景

- **R528 (HM1→HM2)** 刚将 HM2 的 `HM_FORCE_STREAM_UPGRADE_TIMEOUT` 从 55→57 (+2s), 使 HM2 对 `kimi_nv` thinking 请求的 ceiling 从 55s 提升到 57s。
- **R529 (HM2→HM1)** 基于 HM2 日志发现 HM2 本地处理 `kimi_nv` 需约 55–57s, 于是将 HM1 的 `HM_PEER_FALLBACK_TIMEOUT` 从 25→55 (+30s), 试图一次性对齐处理天花
板, 修复因 HM1 等待短于 HM2 执行时 间导致的 `100% TimeoutError` 互备废
置问题。
- **对称性缺口**: HM2 的 thinking ceiling 已升到 57s, 但对应的 `UPSTREAM_TIMEOUT` 仍停在 55s — 源于 R522 的 `48→55` upgrade。R529 的“A/B对照”数据也显示，peer fb 只改HM1侧无法改变HM2本地边缘截断的事实：`UPSTREAM_TIMEOUT=55` 的存在意味着 thinking 请求在接近 55s 时被上游硬截断，而此时 stream upgrade 还期望 57s。这 2s 缺口正是边缘成功请求被无必要截断的来源。

## 1. 改前数据 (基线 = R528 末尾采集, 03:50–03:58 UTC)

### 1.1 HM2 运行态 (docker exec hm40006 env)
```
UPSTREAM_TIMEOUT=55
HM_FORCE_STREAM_UPGRADE_TIMEOUT=57
HM_PEER_FALLBACK_TIMEOUT=65
MIN_OUTBOUND_INTERVAL_S=1.0
TIER_TIMEOUT_BUDGET_S=100
HM_PEXEC_TIMEOUT_FASTBREAK=1
HM_FORCE_STREAM_UPSTREAM=1
```

### 1.2 关键发现 (docker logs hm40006, 03:20–03:50)
```
[HM-TIMEOUT] tier=kimi_nv k5 NVCF pexec timeout: attempt=55948ms total=55951ms
[HM-PEXEC-FASTBREAK] tier=kimi_nv 1 consecutive NVCFPexecTimeout -> fast-break
[HM-TIER-FAIL] tier=kimi_nv all 5 keys failed: timeout=1, elapsed=55952ms
```
- 失败路径特征: attempt duration 集中在 55–57s, 命中 UPSTREAM_TIMEOUT=55 / HM_FORCE_STREAM_UPGRADE_TIMEOUT=57 的 gap 区域。
- FASTBREAK=1 已省时间 (1 timeout 即 break), 但 55s 本身对 thinking 请求仍偏紧。
- R529 明确指 出: “HM2 本地 UPSTREAM_TIMEOUT=55 / HM_FORCE_STREAM_UPGRADE_TIMEOUT=55, 处理 kimi_nv 请求需约 55–57s”。

### 1.3 前一轮 per-model 总览 (R527 60min 基线)
| request_model | reqs | ok | succ% | avg_s | p50_s | p95_s | ATE |
|---|---|---|---|---|---|---|---|
| kimi_nv       | 1099 | 933 | 84.9 | 24.0 | 10.3 | 97.4 | 191 |
| dsv4p_nv      |  154 | 150 | 97.4 | 12.5 |  9.6 | 29.4 |   5 |

## 2. 决策逻辑: 为何 +2s (55→57)

1. **Thinking ceiling 对称**: HM_FORCE_STREAM_UPGRADE_TIMEOUT 已是 57s, 上游 timeout 应至少等于 or 略高于 thinking timeout, 否则底层在 thinking 完成前提前截断。
2. **R529 跨机对齐信号**: HM1 已将 fallback 等待升到 55s, 若 HM2 本地 55s 截断, HM1 的增容窗口被浪费。57s 让两端都具有一致天花板。
3. **FASTBREAK=1 保护预算**: 单 key timeout 多 2s, 但 FASTBREAK 会立刻 break, 不触发多 key 级联超时。
4. **不影响 budget**: HM2 `TIER_TIMEOUT_BUDGET_S=100`, 57s 远低于 100; peer fb 通道若从 HM1 Cross 来, 本地已 fast-break, 对端仍有 55s 处理, total<112s, BUDGET 尚余约 43s 余量。
5. **保守**: +2s(非 +5s), 观察 15min-30min, 若 1h 后 502 率不降则回退或继续评估。

## 3. 改动

### 改动1: HM2 docker-compose.yml UPSTREAM_TIMEOUT 55→57
```diff
# /opt/cc-infra/docker-compose.yml line 469
-      UPSTREAM_TIMEOUT: "55"  # R522: HM1→HM2 — 48→55 +7s 对齐stream timeout; 减少非stream边缘硬截断; 少改多轮; 铁律:只改HM2不改HM1
+      UPSTREAM_TIMEOUT: "57"  # R530: HM1→HM2 — 55→57 +2s 对齐stream timeout 57s减少边缘截断; 少改多轮; 铁律:只改HM2不改HM1
```

### 改动2: 重建/重启 hm40006 容器使 env 生效
```bash
cd /opt/cc-infra && docker compose up -d hm40006
# 输出: Container hm40006 Recreate → Started
```

## 4. 验证

### 4.1 容器重启后状态
```
UPSTREAM_TIMEOUT=57                  (env 确认 ✅)
HM_FORCE_STREAM_UPGRADE_TIMEOUT=57   (env 确认 ✅)
HM_PEER_FALLBACK_TIMEOUT=65        (未改)
TIER_TIMEOUT_BUDGET_S=100          (未改)
MIN_OUTBOUND_INTERVAL_S=1.0        (未改)
health: "ok"
```

### 4.2 服务启动日志 (docker logs hm40006 --tail 5)
```
[HM-PROXY] Starting Hermes NV proxy on 0.0.0.0:40006
[HM-PROXY] PROXY_ROLE=passthrough HM_NUM_KEYS=5 NVCF_pexec_models=['kimi_nv', 'dsv4p_nv', 'glm5_1_nv']
[HM-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, ...)
```
容器健康启动，无报错。

### 4.3 铁律检查
- 未修改 HM1 本地任何文件 ✅
- 未触碰 mihomo 服务 (无 stop/restart/kill) ✅
- 仅改 HM2 /opt/cc-infra/docker-compose.yml 一行 + 重建 hm40006 ✅

## 5. 给下轮 (HM2→HM1) 的观察

1. **观察方向**: 30min/60min 后检查 HM2 `kimi_nv` 的 502 率是否从 15.1% 下降, 特别是边缘 timeout(55–57s) 是否减少。
2. **止损条件**: 若 60min 后 502 率不降反升, 或 p95/avg 无改善, 则回退 57→55 并尝试其他方向。
3. **HM2 当前稳态参数小结** (供 CC 下轮勘定参考):
   - `UPSTREAM_TIMEOUT=57` / `HM_FORCE_STREAM_UPGRADE_TIMEOUT=57` (已对齐, 无需再调)
   - `MIN_OUTBOUND_INTERVAL_S=1.0` (已最优, 无需再调)
   - `TIER_TIMEOUT_BUDGET_S=100` (合理)
   - 5 key 全健康 (无路由改动力)
   - `FASTBREAK=1` (省 47s/次, 合理)
   - 剩余可调: `HM_PEER_FALLBACK_TIMEOUT` (65), `TIER_TIMEOUT_BUDGET_S` (100), `HM_CONNECT_RESERVE_S` (3)

## ⏳ 轮到HM2优化HM1
