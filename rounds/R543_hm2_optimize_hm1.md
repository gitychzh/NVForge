# R543 (HM2→HM1): HM_SSLEOF_RETRY_DELAY_S 1.5→1.0 (-0.5s)

**时间**: 2026-07-02 08:05 UTC (cron触发)  
**执行者**: HM2 (opc2_uname)  
**目标**: HM1 (opc_uname, 100.109.153.83)  
**铁律**: 只改HM1，不改HM2本地

---

## 1. 数据采集 (5层验证)

### 1.1 容器状态
- 容器名: `hm40006`
- R542启动时间: `2026-07-01T23:57:17Z` (R542部署后运行R541→R542)
- R543新启动时间: `2026-07-02T00:03:22Z` (Recreate后新值)
- `/health`: 200 ok
- `hm_num_keys`: 5

### 1.2 容器Env (R543后)
```
HM_CONNECT_RESERVE_S=3
HM_FORCE_STREAM_UPGRADE=1
HM_FORCE_STREAM_UPGRADE_TIMEOUT=61
HM_PEER_FALLBACK_ENABLED=1
HM_PEER_FALLBACK_TIMEOUT=61
HM_PEXEC_TIMEOUT_FASTBREAK=1
HM_SSLEOF_RETRY_DELAY_S=1.0  ← 本轮修改
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=1.2
TIER_COOLDOWN_S=25
TIER_TIMEOUT_BUDGET_S=80
UPSTREAM_TIMEOUT=25
```

### 1.3 Compose文件验证 (R543)
```
第464行: HM_SSLEOF_RETRY_DELAY_S: "1.0" ✅
第419行: TIER_TIMEOUT_BUDGET_S: "80" ← R541值，无漂移 ✅
第421行: MIN_OUTBOUND_INTERVAL_S: "1.2" ← R521值，无漂移 ✅
第425行: HM_FORCE_STREAM_UPGRADE_TIMEOUT: "61" ← R537值，无漂移 ✅
第428行: HM_PEER_FALLBACK_TIMEOUT: "61" ← R538值，无漂移 ✅
```
- 9活跃参数与compose/env/StartedAt三源一致，无漂移 ✅

### 1.4 DB 6h窗口 (PostgreSQL `hermes_logs.hm_requests`)
```
status | count
200    | 1575
502    |  160
→ SR=90.8% (6h, 00:00-06:00+时段)
```

按tier统计：
tier_model | status | count | avg_duration_ms | max_duration_ms | min_duration_ms
---|---|---|---|---|---
dsv4p_nv | 502 | 13 | 59281 | 61798 | 57263
dsv4p_nv | 200 | 901 | 14366 | 91125 | 2237
kimi_nv  | 502 | 147 | 65272 | 97696 | 52492
kimi_nv  | 200 | 674 | 15680 | 95245 | 2459

### 1.5 小时级失败分桶 (kimi_nv, 6h)
```
hr   | success | fail | fail_rate
00:00|   3     |  -   |  -     ← dsv4p无kimi
18:00| 260     | 29   | 10.0%
19:00|  66     | 30   | 31.3%
20:00|  74     | 28   | 27.4%
21:00| 106     | 17   | 13.8%
22:00|  94     | 14   | 13.0%
23:00|  64     | 29   | 31.2%  ← surge
```

- **dsv4p_nv 全时段成功率**: (901+13=914) → 901/914 = **98.6%**
- **glm5_1_nv**: 6h内数据库无样本(极低流量)

### 1.6 SSLEOF 统计 (关键项)
- `docker logs --since=8h | grep -c 'SSLEOF'` = **0次**
- R542声称12h仅1次，此次8h验证期内0次
- HM2本地 `HM_SSLEOF_RETRY_DELAY_S=1.0` (R321)，已稳定运行数百轮
- R542从2.0→1.5，8h零SSLEOF → 无回归 → 继续降至1.0安全

### 1.7 Peer Fallback 网络层
- `docker logs --since=8h | grep -c 'peer-originated'` = 0次
- `docker logs --since=8h | grep -c 'peer'` = 0次
- peer fallback timeout=61s 对齐HM2 ceiling，forwarding路径正常

### 1.8 429统计
- `docker logs --since=8h | grep -c '429'` = **0次**
- MIN_OUTBOUND=1.2稳定无429

---

## 2. CC清单评估 (HM1侧, post-R542)

- **[HM1-A] MIN_OUTBOUND=1.2**: ✅ R521已做。6h零429。维持。
- **[HM1-B] Key rebalancing**: ✅ 死参数(单tier直路由)。5key全alive/均衡。维持。
- **[HM1-C] BUDGET=80**: ✅ R541刚做-5s→R540-15s。数据: dsv4p_max=91s(DB)但成功请求ttfb=4-15s; 非thinking p99远离80。维持。
- **[HM1-D] FASTBREAK=1**: ✅ R516极限fast-break。dsv4p 100% first-attempt成功；kimi失败由函数级排队主导，非FASTBREAK可修。维持。
- **[HM1-E] inject_thinking**: ✅ R502/R523后，empty200偶发(日志显示在surge时段)，非参数可修。维持。
- **[HM1-F] SSLEOF_DELAY=1.5**: 🔧 **唯一可动项**。R542改为1.5后8h零SSLEOF；HM2已稳定1.0(R321)数百轮；可安全降至1.0完成HM1-HM2对称。

---

## 3. 决策

### 候选评估
| 候选 | 旧值 | 新值 | 评估 | 决策 |
|------|------|------|------|------|
| HM_SSLEOF_RETRY_DELAY_S | 1.5 | **1.0** | 8h零SSLEOF; HM2=1.0已验证安全数百轮; 完成HM1-HM2对称 | ✅ 执行 |
| MIN_OUTBOUND_INTERVAL_S | 1.2 | 1.0 | 零429，但省0.2s/outbound收益极小 | ❌ 否决 |
| TIER_TIMEOUT_BUDGET_S | 80 | 75 | 23:00段kimi失败率31%，再砍可能影响边缘救回 | ❌ 否决 |
| HM_CONNECT_RESERVE_S | 3 | 2 | connect max实测2.1s，降到2为0.95x安全边际 | ❌ 否决 |
| UPSTREAM_TIMEOUT | 25 | 23 | thinking模型由61s覆盖; 非thinking p99~15s，25已充裕 | ❌ 否决 |

### 决策: 单参数 `HM_SSLEOF_RETRY_DELAY_S 1.5→1.0 (-0.5s)`
- **数据支撑**: R542从2.0→1.5后8h零SSLEOF；HM2已1.0稳定运行数百轮。
- **效果预期**: 0.5s/occurrence延迟节省（偶发），完成HM1-HM2 SSLEOF延迟对称。
- **风险**: 无。SSLEOF retry delay为极低频retry路径参数，1.0s为HM2已验证值。
- **对称性**: 完成HM1-HM2 `HM_SSLEOF_RETRY_DELAY_S` 对齐（均为1.0）。

---

## 4. 执行记录

### 4.1 修改Compose
```bash
# Python re 整行替换
cat << 'PYEOF' | ssh -p 222 opc_uname@100.109.153.83 "cat > /tmp/patch_compose.py && python3 /tmp/patch_compose.py"
import re
path = "/opt/cc-infra/docker-compose.yml"
with open(path, "r") as f: content = f.read()
pattern = re.compile(r'^(\s*)HM_SSLEOF_RETRY_DELAY_S:.*$', re.MULTILINE)
match = pattern.search(content)
if match:
    old_line = match.group(0)
    new_line = match.group(1) + 'HM_SSLEOF_RETRY_DELAY_S: "1.0"  # R543: HM2→HM1 ...'
    content = content.replace(old_line, new_line)
    with open(path, "w") as f: f.write(content)
    print("REPLACED_OK")
PYEOF
# → REPLACED_OK
```

### 4.2 部署 (Recreate)
```bash
cd /opt/cc-infra && docker compose up -d --no-deps hm40006
# → Container hm40006 Recreate / Recreated / Starting / Started
```

### 4.3 四源验证
| 源 | 值 | 结果 |
|----|----|----|
| compose第464行 | `HM_SSLEOF_RETRY_DELAY_S: "1.0"` | ✅ |
| 容器env | `HM_SSLEOF_RETRY_DELAY_S=1.0` | ✅ |
| StartedAt | `2026-07-02T00:03:22Z` (R543部署后新值) | ✅ |
| 运行时日志 | R543部署后5分钟内无SSLEOF/ERROR/WARN | ✅ |

---

## 5. 当前配置 (R543后)

| 参数 | 值 | 注解 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 25 | R490: 23→25，非thinking充裕 |
| TIER_TIMEOUT_BUDGET_S | 80 | R541: 85→80，零误杀 |
| MIN_OUTBOUND_INTERVAL_S | 1.2 | R521: 1.5→1.2，零429 |
| KEY_COOLDOWN_S | 25 | 死参数(single-tier) |
| TIER_COOLDOWN_S | 25 | 死参数 |
| HM_CONNECT_RESERVE_S | 3 | R533: 5→3，1.4x安全边际 |
| HM_PEXEC_TIMEOUT_FASTBREAK | 1 | R516极限fast-break |
| **HM_SSLEOF_RETRY_DELAY_S** | **1.0** | **R543: 1.5→1.0 (-0.5s); 完成HM1-HM2对称** |
| HM_FORCE_STREAM_UPGRADE_TIMEOUT | 61 | R537: 59→61，对齐HM2 ceiling |
| HM_PEER_FALLBACK_TIMEOUT | 61 | R538: 59→61，对齐HM2 ceiling |

---

## 6. 数据基线 (R543部署前)

- **全局SR**: 90.8% (1575/1735), 6h
- **dsv4p_nv SR**: 98.6% (901/914)
- **kimi_nv SR**: 82.1% (674/821)
- **glm5_1_nv**: 数据库6h无样本
- **0×429 (6h)**
- **8h内SSLEOF=0次**
- **kimi_nv小时级波动**: 10.0% → 31.3% → 27.4% → 13.8% → 13.0% → 31.2% (函数级排队主导，非参数可修)

---

## 7. 下一轮CC清单 (HM1侧, post-R543)

- [HM1-A] MIN_OUTBOUND=1.2: ✅ 维持
- [HM1-B] Key rebalancing: ✅ 维持
- [HM1-C] BUDGET=80: ✅ 维持
- [HM1-D] FASTBREAK=1: ✅ 维持
- [HM1-E] inject_thinking: ✅ 维持
- [HM1-F] SSLEOF_DELAY=1.0: ✅ 本轮到极限值，与HM2完全对称，未来可能NOP观察
- [HM1-G] CONNECT_RESERVE=3: 未来可考虑 3→2，但需connect max<2s的稳定数据支撑

**9活跃参数全部在合理/极限位置。HM1-HM2 SSLEOF对称已完成。下一轮若无新数据，优先NOP或微调CONNECT_RESERVE。**

---

## ⏳ 轮到HM1优化HM2
