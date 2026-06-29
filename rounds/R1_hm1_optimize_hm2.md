# R1: HM1 → HM2 优化 (第一轮)

**日期**: 2026-06-29 09:58 UTC  
**方向**: HM1 优化 HM2  
**模式**: 单模型 glm5.1_hm_nv, 无回退链, 5键轮转  

---

## 📊 基线数据 (30分钟窗口)

### 请求级别 (hm_requests)
| 指标 | 数值 |
|------|------|
| 总请求 | 629 |
| 直接成功 (无回退) | 629 (100%) |
| 真实回退 | 0 (0%) |
| tiers_tried_count=0 | 188 (29.9%) |
| tiers_tried_count=1 | 441 (70.1%) |
| 平均延迟 (成功) | 31,386ms |
| 平均延迟 (0-tier) | 38,791ms |
| 平均延迟 (≥1-tier) | 28,326ms |

### 键级别成功分布
| 键索引 | 成功数 | 平均延迟 | 最小延迟 | 最大延迟 |
|--------|--------|----------|----------|----------|
| k0 | 102 | 28,497ms | 4,600ms | 123,212ms |
| k1 | 87 | 22,804ms | 2,999ms | 78,783ms |
| k2 | 89 | 31,555ms | 6,485ms | 98,230ms |
| k3 | 76 | 29,382ms | 5,708ms | 104,474ms |
| k4 | 79 | 27,573ms | 4,125ms | 101,577ms |
| NULL | 188 | 38,791ms | 2ms | 127,695ms |

### 错误分布 (hm_tier_attempts — 失败键尝试)
| 错误类型 | 总计 | 占比 |
|----------|------|------|
| 500_nv_error | 85 | 50.6% |
| 429_nv_rate_limit | 47 | 28.0% |
| empty_200 | 14 | 8.3% |
| NVCFPexecSSLEOFError | 12 | 7.1% |
| NVCFPexecConnectionResetError | 2 | 1.2% |
| NVCFPexecTimeout | 2 | 1.2% |
| **总计** | **168** | — |

### 每键错误分布
| 键 | 500 | 429 | SSLEOF | empty_200 | 其他 |
|----|-----|-----|--------|-----------|------|
| k0 | 17 | 7 | 3 | 4 | 0 |
| k1 | 20 | 10 | 0 | 4 | 2 (Reset) |
| k2 | 16 | 11 | 0 | 1 | 0 |
| k3 | 15 | 9 | 5 | 3 | 1 (Timeout) |
| k4 | 17 | 10 | 4 | 2 | 1 (Timeout) |

### 键级错误均匀性
- 每键 500 错误: 15-20 (±12.5%) — **均匀分布**
- 每键 429 错误: 7-11 (±22.2%) — **近似均匀**
- SSLEOF 集中在 k0/k3/k4 (端口 7894/7896/7899)

### 当前配置 (R272-R273 基线)
| 参数 | 值 | 来源 |
|------|-----|------|
| MIN_OUTBOUND_INTERVAL_S | 12.0 | R272: 15.6→12.0 |
| KEY_COOLDOWN_S | 32 | R272: 30→32 |
| TIER_COOLDOWN_S | 22 | R1 (无代码匹配—死变量) |
| UPSTREAM_TIMEOUT | 70 | R273: 75→70 |
| TIER_TIMEOUT_BUDGET_S | 128 | single-tier |
| HM_CONNECT_RESERVE_S | 24 | — |

---

## 🔍 瓶颈分析

### 核心发现
1. **500_nv_error 主导 (50.6%)**: NVCF API `822231fa-d4f3` (ai-glm5_1 ACTIVE function) 返回 500 错误率高达 50%+。500 错误触发键冷却 (upstream.py:340 `mark_key_cooling`), 每次冷却 = KEY_COOLDOWN_S * 2^(consecutive-1) = 32s 起步。

2. **0-tier 请求占 29.9% (188/629)**: 这些请求 `tiers_tried_count=0` 但 `fallback_occurred=false`, 平均 38.8s。它们绕过了 NV 键尝试直接成功—可能是系统内部重试或缓存路径。

3. **100% 成功, 0 回退**: 虽然 168 次键尝试失败, 但最终全部成功。系统通过键轮转和内部重试吸收所有错误。

4. **SSLEOF 集中在 k0/k3/k4**: 端口 7894/7896/7899 的 SOCKS5 代理质量偏低。

### 瓶颈定位
- 500 错误触发冷却 → 键被锁定 32s+ → 请求等待键恢复或轮转到下一个键
- 平均成功延迟 31.4s 说明每个请求经历了多次键尝试+冷却周期
- `HM_CONNECT_RESERVE_S=24s`: 连接预留时间从 tier budget 中扣除, 减少有效读取时间 `read_timeout = min(70, 128 - elapsed - 24)`. 当 tier 已耗费 100s 时, 实际读取超时只有 4s。

---

## 🎯 优化计划

### 假说
在 100% 成功 (0 回退) 场景下, 优化应聚焦于减少键轮转等待时间和加速 SSL 握手, 而非防止 429 (因为 429 只占 28%)。

### 变更

| 参数 | 旧值 | 新值 | Δ | 理由 |
|------|------|------|---|------|
| **MIN_OUTBOUND_INTERVAL_S** | 12.0 | **11.0** | **-1.0s** | 减少连续请求间隔 1s, 加速请求周转。当前 12s 为 R272 设定, 在 100% 成功下安全下调。 |
| **HM_CONNECT_RESERVE_S** | 24 | **22** | **-2s** | 减少 SSL 握手预留时间 2s, 将更多 tier budget 留给实际读取。公式: `read_timeout = min(70, remaining_budget - 22)` → 当 remaining_budget=50s 时, 读取超时=28s (vs 旧值 26s)。 |

### 不做
- ❌ 不改 `KEY_COOLDOWN_S` (32s 已保守, 500 错误触发冷却公式)
- ❌ 不改 `TIER_COOLDOWN_S` (代码中无匹配—死变量)
- ❌ 不改 `UPSTREAM_TIMEOUT` (R273 刚下调 5s, 需观察)
- ❌ 不停止/重启 mihomo (铁律)

---

## 🚀 部署验证

### 部署前备份
```bash
cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.$(date +%s)
```

### 变更实施
```bash
sed -i 's/MIN_OUTBOUND_INTERVAL_S: "12.0"/MIN_OUTBOUND_INTERVAL_S: "11.0"/' /opt/cc-infra/docker-compose.yml
sed -i 's/HM_CONNECT_RESERVE_S: "24"/HM_CONNECT_RESERVE_S: "22"/' /opt/cc-infra/docker-compose.yml
docker compose -f /opt/cc-infra/docker-compose.yml up -d --build hm40006
```

### 部署后确认
```
$ docker exec hm40006 env | grep -E 'MIN_OUTBOUND|HM_CONNECT_RESERVE'
MIN_OUTBOUND_INTERVAL_S=11.0
HM_CONNECT_RESERVE_S=22

$ curl localhost:40006/health
{"status":"ok","hm_num_keys":5,"nvcf_pexec_models":["glm5.1_hm_nv"],...}
```

### 容器状态
```
hm40006: Up 51 seconds (healthy)
其他容器 (auth_to_api_*, ms_uni41001, cc_postgres): 未受影响
```

### 预期效果
- 每个请求节省 1s (MIN_OUTBOUND) + 2s (CONNECT_RESERVE 释放给读取)
- 零 tier 请求可能因更快的连接建立而减少
- 键冷却公式不变 (500 错误仍然触发 32s 基础冷却)

---

## 📈 后续观测指标

等待下一轮 HM2 收集数据时需观测:
1. **请求平均延迟** → 是否从 31.4s 下降到 ~29s
2. **0-tier 请求占比** → 是否从 29.9% 下降 (连接更快)
3. **500_nv_error 频率** → 是否仍然主导 (NVCF 函数问题, 非配置可调)
4. **SSLEOF 分布** → 是否仍然集中在 k0/k3/k4

---

## ⏳ 轮到 HM2 优化 HM1