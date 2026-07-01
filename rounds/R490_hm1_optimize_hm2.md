# R490 (HM1→HM2): ⏸️ NOP — CC清单[HM2-A/B/C]三项30min+6h新鲜数据全证伪 · 全参数天花板 · 6h SR=100%(713/713) · 5键p50 cv≈6%无劣化 · 30min 0×fail · 429级联新信号(30min 6×/6h 9×, 全direct同IP, 全cycle救回SR=100%) · A继续降被429证伪(2.5已为降下限) · 零配置变更 · 铁律:只改HM2不改HM1 · 锚定: ⏳ 轮到HM2优化HM1

**轮次**: R490
**方向**: HM1 优化 HM2 (本轮执行者=HM1, 对端=HM2, host_machine=opc2sname)
**日期**: 2026-07-01 09:51 UTC (CST 17:51; DB ts 09:51, 快真实UTC 8h)
**类型**: NOP (No Operation — 无参数变更, 数据驱动证伪)
**Commit**: 3e49c08 (R489, HM2→HM1, NOP) → 本commit (R490)

## 0. 时区与host标识 (R320教训#5)

- DB `ts` 比真实UTC快8h。实测: `SELECT max(ts), now()` → max ts=2026-07-01 09:48:16, now()=2026-07-01 01:48:35, 差8h ✓。所有窗口查询用绝对ts时间戳, 禁用 NOW()。
- 对端HM2 host_machine 标识=`opc2sname`。litellm_model=`nvcf_z-ai/glm-5.1_k1..k5`(5个key各自model名)。
- hm_tier_attempts 表无 host_machine 列, 用绝对ts窗口+`litellm_model LIKE '%glm%'`过滤。

## 1. 改前数据采集 (HM2 对端, host_machine=opc2sname)

### 1a. 容器env (8参数+5 URL, /opt/cc-infra/docker-compose.yml 与容器运行态双处一致)
```
UPSTREAM_TIMEOUT=48                (compose L469区)   容器env一致 ✓
TIER_TIMEOUT_BUDGET_S=100          (compose L470区)   容器env一致 ✓
MIN_OUTBOUND_INTERVAL_S=2.5        (compose L472区)   容器env一致 ✓
KEY_COOLDOWN_S=38                  (compose L473区)   容器env一致 ✓
TIER_COOLDOWN_S=22                 (compose L474区)   容器env一致 ✓
HM_SSLEOF_RETRY_DELAY_S=1.0        (compose L480区)   容器env一致 ✓
HM_PEXEC_TIMEOUT_FASTBREAK=5       (compose L482区)   容器env一致 ✓
HM_CONNECT_RESERVE_S=8             (compose L505区)   容器env一致 ✓
HM_NV_PROXY_URL1=""                (compose L489)   5键全direct ✓
HM_NV_PROXY_URL2=""                (compose L490)
HM_NV_PROXY_URL3=""                (compose L491)
HM_NV_PROXY_URL4=""                (compose L492)
HM_NV_PROXY_URL5=""                (compose L493)
```
compose grep与`docker exec hm40006 env`逐字一致 → **双处零漂移** ✓
/health=200 OK (port 40006): `{"status":"ok","proxy_role":"passthrough","hm_num_keys":5,"hm_model_tiers":["glm5.1_hm_nv"],"hm_default_model":"glm5.1_hm_nv"}`

### 1b. DB 30min窗口聚合 (改前基线, 窗口 DB ts 09:18:00-09:48:00 = 真实UTC 01:18-01:48)
| 指标 | 数值 |
|------|------|
| 总请求 | 118 |
| 成功 (200) | 118 (100.00%) |
| 失败 (502 ATE) | 0 |
| 429 (终态) | 0 |
| empty_200 | 0 |
| p50_ms | 8,063 |
| p95_ms | 45,208 |
| avg_ms | 12,623 |

### 1c. DB 6h窗口聚合 (DB ts 03:48:00-09:48:00 = 真实UTC 19:48-01:48)
| 指标 | 数值 |
|------|------|
| 总请求 | 713 |
| 成功 (200) | 713 (100.00%) |
| 失败 (502 ATE) | 0 |
| 429 (终态) | 0 |
| empty_200 | 0 |
| all_tiers_exhausted | 0 |
| p50_ms | 7,068 |
| p95_ms | 48,813 |
| avg_ms | 13,180 |

### 1d. Per-key 延迟 (30min, success only)
| Key | Reqs | p50(ms) | p95(ms) | max(ms) | avg(ms) |
|-----|------|---------|---------|---------|---------|
| k1 | 31 | 6,659 | 45,768 | 60,164 | 11,818 |
| k2 | 19 | 8,504 | 26,599 | 46,972 | 10,627 |
| k3 | 27 | 8,655 | 43,906 | 68,090 | 14,836 |
| k4 | 23 | 8,614 | 18,309 | 24,300 | 9,600 |
| k5 | 23 | 8,084 | 43,951 | 75,360 | 16,154 |

- 30min 5键p50 range 6,659-8,655ms (差距1.30×, cv≈10%)
- k1最多(31req, 26%), k2最少(19, 16%) — 轻微不均但RR正常范围

### 1e. Per-key 延迟 (6h, success only) — 验证无单key劣化
| Key | Reqs | p50(ms) | p95(ms) | avg(ms) |
|-----|------|---------|---------|---------|
| k1 | 152 | 6,577 | 47,890 | 11,650 |
| k2 | 140 | 7,470 | 47,244 | 13,587 |
| k3 | 142 | 7,513 | 51,738 | 14,337 |
| k4 | 144 | 7,324 | 48,630 | 12,786 |
| k5 | 135 | 6,845 | 45,100 | 13,817 |

**6h 5键均衡**: p50 range 6,577-7,513ms (差距1.14×, cv≈6%), 无单key劣化。
→ **[HM2-B]证伪**: 无劣化key, 5键全direct活跃。

### 1f. 6h小时桶趋势 (DB ts 03:00-09:00 = 真实UTC 19:00-01:00)
| Hour(DB ts) | Reqs | OK | SR% |
|-------------|------|----|-----|
| 03:00 | 39 | 39 | 100.0 |
| 04:00 | 114 | 114 | 100.0 |
| 05:00 | 125 | 125 | 100.0 |
| 06:00 | 132 | 132 | 100.0 |
| 07:00 | 73 | 73 | 100.0 |
| 08:00 | 94 | 94 | 100.0 |
| 09:00 | 136 | 136 | 100.0 |

- 7个小时桶全SR=100%, 零失败 — 系统极其稳定

### 1g. tier_attempts 错误结构 (30min / 6h)
**30min**:
| error_type | count | avg_ms | 备注 |
|------------|-------|--------|------|
| 429_nv_rate_limit | 6 | — | 中间attempt失败, 全cycle救回 |
| NVCFPexecTimeout | 4 | 48,536 | server-side, 全cycle救回 |

**6h**:
| error_type | count | avg_ms | 备注 |
|------------|-------|--------|------|
| NVCFPexecTimeout | 34 | 48,671 | server-side, 全cycle救回 |
| 429_nv_rate_limit | 9 | — | 中间attempt失败, 全cycle救回 |

- 所有error均为中间attempt失败, **终态0失败** (SR=100%)
- 0×empty_200, 0×SSLEOF, 0×conn_err — 连接健康

### 1h. 429级联细节 (新观察信号, 供CC下轮勘定)
docker logs 30min显示09:51:00-07.1的429级联:
```
[09:51:00.6] HM-KEY k2 → NVCF pexec
[09:51:01.2] HM-COOLDOWN k2 marked cooling after 429 → cycle
[09:51:01.2] HM-KEY k3 → NVCF pexec
[09:51:05.9] HM-COOLDOWN k3 marked cooling after 429 → cycle
[09:51:05.9] HM-KEY k4 → NVCF pexec
[09:51:06.5] HM-COOLDOWN k4 marked cooling after 429 → cycle
[09:51:06.5] HM-KEY k5 → NVCF pexec
[09:51:07.1] HM-COOLDOWN k5 marked cooling after 429 → cycle
[09:51:07.1] HM-KEY k1 → NVCF pexec (attempt 5/7)
```
- 6秒内k2/k3/k4/k5连续4个key全429 — 同IP短时密集限速级联
- 5键全direct(同IP), 无代理分流
- 30min tier_attempts 429 per-key: k5×3, k3×2, k2×2, k4×2 — 分散, 非单key问题
- 6h docker logs 429 cycle=15条 / 713req = 2.1%
- **影响评估**: 6h含429的请求仅6个(0.8%), avg 21s vs 无42913.2s(慢60%), 但p95相近(46.3s vs 48.9s), 且**全部最终成功**
- **结论**: 429是微小信号(2.1%, SR无影响), 当前不构成参数可修项

## 2. CC清单[HM2-A/B/C]状态评估 (30min+6h新鲜数据)

### [HM2-A] MIN_OUTBOUND 4.5→2.5 — ✅已达成 + 继续降被429证伪
- 当前=2.5 (R386达成, compose L472+容器env双处一致)
- **继续降证伪**: 30min出现6×429_nv_rate_limit(6h 9×), 429风险已realize
  - 429发生在direct同IP密集请求时(09:51级联:6秒内4 key全429)
  - 降throttle=增加同IP密集度=加剧429 → 与A方向相反, 不可降
- 30min 118req≈3.93 req/min, 远低于throttle天花板(60/2.5=24 req/min), 需求侧远未触达throttle
- 降throttle无吞吐增益(需求3.93req/min<<24天花板), 且加剧429
- **结论**: 2.5已为降的下限(继续降触发429), A目标值已达成, 继续降证伪

### [HM2-B] 失败模式数据补采 + 劣化key检测 — ✅已完成, 证伪
- 6h per-key: 5键p50 6,577-7,513ms (差距1.14×, cv≈6%), p95 45.1-51.7s
- 30min per-key: 5键p50 6,659-8,655ms (cv≈10%)
- 对照HM1-k4劣化(HM1 k4 p95=72.9s vs其他~55s): HM2无此模式
- 5键全direct (HM_NV_PROXY_URL1-5全空), 无单key IP限速迹象
- 6h 0终态失败, 所有error为中间attempt被cycle救回
- **结论**: 无劣化key, 无需路由修复, 证伪

### [HM2-C] TIER_TIMEOUT_BUDGET 128→100 — ✅已达成 + 无失败可修
- 当前=100 (compose L470+容器env一致), break at ~92s (BUDGET-CONNECT_RESERVE=100-8)
- 6h 0终态失败 → BUDGET未被break, 无失败请求可优化
- 6h成功 max_ms未触发budget break (p95=48.8s, 远低于92s break点)
- **结论**: BUDGET=100已达成, 6h无失败使其为非活跃约束, 继续降误杀证伪(无失败可省时)

## 3. 其他参数天花板验证

### UPSTREAM_TIMEOUT=48 — 不可降 (R478结论复检确认)
- 6h NVCFPexecTimeout avg 48,671ms — 单attempt read阶段~48.5s
- 6h p95_ok=48,813ms, 慢成功接近UPSTREAM边界
- 降UPSTREAM会让pexec在更早时间timeout, 减少单attempt成功机会
- **结论**: UPSTREAM=48保护慢成功, 不可降

### HM_PEXEC_TIMEOUT_FASTBREAK=5 — 死参数
- 6h 34次pexec timeout分散在多请求(每请求1-2次), 凑不够5连
- 每请求多在2-3次attempt内cycle救回, 永远到不了第5次FASTBREAK
- **结论**: 死参数, 降无增益

### KEY_COOLDOWN_S=38 / TIER_COOLDOWN_S=22 — 半活跃但无SR影响
- 6h 9×429触发cooldown, 但全cycle救回, 终态0失败
- cooldown 38s对429级联(6秒4 key)的恢复: 第一个429的key 38s后解cooling, 期间其他key轮转
- **结论**: cooldown配合得当, 无SR损失, 不动

## 4. 决策: ⏸️ NOP · 零配置变更

**理由**:
1. CC清单[HM2-A/B/C]三项全部完成: A(2.5)达成+继续降被429证伪(429已realize), B数据补采完成+6h 5键p50 cv≈6%无劣化证伪, C(100)达成+6h 0失败使BUDGET非活跃约束证伪
2. 全8参数在天花板: FASTBREAK/SSLEOF为死参数, KEY_COOLDOWN/TIER_COOLDOWN半活跃但无SR损失, MIN_OUTBOUND/UPSTREAM/BUDGET均已达不误杀下限
3. 系统极其稳定: 30min SR=100%(118/118), 6h SR=100%(713/713), 7小时桶全100%
4. 零终态失败, 零empty_200, 零SSLEOF, 零conn_err — 无连接级劣化
5. 429级联(2.1%, 全救回)是NVCF同IP短时限速, 非HM2参数可修(降throttle加剧, 收紧throttle与CC清单A方向相反且无SR收益)
6. UPSTREAM=48保护慢成功, BUDGET=100未被触发(无失败)

**当前HM2参数已达全局最优**: 6h SR=100%天花板, 所有throttle/cooldown在不误杀下限, 429被cycle机制完全吸收。

## 5. 429级联新观察 (供CC下轮勘定, 非本轮清单项)

本轮发现429级联信号, 但**不在CC清单HM2节内**, 本轮严格按清单执行不擅自改动:
- 现象: 30min 6×429(6h 9×), 5键全direct同IP, 6秒内4 key连续429级联
- 影响: 2.1%请求, 全cycle救回, SR=100%无影响, 含429请求avg慢60%但p95相近
- 潜在方向(供CC勘定, 非本轮执行): HM1侧k1/k3用mihomo代理分流IP, HM2侧5键全direct; 给HM2某1 key加mihomo代理可分流IP减少同IP429级联。但属清单外项, 且当前SR=100%无SR收益, 仅2.1%请求延迟优化, 优先级低。
- 反对者注意: 若下轮勘定此方向, 需先确认HM2 mihomo端口(7894-7899)启用状态, A/B对比429数+延迟。

## 6. 执行记录

### 变更: 无
```bash
# 零配置变更 — docker-compose.yml不变, 容器不重启
# 本轮为数据驱动NOP: CC清单三项30min+6h新鲜数据复检全部证伪, 无可动项
# 429级联为清单外新观察, 上报CC, 不擅自改动
```

### 验证: 通过
```bash
# env一致性检查: compose grep 与 docker exec hm40006 env 逐字一致, 无漂移
ssh -p 222 opc2_uname@100.109.57.26 'docker exec hm40006 env | grep -E "MIN_OUTBOUND|TIER_TIMEOUT|UPSTREAM|KEY_COOLDOWN|TIER_COOLDOWN|CONNECT_RESERVE|FASTBREAK|SSLEOF"'
# ↑ MIN_OUTBOUND=2.5, BUDGET=100, UPSTREAM=48, FASTBREAK=5, 全匹配compose

# 健康检查 (对端): /health=200 ok, hm_num_keys=5, 5键全direct
```

## 7. 轮次统计
- HM2自R485(上次HM1→HM2 NOP)后: R486/R487/R488/R489均为HM2→HM1方向, HM2侧参数未动
- CC清单[HM2-A/B/C]三项状态: A✅达成+继续降被429证伪, B✅完成+证伪, C✅达成+无失败证伪
- 连续NOP(HM2侧): R485→R490, 本轮为清单复检证伪轮(每项证伪有30min+6h具体数据)
- 本轮NOP理由: 三项全部完成/证伪, 全8参数在天花板, 6h SR=100%无失败可修

## 8. 铁律遵守
- ✅ 只改HM2不改HM1: 无变更行为, 合规
- ✅ 单参数少改多轮: NOP验证, 无参数
- ✅ 数据驱动先采集后决策: 6层验证(env + 30min + 6h DB + per-key + 小时桶 + docker logs)
- ✅ 零配置变更: docker-compose.yml未修改, compose与容器env双处零漂移
- ✅ 无R320/R322/R350重蹈: 未改compose, 未commit错文件, push后即停
- ✅ DB时区: 全部用绝对ts窗口, 禁用NOW()
- ✅ 执行CC清单不擅自找改动点: 429级联为清单外项, 上报CC不擅改

## ⏳ 轮到HM2优化HM1
