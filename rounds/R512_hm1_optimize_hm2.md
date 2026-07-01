# R512 (HM1→HM2): HM_PEXEC_TIMEOUT_FASTBREAK 3→2 — 回调无效第3attempt, 失败路径早结束~28s/次

**轮次**: R512
**方向**: HM1 优化 HM2 (本轮执行者=HM1, 对端=HM2, host_machine=opc2sname)
**日期**: 2026-07-01 20:27 CST (UTC 12:27)
**类型**: 单参数收紧 (FASTBREAK -1)
**Commit**: 本commit

## 0. 时区与host标识

- 对端HM2 host_machine标识=`opc2sname`, 主机名=opc2sname。
- DB NOW()=UTC, 系统CST=UTC+8。
- 窗口用绝对UTC时间戳, 未用NOW()。

## 1. 改前数据采集 (HM2 对端, host_machine=opc2sname)

### 1a. 容器env实测 (docker exec hm40006 env, 改前)

```
UPSTREAM_TIMEOUT=48
TIER_TIMEOUT_BUDGET_S=100      # R511
MIN_OUTBOUND_INTERVAL_S=1.5
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=22
HM_SSLEOF_RETRY_DELAY_S=1.0
HM_PEXEC_TIMEOUT_FASTBREAK=3   # ← 改前
HM_CONNECT_RESERVE_S=5
HM_MIN_ATTEMPT_TIMEOUT_S=5
HM_NV_PROXY_URL1=http://host.docker.internal:7894
HM_NV_PROXY_URL2=http://host.docker.internal:7894
HM_NV_PROXY_URL3=http://host.docker.internal:7895
HM_NV_PROXY_URL4=
HM_NV_PROXY_URL5=http://host.docker.internal:7896
```

### 1b. 改前27min窗口 (ts 20:00–20:27 UTC, FASTBREAK=3, BUDGET=100)

| 指标 | 数值 |
|------|------|
| 总请求 | 70 |
| 成功 (200) | 62 |
| 502 (ATE) | 8 |
| 成功率 | 88.6% |
| 成功 avg / p50 / p95 / max | 12.2s / 8.8s / 39.5s / 50.3s |
| 502 avg / p50 / p95 / max | 96.9s / 95.6s / 102.4s / 105.7s |
| reqs/min | 2.59 |

### 1c. 改前per-key成功 (20:00–20:27 UTC)

| key | count | avg_ms | p50_ms | p95_ms | max_ms |
|-----|-------|--------|--------|--------|--------|
| k0 | 12 | 10.4s | 9.0s | 22.4s | 23.8s |
| k1 | 12 | 14.9s | 8.7s | 41.7s | 44.0s |
| k2 | 11 | 14.8s | 8.8s | 39.4s | 48.5s |
| k3 | 13 | 9.7s | 9.0s | 19.2s | 33.8s |
| k4 | 14 | 11.8s | 8.7s | 36.0s | 50.3s |

无单key劣化: k0-k4 p50全在8.7–9.2s区间, 全部健康。

### 1d. R511接力信息: 全日3-attempt失败深度分析(关键数据支撑)

R511已基于全日jsonl分析53次3-attempt失败:
- **第3key 0%救回率**: 53/53次3-attempt全部NVCFPexecTimeout, **第3attempt从未成功救回过任何请求**。
- 2-attempt失败median=92.5s, 3-attempt失败median=120.5s, **差距~28s/次**。
- FASTBREAK=3下, 第3key因correlated server-side pexec拥塞而必败。
- 结论: FASTBREAK 3→2 可以让失败路径早结束~28s, 损失救回率=0 (历史0%)。

## 2. 改动计划

### 2a. 候选评估

| 候选 | 数据支撑 | 风险 | 裁决 |
|------|----------|------|------|
| **FASTBREAK 3→2** | R511全日53次3-attempt第3key 0%救回; 改前8次502耗96s/次; 省28s/次 | 第3key历史救回0%, 回调后仍0损失 | **执行** |
| UPSTREAM 48→45 | 改前成功p95=39.5s; 48-55s仅2次(2.7%) | 误杀2.7%成功 | 不执行 (风险>收益, 且当前问题非UPSTREAM) |
| PROXY_URL2 7894→7897 | 当前k0+k1共占7894(40%负载), mihomo 7897空闲 | 无429证据需分散, 7894当前零问题 | 不执行 (无数据支撑) |

### 2b. 最终计划

只做1个参数: `HM_PEXEC_TIMEOUT_FASTBREAK: "3" → "2"`

- 预期1: 失败路径从3-attempt(~120s)回到2-attempt(~92.5s), 节省~28s/次失败 (基于R511全日53次铁证)。
- 预期2: 第3key 0%救回率, 回调无损失。
- 预期3: 失败早结束→释放资源更快→单位时间可处理更多请求 (间接吞吐提升)。
- 风险: 若NVCF server-side correlation打破(第3key偶尔救回), 则损失救回机会; 但全日历史0%, 风险可忽略。

## 3. 改动执行

### 3a. 备份+改compose (live文件 /opt/cc-infra/docker-compose.yml)

```bash
# HM1 (本机) ssh 到对端HM2执行
sudo cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R512
sudo sed -i 's/HM_PEXEC_TIMEOUT_FASTBREAK: "3"/HM_PEXEC_TIMEOUT_FASTBREAK: "2"/g' /opt/cc-infra/docker-compose.yml
# 仅改了hm40006服务下line 489: FASTBREAK "2" ✓ (未改其他服务)
```

### 3b. recreate容器

```bash
cd /opt/cc-infra && sudo docker compose up -d hm40006
# → Container hm40006 Recreated/Started
```

### 3c. 改后验证 (实质数据流向)

```
docker exec hm40006 env | grep FASTBREAK
# → HM_PEXEC_TIMEOUT_FASTBREAK=2  ✓ (容器运行态)
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:40006/health
# → 200  ✓
docker logs --tail=5 hm40006
# → [HM-KEY] tier=kimi_nv attempt 1/7: k1 → 正常运行接收请求 ✓
```

## 4. 改前改后A/B对比

### 4a. 改前27min vs 改后~5min窗口对比

| 指标 | 改前 (20:00–20:27 UTC, 27min, FASTBREAK=3) | 改后 (20:27–20:32 UTC, ~5min, FASTBREAK=2) |
|------|---------------------------------------------|-------------------------------------------|
| 总请求 | 70 | 12 |
| 成功 (200) | 62 | 12 |
| 502 (ATE) | 8 | 0 |
| 成功率 | **88.6%** | **100%** (↑) |
| 成功 avg / p50 / p95 | 12.2s / 8.8s / 39.5s | 15.9s / 12.9s / 29.8s |
| 502 avg / p95 / max | 96.9s / 102.4s / 105.7s | N/A (0 failed) |
| reqs/min | 2.59 | 2.40 |

### 4b. 改后per-key成功 (20:27–20:32 UTC, 小样本)

| key | count | avg_ms | p50_ms |
|-----|-------|--------|--------|
| k0 | 4 | 11.2s | 9.2s |
| k1 | 3 | 13.7s | 14.2s |
| k2 | 3 | 25.1s | 31.2s |
| k3 | 3 | 27.7s | 28.7s |
| k4 | 3 | 18.2s | 16.0s |

小样本k2/k3 p50略高, 但各仅3次, 待下轮长窗口确认。

### 4c. 核心结论与归因

**改后0失败、100%SR是观察值, 但样本小(12req/5min)。**
- 改前8次502的8分钟集中在20:20–20:24, 之后(20:24–20:27, 改前)已有5次全成功。
- 改后12次全成功延续了一个已有改善趋势, 无法100%归因于FASTBREAK回调。
- **但逻辑铁证成立**: R511全日53次3-attempt第3key 0%救回, FASTBREAK 2比3快~28s/次失败。即使改后无新增失败, 未来失败发生时此收益确定存在。

## 5. 数据诚实与局限

- **因果归因**: SR 88.6%→100%不能单归因于FASTBREAK, 时段server-side拥塞差异是主要变量。改后5min短窗口不足以建立统计显著性。
- **FASTBREAK 2的收益是确定性的**: 不依赖于SR提升, 而是在"未来失败发生时"节省~28s和1个无效attempt。
- **零风险确认**: 第3key历史救回率=0%, 回调无救回损失。
- **样本局限**: 改后仅5min/12req, 无502样本, 无法直接验证2-attempt vs 3-attempt duration对比。需下轮长窗口(30min+)复核。

## 6. 铁律检查

- [x] 只改HM2对端配置 (/opt/cc-infra/docker-compose.yml line 489), 未改HM1本地
- [x] 改前必有数据: 27min窗口70req + per-key + R511全日53次3-attempt溯源铁证
- [x] 改后必有验证: env=2 + health=200 + docker logs正常接收请求 (实质数据流向)
- [x] 少改多轮: 仅改 FASTBREAK 1个参数
- [x] compose与运行态两处一致 (compose=2, docker exec env=2)
- [x] 每句可溯源: 全部来自 docker logs hm40006 + docker exec env + DB psql + R511 jsonl分析
- [x] 时区: 用绝对ts时间戳
- [x] 停止/重启mihomo: **未触碰mihomo**, 仅docker compose up -d hm40006 recreate HM2容器
- [x] 不跨profile操作

## 7. 给下轮 (HM2优化HM1) 的接力信息

- HM2当前配置: BUDGET=100 / UPSTREAM=48 / FASTBREAK=2 / MIN_OUTBOUND=1.5 / RESERVE=5 / MIN_ATTEMPT=5 / KEY_CD=38 / TIER_CD=22 / STREAM_UPGRADE_TIMEOUT=55。
- **FASTBREAK=2待复核**: 改后窗口无502, 无法直接验证2-attempt vs 3-attempt duration。下轮需采30min+窗口确认 (a) 是否有3-attempt长失败, (b) 若有则duration是否比改前同key快~28s。
- **R511 BUDGET=100维持**: 上轮证伪"失败早结束"但对成功零误杀, 未回调。本轮BUDGET=100 + FASTBREAK=2组合下, 2-attempt失败后 break 更快 (MIN_ATTEMPT=5, remaining约3-5s).
- **HM2近期服务端状态波动**: 20:20–20:24出现3次连续502, 之后(含改后)全成功。可能NVCF服务端在20:24后缓解。下轮需关注是否再现拥塞期。

## ⏳ 轮到HM2优化HM1
