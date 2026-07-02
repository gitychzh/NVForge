# R576: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 76→90 (+14s regime回调)

> 角色: HM2(opc2) → 优化目标: HM1(opc) / 链路: nv_40006_uni
> 铁律: 只改HM1配置, 绝不改HM2本地任何文件

## 1. 数据来源与采集命令

### 1.1 容器日志 (最近100行)
```
ssh opc_uname@100.109.153.83 -p 222
# docker logs nv_40006_uni --tail 100 2>&1
# 主要为proxy启动日志, 最近无error/warn级日志
```

### 1.2 容器环境变量 (完整状态)
```bash
docker exec nv_40006_uni env | grep -E 'UPSTREAM|TIER_TIMEOUT|MIN_OUTBOUND|KEY_COOLDOWN|TIER_COOLDOWN|FASTBREAK|CONNECT_RESERVE|SSLEOF|STREAM_UPGRADE|EMPTY_200|INTEGRATE|PEER_FALLBACK' | sort
```

采集结果:
```
NVU_CONNECT_RESERVE_S=2
NVU_EMPTY_200_FASTBREAK=0
NVU_FORCE_STREAM_UPGRADE=1
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_PEER_FALLBACK_ENABLED=1
NVU_PEER_FALLBACK_TIMEOUT=25
NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006
NVU_SSLEOF_RETRY_DELAY_S=1.0
NV_INTEGRATE_MODELS=dsv4p_nv,kimi_nv
TIER_TIMEOUT_BUDGET_S=90   ← 本轮修改后
TIER_COOLDOWN_S=25
```

### 1.3 DB 请求延迟与成功率 (1h 与 6h 窗口)

**1小时数据** (PostgreSQL nv_requests 表):
```sql
SELECT tier_model, status, count(*), avg(duration_ms)::int
FROM nv_requests WHERE ts > NOW() - interval '1 hour' AND tier_model IS NOT NULL
GROUP BY tier_model, status ORDER BY tier_model, status;
```
结果:
| tier_model | status | count | avg_ms |
|------------|--------|-------|--------|
| dsv4p_nv   | 200    | 509   | 26,364 |
| dsv4p_nv   | 502    | 60    | 66,236 |
| glm5_1_nv  | 200    | 13    | 4,670  |
| glm5_1_nv  | 502    | 1     | 67,868 |
| kimi_nv    | 200    | 93    | 29,759 |
| kimi_nv    | 502    | 117   | 77,337 |

成功率 (1h): dsv4p_nv 89.5%, kimi_nv 44.3%

成功 max 与百分位:
- dsv4p_nv: max=91,878ms; p50=23,353ms; p90=45,699ms; p95=53,259ms; p99=75,214ms
- kimi_nv: max=89,020ms; p50=29,612ms; p90=57,332ms; p95=61,291ms; p99=81,077ms

**6小时数据**:
| tier_model | status_200 | status_502 | total | SR%    | avg_succ_ms | max_succ_ms |
|------------|------------|------------|-------|--------|-------------|-------------|
| dsv4p_nv   | 509        | 75         | 584   | 87.1%  | 26,364      | 91,878      |
| glm5_1_nv  | 13         | 1          | 14    | 92.9%  | 4,670       | 8,485       |
| kimi_nv    | 364        | 240        | 604   | 60.3%  | 20,173      | 89,020      |

ATE 6h 总计: 313 次 (几乎是全部 502 的原因)
失败原因细分: 几乎 100% 为 `all_tiers_exhausted` / `all_tiers_failed_in_mapped_tier`

### 1.4 小时级 trend (kimi_nv 波动显著)
```
11:00  82.9% | 12:00  40.9% | 13:00  72.2% | 14:00  33.3% | 15:00  41.2%
16:00  28.0% | 17:00  18.2% | 18:00  16.7% | 19:00  61.3% | 20:00  50.0%
21:00  45.5% | 22:00  95.5% | 23:00  36.4% | 00:00  16.0% | 01:00 100.0%
```
典型的 function-level surge isolation: SR 从 16% 到 95% 剧烈波动, 非参数可修。

### 1.5 NV proxy 日志关键发现
- `nv_error_detail`: kimi_nv ATE 模式固定为 `empty_200` (第1个 key) → `NVCFPexecTimeout` (第2个 key), elapsed 78-84s
- `nv_proxy.log`: kimi_nv integrate 路径出现 **7 个 keys 全部 empty_200** 后失败, dsv4p_nv integrate 首击成功率高
- 说明 kimi 的 empty_200 是 **模型/函数级间歇性问题** (integrate 与 pexec 均受影响), 非网关参数可修

### 1.6 HM1 参数现状态 (docker-compose.yml, 逐行对应)
```
UPSTREAM_TIMEOUT: "25"                    (R490)
TIER_TIMEOUT_BUDGET_S: "90"              (R576 本次)
MIN_OUTBOUND_INTERVAL_S: "0.5"            (R570)
KEY_COOLDOWN_S: "25"                      (R162)
TIER_COOLDOWN_S: "25"                     (R492)
NVU_FORCE_STREAM_UPGRADE: "1"             (R502)
NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "61"    (R537)
NVU_CONNECT_RESERVE_S: "2"                (R570)
NVU_SSLEOF_RETRY_DELAY_S: "1.0"           (R543)
NVU_PEXEC_TIMEOUT_FASTBREAK: "1"          (R559)
NVU_EMPTY_200_FASTBREAK: "0"              (R567)
NVU_PEER_FALLBACK_ENABLED: "1"            (R560)
NVU_PEER_FALLBACK_TIMEOUT: "25"            (R560)
```

## 2. 候选参数评估 (按优先级排序)

| 参数 | 现值 | 评估 | 本轮决策 |
|------|------|------|----------|
| TIER_TIMEOUT_BUDGET_S | **76** | **binding**: 6h 成功 max=91.9s(ds) / 89.0s(kimi) 远超 76; R573 提交时 max=41.7s, 现已 **regime 变化**; p95=53/61s 下 90 有 29-37s 余量; kimi ATE avg=77.5s 已逼近 76 边缘, BUDGET 对 multi-tier 救回窗口存在截断风险 | **76→90 (+14s)** |
| UPSTREAM_TIMEOUT | 25 | 第二 key timeout elapsed 仅 13-23s < 25, 不 binding | 不改 |
| MIN_OUTBOUND_INTERVAL_S | 0.5 | 已是地板价; KEY_COOLDOWN=25 >> 0.5 零 429 风险 | 不改 |
| NVU_CONNECT_RESERVE_S | 2 | 已是地板价; connect 实测 0.6-2.1s | 不改 |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 近期 0 次 SSLEOF | 不改 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 当前 ATE 模式 2 次 attempts (empty200+timeout), fastbreak 未触发; empty200→fastbreak=0 保持更多 key 轮转机会 (R567 已验证) | 不改 |
| NVU_PEER_FALLBACK_TIMEOUT | 25 | 近期 0 次 peer fallback 记录 | 不改 |
| NV_INTEGRATE_MODELS | dsv4p_nv,kimi_nv | R575 新增 kimi; dsv4p integrate 表现好(首击成功), kimi integrate 也出现 empty200, 但保留覆盖无额外成本 | 不改 |

## 3. 本轮改动与推理

### 改动: `TIER_TIMEOUT_BUDGET_S 76 → 90` (+14s)

- **数据支撑**: R573 提交时 1h 成功 max=41.7s, 当前 6h max=91.9s, 增长 50.2s → 明确 **regime 变化**
- BUDGET=76 对当前成功分布余量严重不足 (-15.9s 相对 max; kimi ATE avg 77.5s 已超 76)
- 回调至 90 提供 p95 层级 29-37s 安全余量
- 单参数改动, 符合 "少改多轮" 铁律
- **已知代价**: 边际 ATE 等待时间增加 ~14s; 但 multi-tier 救回窗口恢复

**铁律查核**: compose 层面改, 不改 hm2 本地, 改完 HM1 立即验证 env 一致性 → `TIER_TIMEOUT_BUDGET_S=90` 已确认。

### git diff (应用于 HM1 docker-compose.yml)
```diff
--- a/opt/cc-infra/docker-compose.yml
+#      TIER_TIMEOUT_BUDGET_S: "76" # R573: HM2→HM1 — BUDGET 80→76 (-4s) ...
+      TIER_TIMEOUT_BUDGET_S: "90" # R576: HM2→HM1 — BUDGET 76→90 (+14s). 6h数据dsv4p_max=91.9s,kimi_max=89.0s远超76,regime变化确认; p95=53s(ds)61s(kimi)90s余量29-37s充足; ATE路径avg 67-77s逼近76边缘; 回调恢复multi-tier救回窗口; 单参数少改多轮; 铁律:只改HM1不改HM2
```

## 4. 评判维度

| 维度 | 本轮影响 | 备注 |
|------|----------|------|
| 更少报错 | 边际改善 | 恢复 multi-tier 救回窗口, 救回少量因 BUDGET 截断的边缘请求 |
| 更快请求 | -14s/ATE (等待增加) | 代价: ATE 路径等待延长 ~14s; 成功路径不受影响 |
| 超低延迟 | 无影响 | p50=23s(ds) / 30s(kimi) 未触及 |
| 稳定性优先 | ↑ | regime 回调防止边缘请求被误杀, 减少 BUDGET 相关的不确定性 |

> 注: kimi_nv 成功率 60.3% 的 main root cause 为 function-level empty200 surge (integrate 与 pexec 均受影响), 非网关参数可修。建议等待 NVCF 上游恢复或观察后续轮次数据。

## ⏳ 轮到HM1优化HM2
