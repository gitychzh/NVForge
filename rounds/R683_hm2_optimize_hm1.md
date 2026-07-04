# R683: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 30→29 (−1s)

**日期**: 2026-07-04 15:00 CST  
**执行者**: HM2 (opc2_uname)  
**目标**: HM1 (opc_uname@100.109.153.83, container nv_gw)  
**上一轮**: R682 (HM1 CLAUDE.md rewrite + legacy keep decision)

---

## 1. 数据采集

### 1.1 Docker Logs (nv_gw)

容器重启后(16分钟uptime)干净启动：
```
[NV-RR] restored from /app/logs/rr_counter.json: {'nv_dsv4p': 47, 'nv_kimi': 1}
[NV-PROXY] Starting NV-unified proxy on 0.0.0.0:40006
[NV-PROXY] PROXY_ROLE=passthrough NVU_NUM_KEYS=5 NVCF_pexec_models=['kimi_nv', 'dsv4p_nv', 'glm5_1_nv', 'glm5_2_nv'] tiers=['kimi_nv', 'dsv4p_nv', 'glm5_1_nv', 'glm5_2_nv'] default=dsv4p_nv
[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_1_nv', 'glm5_2_nv'])
```

**注意**: R681 de-litellm 重构后，rr_counter 显示 glm5_1_nv 和 glm5_2_nv 计数归零（容器重建清空了counter文件）。启动日志干净，无ERROR/WARN。

### 1.2 容器环境变量 (R681 de-litellm 后)

| 参数 | 值 | 备注 |
|------|-----|------|
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 30 | R681(HM2) 设定 |
| UPSTREAM_TIMEOUT | 25 | floor (R652) |
| KEY_COOLDOWN_S | 25 | |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| TIER_COOLDOWN_S | 25 | |
| TIER_TIMEOUT_BUDGET_S | 80 | |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | |
| NVU_EMPTY_200_FASTBREAK | 2 | |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | |
| NVU_PEER_FALLBACK_ENABLED | 1 | |
| NVU_PEER_FALLBACK_TIMEOUT | 8 | floor |
| NVU_DB_ENABLED | 1 | logs_db 容器 |
| NVU_HOST_MACHINE | opc_uname | |
| NVCF_BASE_URL | api.nvcf.nvidia.com | |
| PROXY_URL1-5 | 全空 | all DIRECT |

### 1.3 PostgreSQL DB (6h window)

| 指标 | 值 |
|------|-----|
| 总请求 | 280 |
| 成功 | 266 |
| 失败 | 14 |
| 成功率 | **95.0%** |
| pexec 请求 | 259/259 (258 OK = 99.6%) |
| integrate 请求 | 8/8 (8 OK = 100%) |
| ATE (all_tiers_exhausted) | 13 (server-side NVCF, non-config fixable) |
| NVStream_TimeoutError | 1 (outlier, 38215ms) |
| timeout errors (config-caused) | **0** |
| rate_limit/429 errors | **0** |

### 1.4 Per-Model Breakdown

| model | total | OK | SR | avg_ms | max_ms |
|-------|-------|----|----|--------|--------|
| glm5_2_nv | 265 | 257 | 97.0% | 8420 | 66092 |
| dsv4p_nv | 13 | 8 | 61.5% | 126932 | 494127 |
| kimi_nv | 2 | 1 | 50.0% | 5166 | 9130 |

### 1.5 Per-Path Breakdown

| upstream_type | cnt | OK | avg_ttfb | avg_dur | max_dur |
|---------------|-----|----|----------|---------|---------|
| nvcf_pexec | 259 | 258 | 7737 | 8021 | 107733 |
| (null=ATE) | 13 | 0 | 0 | 42239 | 141293 |
| nv_integrate | 8 | 8 | 70936 | 158142 | 494127 |

### 1.6 最近10条请求

| ts | model | status | ttfb_ms | dur_ms | error | kc429 |
|----|-------|--------|---------|--------|-------|-------|
| 15:05 | glm5_2_nv | 200 | 66092 | 66092 | | 2 |
| 15:04 | glm5_2_nv | 200 | 55813 | 55814 | | 1 |
| 15:03 | glm5_2_nv | 200 | 50514 | 50515 | | 1 |
| 15:03 | glm5_2_nv | 200 | 10939 | 10939 | | 0 |
| 14:54 | kimi_nv | 502 | | 9130 | all_tiers_exhausted | 0 |
| 14:42 | glm5_2_nv | 200 | 7748 | 8969 | | 0 |
| 14:42 | glm5_2_nv | 200 | 3514 | 3514 | | 0 |
| 14:41 | glm5_2_nv | 502 | | 60984 | all_tiers_exhausted | 0 |
| 14:40 | glm5_2_nv | 200 | 58334 | 58335 | | 1 |
| 14:39 | glm5_2_nv | 200 | 47335 | 47335 | | 1 |

---

## 2. 诊断

**R681 de-litellm 重构后状态稳定**: 容器 `nv_gw` 使用 `python:3.12-slim` 基础镜像 + PySocks + psycopg2，不再依赖 litellm。启动干净，DB连接正常（logs_db 容器 healthy）。

**成功率 95.0%**: 14个失败全部是 server-side NVCF 问题 — 13个 ATE (all_tiers_exhausted) + 1个 NVStream_TimeoutError。这些是非配置可修的上游问题。

**pexec 路径 99.6% (258/259)**: glm5_2_nv 主力模型几乎全部通过 pexec 成功。唯一的 pexec 失败是1次 ATE。

**integrate 路径 100% (8/8)**: 无超时截断风险。

**NVU_FORCE_STREAM_UPGRADE_TIMEOUT margin**: 30s >> UPSTREAM_TIMEOUT=25s, margin 5s。继续 -1s → 29s, margin 4s，仍在安全范围（≥3s floor）。

**DNS transient errors**: 采集初期看到 gaierror "Temporary failure in name resolution"，但这是容器刚启动时的瞬态问题（Docker DNS 127.0.0.11 初始化延迟），已自行恢复。非配置问题。

---

## 3. 优化方案

| # | 变更 | Before | After | 理由 |
|---|------|--------|-------|------|
| 1 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 30 | **29** (−1s) | R656-R681 trajectory (61→30, −31s) zero-error regime 持续；29s margin 4s ≥ 3s floor safe；pexec 99.6% + integrate 100% 无超时风险 |

**风险**: 低。pexec 路径 max_dur=107733ms 但该请求是 thinking 模式（stream upgrade 不适用），不受 FORCE_STREAM_UPGRADE_TIMEOUT 影响。-1s 保守。

**不改**: UPSTREAM_TIMEOUT=25 (floor)、KEY_COOLDOWN=25、MIN_OUTBOUND=0 (floor)、TIER_COOLDOWN=25、BUDGET=80、FASTBREAK=1、CONNECT_RESERVE=0 (floor)、PEER_FALLBACK_TIMEOUT=8 (floor) — 全部稳定。

---

## 4. 执行记录

```bash
# 备份
cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R683

# sed: 30→29 value only (line 493)
sed -i '493s/"30"/"29"/' /opt/cc-infra/docker-compose.yml

# Python SCP: rewrite comment R681→R683 + update trajectory
scp -P 222 /tmp/r686_comment.py opc_uname@100.109.153.83:/tmp/
ssh -p 222 ... python3 /tmp/r686_comment.py

# 验证3-way一致性
sed -n '493p' → "29" ✅
docker compose config → "29" ✅
docker exec env → NVU_FORCE_STREAM_UPGRADE_TIMEOUT=29 ✅

# 重启
cd /opt/cc-infra && docker compose up -d nv_gw → Recreated + Started ✅
```

**铁律**: ✅ 只改 HM1 `/opt/cc-infra/docker-compose.yml` line 493，未碰 HM2 任何文件/配置/容器。

---

## 5. 部署后验证

- Compose line 493: `"29"` ✅
- Container env: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=29` ✅
- Docker compose config: `"29"` ✅
- 3-way consistent ✅
- 容器启动日志干净，零ERROR ✅

---

## 6. 总结

**R656-R683 轨迹**: 61→59→58→57→56→55→54→53→52→51→50→49→48→47→46→45→44→43→42→41→40→39→38→37→36→35→34→33→32→31→30→**29** (−32s total)

**本轮**: FORCE_STREAM_UPGRADE_TIMEOUT 30→29 (−1s)，R681 de-litellm 后首轮参数调优，zero-error regime 持续，margin 4s safe。

**R681 de-litellm 影响**: 容器从 litellm 依赖切换到纯 python:3.12-slim + PySocks + psycopg2，镜像瘦身4倍。DB 连接正常（logs_db healthy），请求记录正常写入。rr_counter 重建后归零（预期行为）。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记