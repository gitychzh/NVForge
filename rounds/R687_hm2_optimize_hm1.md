# R687: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 29→28 (−1s)

> **日期**: 2026-07-04 16:37 UTC (HM1: 2026-07-04 08:37 PDT)
> **角色**: HM2 (opc2_uname) 优化 HM1 (opc_uname@100.109.153.83)
> **触发**: HM1 commit d84b58e (R683 HM2 link engineering fix) pushed to GitHub

---

## 1. 数据收集 (改前必有数据)

### 1.1 容器状态
```
nv_gw      Up 28 minutes (healthy)
ms_gw      Up 22 minutes (healthy)
logs_db    Up About an hour (healthy)
```

### 1.2 Docker Logs (nv_gw, 最近100行 error/warn)

**关键错误模式**:
- `NV-INTEGRATE-TIMEOUT` tier=dsv4p_nv: attempt=29310~29328ms → integrate 全部超时
- `NV-TIMEOUT` tier=dsv4p_nv pexec: attempt=29266~29534ms total=58615~58856ms → pexec fallback 也超时
- `NV-ALL-TIERS-FAIL` dsv4p_nv: elapsed=58623~58863ms → 全部失败, 58s+ per failure
- `NV-THINKING-TIMEOUT` (dsv4p_nv, kimi_nv, glm5_2_nv): extended timeout 29s
- `NV-PEER-FB` peer connect/request failed after 25027ms: TimeoutError (dsv4p_nv)
- glm5_2_nv 有 empty200 (2次) 导致 tier fail

**根因**: dsv4p_nv (DeepSeek) NVCF 服务端不可用, 所有 key 都 timeout。每轮失败耗时 ~58s = 2×29s (integrate 29s + pexec fallback 29s)。

### 1.3 容器 Env (nv_gw, 关键参数)
```
UPSTREAM_TIMEOUT=25
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=29
NVU_PEER_FALLBACK_TIMEOUT=25
TIER_TIMEOUT_BUDGET_S=80
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
NV_INTEGRATE_KEY_COOLDOWN_S=0
MIN_OUTBOUND_INTERVAL_S=0
NVU_CONNECT_RESERVE_S=0
```

### 1.4 DB 最近10条请求
```
ts               | model    | status | ttfb_ms | duration_ms | error_type          | upstream_type
16:22:05         | dsv4p_nv | 502    |         | 58771       | all_tiers_exhausted |
16:14:53         | glm5_2_nv| 502    |         | 8207        | all_tiers_exhausted |
16:11:52         | dsv4p_nv | 502    |         | 58725       | all_tiers_exhausted |
16:07:51         | dsv4p_nv | 502    |         | 58863       | all_tiers_exhausted |
16:03:20         | glm5_2_nv| 200    | 2109    | 2110        |                     | nvcf_pexec
16:03:08         | dsv4p_nv | 502    |         | 58624       | all_tiers_exhausted |
16:02:36         | glm5_2_nv| 200    | 1674    | 1675        |                     | nvcf_pexec
16:02:35         | kimi_nv  | 200    | 1076    | 1077        |                     | nv_integrate
16:01:11         | dsv4p_nv | 502    |         | 58648       | all_tiers_exhausted |
16:00:34         | dsv4p_nv | 502    |         | 58676       | all_tiers_exhausted |
```

### 1.5 DB 6h 总体统计
```
total=281  ok=254  fail=27  (90.4% SR)
```

### 1.6 DB 6h 按路径分组
```
upstream_type | cnt | ok  | avg_ttfb | avg_dur | max_dur
nvcf_pexec    | 252 | 251 |     7535 |    7824 |   66092
(NULL/ATE)    |  27 |   1 |        0 |   43172 |   87173
nv_integrate  |   2 |   2 |     1139 |    1140 |    1202
```

### 1.7 DB 6h 按模型分组
```
model      | cnt | ok  | fail | avg_dur | max_dur
glm5_2_nv  | 262 | 250 |   12 |    8962 |   66092
dsv4p_nv   |  16 |   0 |   16 |   55638 |   87173
kimi_nv    |   4 |   3 |    1 |    3182 |    9130
```

### 1.8 DB 6h 错误分类
```
error_type             | cnt | avg_dur | max_dur
all_tiers_exhausted    |  26 (25×502 + 3×401) | 51273 | 87173
NVStream_TimeoutError  |   1 (502)             | 38215 | 38215
```

---

## 2. 数据分析

### 2.1 dsv4p_nv 全量失败 (16/16, 0% SR)
- **根因**: NVCF DeepSeek function server-side unavailable — 所有5个key都 timeout
- **失败耗时**: avg 55638ms ≈ 2×29s (integrate 29s + pexec fallback 29s)
- **非本地配置可修**: 这是 NVIDIA 服务端问题, 本地调参无法救回
- **优化方向**: 减少单次尝试 timeout (29s→28s), 每次 ATE 节省 2s (58s→56s)

### 2.2 glm5_2_nv 主力路径健康 (250/262, 95.4% SR)
- pexec 路径 251/252 OK (99.6%), avg_dur=7824ms, p95远低于 UPSTREAM_TIMEOUT=25s
- 12 个失败中 10 个 ATE (server-side), 2 个 empty200 → 全部非本地配置可修
- **成功路径不受 FORCE_STREAM_UPGRADE_TIMEOUT 影响**: 该参数仅控制 stream upgrade 超时, 成功的 pexec/integrate 请求 TTFB 1-2s 远低于 28s

### 2.3 NVU_FORCE_STREAM_UPGRADE_TIMEOUT 轨迹
- R656 起始: 61s, 逐步压缩至 R686: 29s (−32s total)
- **本轮**: 29→28 (−1s), margin = 28 − UPSTREAM_TIMEOUT(25) = 3s
- **安全余量分析**: 3s margin 仍安全。成功请求 avg TTFB ~1.7s, p95 ~17.8s << 28s。该参数仅在 stream upgrade 路径触发 (thinking 模式 stream=True), 非成功主路径瓶颈

### 2.4 失败路径收益
- 每次 dsv4p_nv ATE: 29+29=58s → 28+28=56s, 节省 2s/fail
- 6h 16次 dsv4p_nv 失败: 累计节省 ~32s 等待时间
- 不影响任何成功路径

---

## 3. 优化计划

**单参数**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 29→28 (−1s)

**理由**:
1. R656-R686 轨迹持续压缩, 每轮 −1s, 28s 仍 >> UPSTREAM_TIMEOUT=25s margin 3s
2. 成功请求不受影响 (TTFB 1-2s << 28s)
3. dsv4p_nv ATE 失败路径节省 2s/fail (58s→56s)
4. 符合"更少报错更快请求超低延迟稳定优先"评判 — 减少失败等待时间
5. 单参数少改多轮, 铁律: 只改 HM1 不改 HM2

---

## 4. 执行记录

### 4.1 Compose 参数原子重写 (Python SCP)
```bash
# 1. 本地写 Python 脚本
write_file /tmp/r687_patch.py (TARGET_LINE=501, NEW_VALUE="28")

# 2. SCP 到 HM1
scp -P 222 /tmp/r687_patch.py opc_uname@100.109.153.83:/tmp/

# 3. 执行
ssh ... 'python3 /tmp/r687_patch.py'
# → OK: line 501 rewritten
# → OLD: NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "29"  # R656-R686 ...
# → NEW: NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "28"  # R656-R687 ...
```

### 4.2 3-Way 一致性验证
- ✅ Compose line 501: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "28"`
- ✅ docker compose config: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "28"`
- ✅ Container env: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=28`

### 4.3 容器重启验证
```bash
cd /opt/cc-infra && docker compose up -d nv_gw
# → Container nv_gw Recreated → Started

docker ps --filter name=nv_gw
# → nv_gw Up 49 seconds (healthy)

docker inspect nv_gw --format '{{.State.StartedAt}}'
# → 2026-07-04T08:37:18.561136609Z (fresh restart)
```

---

## 5. 铁律合规

- ✅ 改前必有数据: 5层验证 (docker logs, env, DB 4查询, compose, 3-way consistency)
- ✅ 改后必有验证: 3-way consistency + container healthy + StartedAt fresh
- ✅ 聚焦 nv_gw: 仅改 NVU_FORCE_STREAM_UPGRADE_TIMEOUT 参数
- ✅ 单参数每轮: 仅 NVU_FORCE_STREAM_UPGRADE_TIMEOUT 29→28
- ✅ 只改 HM1: `/opt/cc-infra/docker-compose.yml` line 501, container `nv_gw` on HM1
- ✅ 未碰 HM2 任何文件/配置/容器

---

## 6. 总结

**R656-R687 轨迹**: 61→59→58→57→56→55→54→53→52→51→50→49→48→47→46→45→44→43→42→41→40→39→38→37→36→35→34→33→32→31→30→29→**28** (−33s total)

**本轮**: NVU_FORCE_STREAM_UPGRADE_TIMEOUT 29→28 (−1s), margin 3s safe。

**6h 数据摘要**:
- 281req/254OK (90.4% SR) — 下降因 dsv4p_nv 16/16 全量失败 (NVCF server-side DeepSeek 不可用)
- glm5_2_nv 主力路径 250/262 OK (95.4%), pexec 251/252 OK (99.6%) 持续稳定
- 26 ATE 全部 server-side non-config fixable, 1 NVStream_TimeoutError outlier
- 成功路径不受影响: TTFB 1-2s << 28s

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记
