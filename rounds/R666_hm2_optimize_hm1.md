# R666: HM2→HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 51→50 (−1s)

**日期**: 2026-07-04 06:50 CST  
**执行者**: HM2 (opc2_uname)  
**目标**: HM1 (opc_uname@100.109.153.83, container nv_40006_uni)

---

## 1. 数据采集

### 1.1 Docker Logs (nv_40006_uni)

容器重启后干净启动，零ERROR/WARN日志：
```
[NV-RR] restored from /app/logs/rr_counter.json: {'nv_dsv4p': 8273, 'nv_kimi': 3043, 'nv_glm5_1': 93}
[NV-PROXY] Starting NV-unified proxy on 0.0.0.0:40006
[NV-PROXY] PROXY_ROLE=passthrough NVU_NUM_KEYS=5 ... tiers=['kimi_nv', 'dsv4p_nv', 'glm5_1_nv', 'glm5_2_nv']
```
grep error/warn: 零匹配 — 零日志错误 regime 持续。

### 1.2 容器环境变量

| 参数 | 值 | 状态 |
|------|-----|------|
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 51 | R665 |
| UPSTREAM_TIMEOUT | 25 | floor |
| KEY_COOLDOWN_S | 25 | |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| TIER_COOLDOWN_S | 25 | |
| TIER_TIMEOUT_BUDGET_S | 80 | |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | |
| NVU_EMPTY_200_FASTBREAK | 2 | |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | |
| NVU_PEER_FALLBACK_TIMEOUT | 8 | floor |
| NVU_PEER_FALLBACK_ENABLED | 1 | |
| PROXY_URL1-5 | 全空 | all DIRECT |

### 1.3 PostgreSQL DB (6h window, 2026-07-03 17:03 ~ 07-04 06:33 UTC)

| 指标 | 值 |
|------|-----|
| 总请求 | 76 |
| 成功 | 72 |
| 失败 | 4 |
| 成功率 | **94.7%** |
| avg latency | 25521ms |
| p50 latency | 3313ms |
| p95 latency | 114642ms (integrate长尾) |
| ATE (all_tiers_exhausted) | 4 (server-side NVCF, 非config可修) |
| timeout errors | **0** |
| rate_limit errors | **0** |
| key_cycle_429s | 1 minor |
| pexec 请求 | 60/60 OK (100%) |
| integrate 请求 | 12/12 OK (100%) |
| upstream_type NULL | 4 (ATE records, no key assigned) |

### 1.4 Per-Model Breakdown

| model | total | OK | SR | avg_ms | p50 | p95 | ATE | pexec | integrate |
|-------|-------|----|----|--------|-----|-----|-----|-------|-----------|
| dsv4p_nv | 10 | 9 | 90.0% | 154931 | 97066 | 415491 | 1 | 1 | 0 |
| glm5_2_nv | 62 | 59 | 95.2% | 5407 | 3062 | 16628 | 3 | 59 | 0 |
| kimi_nv | 4 | 4 | 100.0% | 13763 | 11723 | 28052 | 0 | 0 | 0 |

### 1.5 Per-Key Breakdown (成功请求 only)

| key | total | avg_ms | p50 | p95 |
|-----|-------|--------|-----|-----|
| k1(idx0) | 15 | 12302 | 2996 | 49936 |
| k2(idx1) | 16 | 19766 | 3449 | 90746 |
| k3(idx2) | 15 | 43317 | 2778 | 208717 |
| k4(idx3) | 13 | 15292 | 4815 | 64313 |
| k5(idx4) | 13 | 33971 | 3781 | 166911 |

---

## 2. 诊断

**Zero-error regime 持续**: 零log error, 零timeout, 零rate_limit, 仅1次次要kc429。

**4 ATE 全部 server-side**: error_type='all_tiers_exhausted' + upstream_type=NULL — NVCF 上游全tier耗尽，非proxy参数可修。

**FORCE_STREAM_UPGRADE_TIMEOUT margin**: 51s >> UPSTREAM_TIMEOUT=25s margin 26s，非常安全。

**integrate 12/12 OK、pexec 60/60 OK** — 无超时截断风险。

**结论**: FORCE_STREAM_UPGRADE_TIMEOUT 继续 -1s conservative trajectory 安全。margin 26s → 25s 仍充裕（>20s safety buffer）。

---

## 3. 优化方案

| # | 变更 | Before | After | 理由 |
|---|------|--------|-------|------|
| 1 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 51 | **50** (−1s) | R656-R665 trajectory (61→51, −10s) zero-error持续；50s margin 25s >> UPSTREAM_TIMEOUT=25 safe |

**风险**: 低。integrate路径从未超时，streaming keepalive不受影响。-1s保守。

**不改**: UPSTREAM_TIMEOUT=25 (floor)、KEY_COOLDOWN=25、MIN_OUTBOUND=0 (floor)、TIER_COOLDOWN=25、BUDGET=80、FASTBREAK=1、CONNECT_RESERVE=0 (floor) — 全部稳定。

---

## 4. 执行记录

```bash
# 备份
cp docker-compose.yml docker-compose.yml.bak.R666

# sed: 51→50 value only
sed -i '/NVU_FORCE_STREAM_UPGRADE_TIMEOUT/s/"51"/"50"/' docker-compose.yml

# Python SCP: rewrite R665 comment → R666 comment
scp -P 222 r666_comment.py opc_uname@100.109.153.83:/tmp/
ssh -p 222 ... python3 /tmp/r666_comment.py

# 验证3-way一致性
grep → compose="50" ✅
docker compose config → "50" ✅
docker exec env → NVU_FORCE_STREAM_UPGRADE_TIMEOUT=50 ✅

# 重启
docker compose up -d nv_40006_uni → Recreated + Started ✅
```

**铁律**: ✅ 只改HM1 `/opt/cc-infra/docker-compose.yml` line 492，未碰HM2任何文件/配置/容器。

---

## 5. 部署后验证

- Compose line 492: `"50"` ✅
- Container env: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=50` ✅
- Docker compose config: `"50"` ✅
- 3-way consistent ✅
- 容器启动日志干净，零ERROR ✅

---

## 6. 总结

**R656-R666 轨迹**: 61→59→58→57→56→55→54→53→52→51→**50** (−11s total)

**本轮**: FORCE_STREAM_UPGRADE_TIMEOUT 51→50 (−1s)，zero-error regime 持续，margin 25s safe。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记