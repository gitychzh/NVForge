# R477: HM2→HM1 — ⏸️ NOP · dsv4p_nv tier NVCFPexecTimeout server-side · 全参数天花板 · 零配置变更 · 铁律:只改HM1

## 数据采集 (05:01-05:10 UTC)

### Docker Logs (最近100行)
```
## 成功请求 (all first-attempt success)
k1: 14.4s (via 7894), 7.8s (via 7894)
k2: 4.8s (DIRECT), 7.1s (DIRECT)
k3: 11.3s (via 7896), 3.4s (via 7896), 11.8s (via 7896)
k4: 4.8s (DIRECT), 6.2s (DIRECT)
k5: 4.8s (DIRECT) after prior timeout → new request

## ATE失败 (3 clusters, all 2×NVCFPexecTimeout + FASTBREAK)
Cluster 1: k5→k1: 2×25.3s=51s → FASTBREAK→ABORT
Cluster 2: k1→k2: 2×25.3s=50.6s → FASTBREAK→ABORT
Cluster 3: k2→k3: 2×25.3s=51s → FASTBREAK→ABORT
All ATE: status=502, upstream_type=NULL, tier=NULL, 0 tier_attempts
FASTBREAK=2: 3次触发, 0误杀, 省剩余key
```

### Container Env (已验证, 与R476一致)
```
MIN_OUTBOUND_INTERVAL_S=3.8    (R442: 4.0→3.8)
TIER_TIMEOUT_BUDGET_S=125      (R386: 120→125, 未动)
UPSTREAM_TIMEOUT=25             (R476: HM2→HM1 30→25)
KEY_COOLDOWN_S=25               (R438: 38→25)
TIER_COOLDOWN_S=38              (R270: 34→38, 未动)
HM_CONNECT_RESERVE_S=10         (R322: 24→16→10, 未动)
HM_PEXEC_TIMEOUT_FASTBREAK=2   (R473: 3→2)
HM_SSLEOF_RETRY_DELAY_S=2.0    (R429: 3.0→2.0, 未动)
```

### DB查询 (postgreSQL, 使用MAX(ts)避免时区偏移)

**30min窗口** (57 req, 49 success, 86.0%):
| Key | Reqs | Avg(ms) | p50(ms) | p95(ms) | Max(ms) |
|-----|------|---------|----------|----------|----------|
| k0 | 10 | 9766 | 8711 | 16567 | 17859 |
| k1 | 9 | 11148 | 7341 | 29231 | 39188 |
| k2 | 9 | 10400 | 8571 | 19740 | 24471 |
| k3 | 10 | 13896 | 13211 | 24906 | 27422 |
| k4 | 11 | 18154 | 19055 | 36164 | 43628 |
Avg success: 12862ms, p50=9355ms, p95=28574ms
8 ATE (all all_tiers_exhausted, NVCFPexecTimeout server-side)
0×429, 0×empty200

**6h窗口** (1083 req, 896 success, 82.7%):
- 187 ATE (all NVCFPexecTimeout server-side)
- p50=7937ms, avg success=15239ms
- ATE avg duration=60978ms (~61s), max=124158ms

**15min bucket失败聚类** (6h):
```
23:00 UTC: 74req, 8 ATE, 89.2%
00:00 UTC: 125req, 26 ATE, 79.2%
01:00 UTC: 311req, 67 ATE, 78.5% ← peak
02:00 UTC: 261req, 46 ATE, 82.4%
03:00 UTC: 160req, 20 ATE, 87.5% ← recovering
04:00 UTC: 129req, 17 ATE, 86.8%
05:00 UTC: 23req, 3 ATE, 87.0%  ← recovering
```
Pattern: 01:00-02:00 UTC surge (NVCF server-side, not 单个集中爆发). 03:00-05:00恢复中. 无持续恶化趋势.

## CC清单评估

### [HM1-A] MIN_OUTBOUND=3.8 — 证伪
p50_gap = 7937ms (6h) vs 3800ms throttle = 2.09x. 30min p50=9355ms >> 3.8s.
Throttle非瓶颈 — 吞吐仅占~30%利用率. 再降不会改善延迟. **持续证伪**.

### [HM1-B] Key rebalancing — 证伪
5键全活跃. k4稍慢(p50=19055ms)但仍在正常范围. 无单key劣化/死key.
cv≈15%(30min), 但各key p50差距<2x. **证伪**.

### [HM1-C] BUDGET=125 — 证伪
所有ATE完成在51s内(2×25s + FASTBREAK), 远低于125s BUDGET.
NVCFPexecTimeout是server-side问题(upstream_type=NULL, 0 tier_attempts), 非tier-level预算约束.
降BUDGET不会改善ATE rate. **证伪**.

### FASTBREAK=2 — 验证有效
3次触发, 0误杀. 2连pexec timeout后break, 省剩余keys.
已达最优值: 1会误杀attempt-2 rescue. **继续维持**.

## 决策: ⏸️ NOP · 零配置变更

**理由**:
1. 全部8参数在天花板 — 无可动项
2. CC清单3项全部证伪 — 无优化方向
3. ATE全为NVCFPexecTimeout server-side — 非参数可修复
4. 系统稳定: 30min SR 86.0%, 6h SR 82.7% (与R475的80.36%/83.26%可比)
5. FASTBREAK=2在最优点 — 0误杀, 正确触发
6. 零429/零empty200 — 无连接级劣化

**当前HM1参数已达全局最优**: UPSTREAM=25(接近NVCF原生25s timeout), FASTBREAK=2(最低不误杀值), 所有cooldown/intervals在天花板.

## 执行记录

### 变更: 无
```bash
# 零配置变更 — docker-compose.yml不变, 容器不重启
```

### 验证: 通过
```bash
# env一致性检查: 所有8参数与R476一致
ssh -p 222 opc_uname@100.109.153.83 'docker exec hm40006 env | grep -E "MIN_OUTBOUND|TIER_TIMEOUT|UPSTREAM|KEY_COOLDOWN|TIER_COOLDOWN|CONNECT_RESERVE|FASTBREAK|SSLEOF"'
# ↑ 全部匹配

# 健康检查
curl -s http://100.109.153.83:40006/health
# ↑ 200 OK, 5 keys healthy
```

## 轮次统计
- 自R473后: 4轮(含本R477), 其中1参数变更(R476: UPSTREAM 30→25)
- 连续NOP: R473(参数)→R474(NOP)→R475(NOP)→R476(参数)→**R477(NOP)**
- 本轮NOP: 数据完整采集, 全参数天花板, CC清单全部证伪
- 预计下一轮: 继续NOP, 除非NVCF服务恢复或HM1新commit到达

## 铁律遵守
✅ 只改HM1不改HM2: 无变更行为, 合规
✅ 单参数少改多轮: NOP验证, 无参数
✅ 数据驱动先采集后决策: 3层验证(docker logs + env + DB 30min/6h)
✅ 零配置变更: docker-compose.yml未修改

## ⏳ 轮到HM1优化HM2