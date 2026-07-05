# R758: HM2 nv_gw NVU_PEXEC_TIMEOUT_FASTBREAK 1→3 — 修复 dsv4p_nv 1 次 timeout 即放弃 5 key 的误杀

> 仅改 HM2。HM1 全未动 (生产冻结, 待 HM2 验证 + 用户授权后同步)。

## 改前数据 (hermes 飞书报 hm4104 fallback 提醒, 深入排查)

### dsv4p_nv 3h 量化 (hermes_logs DB)
| 指标 | 值 |
|---|---|
| 总请求 | 97 |
| 成功 200 | 63 (64.9%) |
| 失败 502 | 34 (35.1%) |
| 失败 error_type | 100% all_tiers_exhausted (34/34) |
| 成功 p50/p90 | 23.4s / 37.5s |
| 502 p50/p90 | 40.6s / 41.0s |

### fast-break 触发 (1h)
- NV-PEXEC-FASTBREAK 触发 22 次 (dsv4p_nv 16 次)
- PEER-FB: 21 OK / 9 FAILED (70% 救活)
- NVCF pexec timeout 耗时: 40.5~44.6s (UPSTREAM_TIMEOUT=40 卡死)

### 关键证据: "5 key 全故障" 是假象
NV-TIER-FAIL 日志反复出现:
```
tier=dsv4p_nv all 5 keys failed: 429=0, empty200=0, timeout=1, other=0, elapsed=40679ms
```
"all 5 keys failed" 但 "timeout=1" — 数学矛盾。FASTBREAK=1 让第 1 个 key timeout 即 break, 其余 4 key 根本没试。

### 5 key 救援分布 (6h, 证明 k2-k5 完全能成功)
| key_idx | ok | total |
|---|---|---|
| 0 (k1) | 40 | 40 |
| 1 (k2) | 45 | 45 |
| 2 (k3) | 31 | 31 |
| 3 (k4) | 44 | 44 |
| 4 (k5) | 43 | 43 |

5 key 成功均匀 (40-45), 每个独立可用。k1 timeout 不代表 k2-k5 也会, 但 FASTBREAK=1 从不给它们机会。

## 根因 (代码级)

### 配置 (两机一致, R742 注释记 "FASTBREAK=1 unchanged")
- compose env: NVU_PEXEC_TIMEOUT_FASTBREAK=1
- config.py 默认值 3 (upstream.py:445), 但 compose env 覆盖成 1
- 某时间点 (R735 前, 无轮次记录) 两机都被改成 1, 违背 R347 原始设计

### 代码 (upstream.py:678 pexec / :322 integrate, 同构)
```python
consecutive_pexec_timeout += 1
if consecutive_pexec_timeout >= PEXEC_TIMEOUT_FASTBREAK:  # =1 → 第 1 次 timeout 即触发
    _log("NV-PEXEC-FASTBREAK", "... fast-break (saved remaining keys)")
    break  # ← 跳出 key 循环, 其余 4 key 不试
```

### R347 设计意图 vs 实际
- R347/R349/R350: N=3, "前 3 次连续 timeout 即 break, rescue 2/231=0.87% 可接受"
- R365-R384 多轮验证 N=3 最优 (R372: "FASTBREAK=3 被 24h 救援数据证伪最优, eq2=11+eq3=7 牺牲救回换 260s 净亏")
- N=1 把所有 k2-k5 rescue 机会全杀, 违背设计

### 故障完整链
1. dsv4p_nv NVCF 74f02205 偶发挂死, pexec 40s timeout
2. FASTBREAK=1 → 第 1 个 key timeout 立即 break, 4 key 不试
3. all_tiers_exhausted (谎报"5 key 全失败", 实试 1 个) → 502
4. PEER-FB 到 HM1 (21/9 = 70% 救活)
5. PEER-FB 失败的 9 次 → hm4104 502 → fallback dsv4p_ms → 用户看到提醒

## 改动 (单参数, 1 行)

### 改了什么
`/opt/cc-infra/docker-compose.yml`:
```
- NVU_PEXEC_TIMEOUT_FASTBREAK=1   →   NVU_PEXEC_TIMEOUT_FASTBREAK=3
```
恢复 R347 原始设计 (N=3)。仅 HM2。

### 为什么是 3 不是 5
- R347 数据 N=3, rescue 0.87% 可接受
- R365-R384 长期验证 N=3 最优
- N=5: 5×40s=200s > TIER_TIMEOUT_BUDGET_S=110, budget 先 break
- 当前 5 key 成功均匀 (40-45/key), N=3 让 k1-k3 各试一遍, k4/k5 仍可救

### 不改的东西 (明确边界)
- 不改代码逻辑 (upstream.py:678 break 保持, 只调阈值)
- 不改 UPSTREAM_TIMEOUT=40 (本轮聚焦 fastbreak, 单参数铁律; UPSTREAM 40 vs R757 记 66 是另一漂移, 留下轮)
- 不改 HM1 (生产冻结)
- 不改 nv_gw/ms_gw 源码 (模块化铁律)
- 不改 hm4104 adapter (R757 已修 PRIMARY_STREAM_TIMEOUT_S=150, adapter 正常)

### 部署
compose env 改动, bind-mount 在位:
```
cd /opt/cc-infra && docker compose up -d nv_gw   # 不用 build
```

## 改后验证

### 配置生效
- `docker exec nv_gw env | grep FASTBREAK` → NVU_PEXEC_TIMEOUT_FASTBREAK=3 ✓
- `curl /health` → 200 ✓

### 实测链路 (改后立即)
- 直测 nv_gw dsv4p_nv: "你好" 200, k1 一次成功 18.6s ✓
- hm4104 (hermes 路径): "你好" 200, k2 一次成功 28.7s ✓
- 无 fast-break 触发, 无 PEER-FB, 无 fallback 提醒 ✓

### 改后 5min 窗口
- dsv4p_nv: 6/6 全成功, 0 个 502 (baseline 64.9%)
- NV-PEXEC-FASTBREAK: 0 次 (baseline 16 次/h)
- (00:23:48 有 1 次 hm4104 fallback, 是 nv_gw 重启瞬间端口断 RemoteDisconnected, 非 fast-break 问题, 预期行为)

## 预期效果 (可证伪, 待 30min+ 窗口观察)
1. NV-PEXEC-FASTBREAK 触发条件从 "1 timeout" 变 "3 consecutive timeouts"
2. NV-TIER-FAIL 的 timeout= 从 1 变 3 (真试 3 个 key 才放弃)
3. dsv4p_nv 成功率 64.9% → 75%+ (救回 k2-k3 rescue 机会)
4. 502 数量下降, PEER-FB 触发减少
5. hm4104 fallback 提醒频率显著下降

## 代价 (可接受)
- 单次 502 耗时 40s → 120s (3×40s), 但 502 数量减少
- TIER_TIMEOUT_BUDGET_S=110 兜底, 不会无限拖

## 风险
- 低: 恢复 R347 原始设计, N=3 在 R365-R384 长期验证过
- 回滚: env 改回 1 即可, 1 行
- HM1 隔离: 只改 HM2

## 遗留 (下轮候选)
- UPSTREAM_TIMEOUT=40 漂移 (R754-R757 记 66, 当前 40, 无轮次记录下调) — 独立问题, 下轮处理
- HM1 同步 FASTBREAK=3 (待 HM2 验证稳 + 用户授权)
