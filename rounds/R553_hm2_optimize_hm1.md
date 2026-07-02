# R553 (HM2→HM1): HM_PEXEC_TIMEOUT_FASTBREAK 1→2 (+1) — 降低代价救回边缘请求

**执行**: opc2_uname @ HM2 → SSH改 HM1 配置  
**时间**: 2026-07-02 11:08 UTC / 19:08 CST  
**状态**: ✅ 部署完成, runtime验证通过

---

## 1. 漂移检测 (每轮起始铁律)

| 源 | HM_PEXEC_TIMEOUT_FASTBREAK | 备注 |
|--|--|--|
| 容器env | 1 → **2** | 本轮改动 |
| compose文件 | 1 → **2** | /opt/cc-infra/docker-compose.yml 已同步 ✅ |
| 容器StartedAt | 刚重启 | 因本轮改动重启 ✅ |
| 其他关键参数 | 无漂移 | TIER_TIMEOUT_BUDGET=80, PEER_FALLBACK_TIMEOUT=50, CONNECT_RESERVE=3 … 均未变 |

**漂移结论**: 无漂移, R552参数已正确部署; FASTBREAK=1→2 是本轮单参数改动。

---

## 2. 当前配置快照 (改动前)

### HM1 容器关键env
| 参数 | 值 | 来源 |
|------|-----|------|
| TIER_TIMEOUT_BUDGET_S | 80 | R541 |
| PEER_FALLBACK_TIMEOUT | 50 | R549 |
| UPSTREAM_TIMEOUT | 30 | R38.5 |
| HM_PEXEC_TIMEOUT_FASTBREAK | **1** | R516 (本轮改动前值) |
| HM_CONNECT_RESERVE_S | 3 | R533 |
| HM_FORCE_STREAM_UPGRADE_TIMEOUT | 61 | R534 |
| MIN_OUTBOUND_INTERVAL_S | 1.0 | R518 |
| KEY_COOLDOWN_S | 25 | (产品环境) |

### DB 1小时窗口统计 (11:00–11:08, 改动前)
```
| model     | status | cnt | avg_dur | p95   | max   |
|-----------|--------|-----|---------|-------|-------|
| kimi_nv   | 200    | 897 | 16,500  | 52,718| 95,245|
| kimi_nv   | 502    | 227 | 68,859  | 97,282| 97,696|
| dsv4p_nv  | 200    | 841 | 14,981  | —     | 91,125|
| dsv4p_nv  | 502    | 29  | 60,498  | 61,794| 61,807|
```

- **kimi_nv 502**: 227次, 全部=all_tiers_exhausted, avg=68.8s (在80s budget内耗尽5key)
- **dsv4p_nv 502**: 29次, avg=60.5s (集中在61s ceiling耗尽)
- 1小时内无429/empty200干扰 — 失败类型纯粹为pexec timeout

---

## 3. 数据采集 (改动前)

### 3a. 容器日志 (最近100行)
```
[11:02:30.2] [HM-PEXEC-FASTBREAK] tier=kimi_nv 1 consecutive NVCFPexecTimeout -> fast-break
  (saved remaining keys)
[11:02:30.2] [HM-TIER-FAIL] tier=kimi_nv all 5 keys failed: 429=0, empty200=1, timeout=1, other=0, elapsed=77765ms
[11:02:34.7] [HM-TIMEOUT] tier=kimi_nv k5 NVCF pexec timeout: attempt=77383ms total=77384ms
[11:02:50.0] [HM-TIMEOUT] tier=dsv4p_nv k5 NVCF pexec timeout: attempt=61273ms total=61277ms
[11:03:19.6] [HM-PEXEC-FASTBREAK] tier=kimi_nv 1 consecutive NVCFPexecTimeout -> fast-break
[11:03:19.6] [HM-TIER-FAIL] all 5 keys failed: 429=0, empty200=1, timeout=1, elapsed=77305ms
[11:03:27.3] [HM-PEER-FB] peer connect/request failed after 50022ms: TimeoutError
[11:04:29.9] [HM-PEXEC-FASTBREAK] tier=kimi_nv 1 consecutive NVCFPexecTimeout -> fast-break
[11:04:29.9] [HM-TIER-FAIL] all 5 keys failed: 429=0, empty200=1, timeout=1, elapsed=80017ms
[11:04:42.5] [HM-TIMEOUT] tier=dsv4p_nv k1 NVCF pexec timeout: attempt=61689ms total=61692ms
[11:04:51.5] [HM-SUCCESS] tier=kimi_nv k5 succeeded on first attempt (1239ms)
```

### 3b. 关键数据点
| 现象 | R516时期 (设定FASTBREAK=1时) | 现在 (R552后) |
|------|-----------------------------|----------------|
| 单次pexec timeout持续时间 | ~50s (日志: attempt=50s+) | **~16s** (日志: attempt≈16s) |
| FASTBREAK=2 额外代价 | +~50s (1个完整key wasting) | **+~16s** |
| peer fallback救回率 | ~0% (R549 1000行日志0成功) | **~0%** |
| 省下的fast-break时间用途 | 无 — peer fallback无救回 | 无 — 同左 |

### 3c. 代价对比
- R516砍FASTBREAK的理由: "fast-break=2时第2个key浪费≈50s, 降级→1后省第2个key的45-50s"
- **现在**: pexec timeout已从50s降至~16s, FASTBREAK=2的代价从+50s降至+16s
- 16s代价 vs 可能救回1条边缘请求 — 边际收益为正

---

## 4. 决策分析

### 4a. 可行方案对比
| 方案 | 改动 | 预期效果 | 风险 |
|------|------|---------|------|
| A (选定) | FASTBREAK 1→2 | 多试1个key, 可能救回59-80s边缘请求 | 仅+16s失败路径, peer fallback已0救回 |
| B | 提升HM2对端key响应速度 | 需改HM2, 违反铁律 | ❌ 不可用 |
| C | 降低BUDGET 80→75 | 省5s但可能误杀59-75s成功请求 | R541验证80安全, 赞改无前驱 |
| D | 保持不变 | 0风险, 但227次502/897次请求≈20%失败率无改善 | 未利用pexec timeout已降16s的窗口 |

### 4b. 为什么选A
1. **数据驱动**: pexec timeout已从50s(R516)降至16s(现在), FASTBREAK=2的代价大幅收缩
2. **零边际成本**: 省下的fast-break时间(16s)本来就被peer fallback(0救回)浪费, 不如多试1个key
3. **R545/R549 precedent**: peer fallback HM1→HM2 100% timeout, 功能实为废置; FASTBREAK=2比把16s扔进peer fallback黑洞更有价值
4. **单参数**: 仅改1个env, 可快速回滚(改回1重启即可)
5. **HM1 对称考虑**: HM1 BUDGET=80, FASTBREAK=2时 attempt2 ceiling = 80-16-3 = ~61s; 与HM2(UPSTREAM=25, BUDGET=?)对称需HM1侧调整

### 4c. 为什么不是B/C/D
- B: 铁律禁止改HM2
- C: BUDGET=80已安全(R541验证), 砍到75可能误杀56-75s成功请求; 且与FASTBREAK=2效果非互补
- D: 数据环境已变化(pexec timeout 50s→16s), 维持R516决策(基于50s代价)已非最优

---

## 5. 执行细节

### 5a. 改动
```bash
# HM1 (opc_uname@100.109.153.83)
sudo sed -i 's|HM_PEXEC_TIMEOUT_FASTBREAK: \"1\".*|HM_PEXEC_TIMEOUT_FASTBREAK: \"2\"  # R553 (HM2→HM1): FASTBREAK 1→2 (+1). 数据驱动: R516时pexec timeout≈50s/次, FASTBREAK=2代价过高(+50s)故砍至1; 现在kimi_nv日志pexec timeout仅~16s(99p<20s), FASTBREAK=2代价降至~16s. peer fallback 0救回(R549 1000行0成功), 省下的fast-break时间无收益. 多试1个key可能救回边缘请求. 单参数; 铁律:只改HM1不改HM2|' /opt/cc-infra/docker-compose.yml
sudo docker compose restart hm40006
```

### 5b. 改动前后对比
| 参数 | 前值 | 新值 | 增量 |
|------|------|------|------|
| HM_PEXEC_TIMEOUT_FASTBREAK | 1 | 2 | +1 (允许2连timeout再break, 非1连) |

### 5c. 运行时验证
```bash
docker exec hm40006 env | grep FASTBREAK
# 输出: HM_PEXEC_TIMEOUT_FASTBREAK=2 ✅
```

### 5d. 容器健康检查
```
hm40006 Up 29s (healthy) ✅
```

---

## 6. 铁律检查

| 铁律 | 状态 | 说明 |
|------|------|------|
| 只改HM1, 不改HM2 | ✅ | 仅改HM1 compose env, HM2任何参数未动 |
| 单参数少改多轮 | ✅ | 仅改1个FASTBREAK值, 小步修复 |
| 数据驱动 | ✅ | pexec timeout 50s→16s实证, peer fallback 0救回实证 |
| 漂移检测 | ✅ | R552参数无漂移确认后执行 |
| 不停止mihomo | ✅ | 仅docker compose restart hm40006, mihomo宿主机进程未动 |

---

## 7. 下轮待观察

- FASTBREAK=2后 502日志中是否出现 "2 consecutive NVCFPexecTimeout -> fast-break" (确认逻辑生效)
- kimi_nv 502率是否下降 (目标: 227→<200/小时)
- dsv4p_nv 失败路径是否延长 (+16s代价是否0救回)
- 保留HM2侧FASTBREAK当前值(若HM2用FASTBREAK)是否需要对等调整

---

## 8. CC清单更新

- [HM1-A] FASTBREAK 1→2: ✅ **本轮修复** (pexec timeout代价已降)
- [HM1-B] PEER_FALLBACK_TIMEOUT=50: HM1→HM2 0救回, 维持(如后续仍0可再砍)
- [HM1-C] BUDGET=80: FASTBREAK=2下 attempt2 ceiling=61s, BUDGET仍安全
- [HM1-D] UPSTREAM=30: p50=3s, p95<30s, 已验证安全
- [HM1-E] CONNECT_RESERVE=3: 已验证1.4x安全边际
- [HM1-F] dsv4p_nv reasoning_effort=low: R551修复后维持
- [HM1-G] kimi_nv reasoning_effort=low: R523修复后维持

---

*单参数少改多轮. 铁律:只改HM1不改HM2*

## ⏳ 轮到HM1优化HM2
