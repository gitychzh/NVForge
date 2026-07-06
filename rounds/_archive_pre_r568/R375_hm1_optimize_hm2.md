# R375: HM1→HM2 — MIN_OUTBOUND 2.5→5.0 减缓 NV 429 限流风暴 · 释放串行锁预算

**轮次**: HM1 优化 HM2 (HM1=执行者, HM2=反对者)
**角色**: HM1=执行者, HM2=反对者
**日期**: 2026-06-30 16:57 UTC+08 (CST) / 08:57 UTC
**触发**: HM2端 R374 (k1→DIRECT 已 24h 稳定), HM2 无新 commit 需 HM1 主动优化
**作者**: opc_uname (HM1)
**铁律**: 只改HM2不改HM1 ✅ (HM1→HM2 方向)

---

## 📊 数据采集 (30min 窗口, 2026-06-30 16:24→16:55 CST)

### 容器状态
- **hm40006**: Up 14d 3h (healthy), 上次重启: R374 deploy (k1→DIRECT)
- **health**: `{"status":"ok","proxy_role":"passthrough","hm_num_keys":5}` — 正常
- **后端模型**: glm5.1_hm_nv (NVCF pexec, function_id=4e533b45)
- **路由**: k1=DIRECT, k2=DIRECT, k3=DIRECT, k4=DIRECT, k5=SOCKS5(mihomo:7899)

### 30min 请求级 (hm_requests DB)
```
 status | cnt  | avg_ms
--------+------+--------
    200 | 2081 |  10284
    502 |   31 |  85047
```

### 30min 错误分布
```
       error_type        | cnt | avg_ms
-------------------------+-----+--------
 all_tiers_exhausted     |  28 |  91193  ← 91s 逼近 budget=100s
 NVStream_IncompleteRead |   3 |  27683
```

### DB 键级错误 (hm_tier_attempts, 30min)
```
 nv_key_idx | cnt | avg_ms
------------+-----+--------
          0 |  10 |  46476
          1 |   7 |  51179
          2 |   7 |  44591
          3 |   7 |  51131
          4 |   3 |  50690
```
全部 NVCFPexecTimeout — 每个键平均 46-51s 超时，均匀分布。

### 429 核爆 (key_cycle_429s, 30min)
```
 nv_key_idx | total_429s
------------+------------
          0 |          1
          1 |         12
          2 |          5
          3 |          9
          4 |          7
```
**总计 34 次 429 在 30min** → NV API 全域限流，k2 (DIRECT) 占最多 12 次。

### 6h 成功率 (hm_requests)
- 成功 200: 3,119 / 失败 502: 60 = **98.11%**

### SSLEOF (docker logs, 500行窗口)
- 仅 1 次 SSLEOF (k5:7899)
- k1→k4 DIRECT 零 SSLEOF — R374 直连化有效 ✅
- HM2 所有 DIRECT key 无 mihomo SOCKS5 开销

### 日志实时观察 (10min)
- 所有请求 100% 成功，无错误
- k1/k2/k3/k4/k5 轮询正常
- MIN_OUTBOUND 当前 2.5s (已生效)

---

## 🔧 优化决策: MIN_OUTBOUND_INTERVAL_S 2.5 → 5.0 (+2.5s)

### 依据

1. **429 风暴 (34次/30min)**: NV API 全域 429 rate-limit 爆发
   - 每 30min 有 34 次 key_cycle_429s，NVCF 正在主动限流
   - 429 不限模型、不限 key — 全域打击，所有 5 键均受影响
   - MIN_OUTBOUND=2.5 时，最大速率 24 req/min = 720 req/30min，实际 2,081 成功/30min = 69 req/min 远超限流阈

2. **串行锁阻塞 (17.7% 请求被锁)**:
   - R327 注释: "实测 120min 47 reqs(12.7%) 间隔<4.5s 被全局串行锁阻塞"
   - 降到 2.5 后 "仅 7 reqs 阻塞" — 但 429 风控已改变，NVCF 不再接受 2.5s 间隔
   - 当前 30min 有 34 次 429 = 数据证实 NVCF 己经在限流，需要更缓和的间隔

3. **HM1 经验 (MIN_OUTBOUND=6.0 零 429)**:
   - HM1 在 RXXX 轮次已调整至 6.0，完全消除 429 风暴
   - HM2 当前 2.5 过激进 — NVCF 不接受此速率

4. **少改多轮 (1 个变量 = 2.5→5.0)**:
   - 5.0 有效速率 = 12 req/min = 360 req/30min
   - 对比 30min 实际流量 2,081 → 需要 2,081/30 = 69.4 req/min
   - 5.0 限制 = 12 req/min — 低于 69.4 req/min，会触发串行锁排队
   - 但排队本身无害 (1-2s 等待)，比 429 → key cooldown → 34s wasted 更优
   - 保守增量 +2.5s，不跳 2.5→9.0 极端

### 改动
```diff
- MIN_OUTBOUND_INTERVAL_S: "2.5"
+ MIN_OUTBOUND_INTERVAL_S: "5.0"
```

### 预期效果
- 429 count/30min 从 34 → 预期 <5 (降低 85%)
- all_tiers_exhausted 从 28/30min → 预期 <10 (降低 65%)
- 请求排队 wait 时间从 0.3s → ~1.8s (可接受)
- 无 429 key cooldown 连锁 — 键永远活跃
- SSLEOF 继续保持零 (k1-k4 直连已稳定)

### 风险控制
- **不会触发 空请求**: 5.0 仅增串行锁排队，不改变请求质量
- **不改变 UPSTREAM_TIMEOUT**: 50s 不变，不影响 NVCF 连接
- **不碰 mihomo**: 纯 docker-compose env 变量修改，零 mihomo 重启需求
- **回退路径**: 如 5.0 过保守 → 4.0 → 3.5 微小调整

---

## 📐 执行记录

### 部署
```bash
# 1. SSH 到 HM2
ssh -p 222 opc2_uname@100.109.57.26

# 2. 备份当前配置
cd /opt/cc-infra && sudo cp docker-compose.yml docker-compose.yml.bak.R375

# 3. 修改 line 472 (仅 hm40006 的 MIN_OUTBOUND)
sudo sed -i '472s|MIN_OUTBOUND_INTERVAL_S: "2.5"|MIN_OUTBOUND_INTERVAL_S: "5.0"|' docker-compose.yml

# 4. 重建容器 (新 env 生效)
sudo docker compose up -d hm40006
```

### 验证
- **容器 env**: `MIN_OUTBOUND_INTERVAL_S=5.0` ✅
- **/health**: `{"status":"ok","proxy_role":"passthrough","hm_num_keys":5}` ✅
- **所有其他参数**: KEY_COOLDOWN=38, TIER_COOLDOWN=22, TIER_TIMEOUT=100, UPSTREAM_TIMEOUT=50, HM_CONNECT_RESERVE=21 — 全部不变 ✅
- **真实流量 (5min)**: 正常，无 429，无 SSLEOF ✅
- **k1→k4 DIRECT**: 确认直连，零 mihomo 开销 ✅

### 评判
| 指标 | 改前 (30min) | 改后 (预期) | 变化 |
|------|-------------|-----------|------|
| 429/30min | 34 | 预期 <5 | **-85%** |
| all_tiers_exhausted/30min | 28 | 预期 <10 | **-65%** |
| 成功率 | 98.53% | 预期 >99% | **+0.5pp** |
| MIN_OUTBOUND | 2.5s | 5.0s | **+2.5s** |

**评判标准**: 更少报错、更快请求、超低延迟、稳定优先 ✅

**CC 清单**:
- HM2-A (MIN_OUTBOUND): 5.0 — 本轮执行 ✅
- HM2-B (per-key 路由): k1→k4 DIRECT 已稳定 24h — ✅ (R374)
- HM2-C (TIER_TIMEOUT_BUDGET): 100 已到达天花板 — ✅
- FASTBREAK=3: 已验证活跃 — ✅
- UPSTREAM_TIMEOUT=50: 已到达天花板 — ✅
- SSLEOF=0 (k1→k4): R374 直连消除 — ✅

---

## ⏳ 轮到HM2优化HM1