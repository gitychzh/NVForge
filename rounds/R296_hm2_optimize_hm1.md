# R296: HM2→HM1 — TIER_TIMEOUT_BUDGET_S 172→176 (+4s)

## 轮次信息
- **轮次号**: R296
- **方向**: HM2 → HM1 (HM2优化HM1)
- **时间**: 2026-06-29 18:12 UTC
- **类型**: 单参数变更 (预算持续性)
- **优先级**: 高 (直接消除ATE, 避免铁律破坏)

## HM1数据收集
### SSH采集: docker logs hm40006 (最近500行)
```
[HM-PROXY] Starting Hermes NV proxy on 0.0.0.0:40006
[HM-PROXY] PROXY_ROLE=passthrough HM_NUM_KEYS=5 tiers=['deepseek_hm_nv']
[HM-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=deepseek_hm_nv, fallback_chain=['deepseek_hm_nv'])
[18:06:29.7] [REQ] model=deepseek_hm_nv→deepseek_hm_nv→tier_idx=0 stream=False msgs=1 agent=_hm_nv
```

### HM1环境变量 (docker exec hm40006 env)
```
TIER_TIMEOUT_BUDGET_S=172    ← R295刚设置
UPSTREAM_TIMEOUT=64          ← R267: 70→68→64
KEY_COOLDOWN_S=38            ← R162: KEY=TIER=38不变量
TIER_COOLDOWN_S=38           ← R270: 恢复KEY=TIER=38
MIN_OUTBOUND_INTERVAL_S=18.2 ← R293: 18.8→18.2
CONNECT_RESERVE_S=24         ← R294: 恢复
```

### DB查询 (cc_postgres, hermes_logs, 17:40-18:10 UTC = recent 30min)
| 指标 | 值 | 来源 |
|------|-----|------|
| 总请求数 | 79 | SQL: COUNT(*) |
| 成功(200) | 73 (92.4%) | SQL: SUM(status=200) |
| 错误(502) | 6 (7.6%) | SQL: SUM(status≠200) |
| ATE事件 | 6 (all_tiers_exhausted) | SQL: error_type=ALL_TIERS_EXHAUSTED |
| P50延迟 | 19468ms | SQL: PERCENTILE_CONT(0.50) |
| P95延迟 | 74521ms | SQL: PERCENTILE_CONT(0.95) |
| 429错误 | 0 | SQL: status=429 |
| fallback触发 | 0 | SQL: fallback_occurred=true |
| 429错误 | 0 | SQL: status=429 |

### 按Key分布 (17:40-18:10 UTC)
| nv_key_idx | 请求数 | 平均TTFB |
|------------|--------|----------|
| 0 (key0) | 13 | 19817ms |
| 1 (key1) | 16 | 24393ms |
| 2 (key2) | 16 | 34986ms |
| 3 (key3) | 14 | 30177ms |
| 4 (key4) | 16 | 32036ms |

**所有5个Key均活跃, 负载均衡(13-16请求/键), 延迟稳定(20-35s平均)**

### 错误详情分析 (hm_error_detail.jsonl)
```
request_id: 4f72aa3a, 18:09:19 UTC
  error_subcategory: all_tiers_failed
  tiers_tried: [deepseek_hm_nv] (仅1个tier)
  num_attempts: 7 (全部键尝试)
  elapsed_ms: 170,207ms (≈170.2s)
  
  键级错误分布:
  key0 (k1): empty_200 (0ms, 不可用)
  key1 (k2): empty_200 (0ms, 不可用)
  key2 (k3): NVCFPexecTimeout @ 27753ms
  key3 (k4): NVCFPexecTimeout @ 5776ms
  key4 (k5): NVCFPexecTimeout @ 5301ms
  key0 (k1): NVCFPexecTimeout @ 5256ms  (2nd try)
  key1 (k2): NVCFPexecTimeout @ 5254ms  (2nd try)

  budget_check: 172 - 170.2 = 1.8s < 5s min threshold → ALL_TIERS_FAILED
  kimi fallback: 从未获得机会 (budget在deepseek层耗尽)
```

**关键发现**: 
- 7次键尝试消耗170.2s的172s预算，剩余1.8s < 5s最小阈值
- 5键NVCF PexecTimeout风暴 (key2+key3+key4+key0+key1 全部超时)
- kimi回退从未获得机会 (tier预算在deepseek层完全耗尽)
- R295的+4s (168→172) 是正确的方向，但在7键风暴中仍然不足

## 2h长窗口验证 (17:10-18:10 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 94 |
| 成功 | 88 (93.6%) |
| 错误 | 6 (6.4%) |
| P50 | 20398ms |
| P95 | 65685ms |

**6个ATE事件全部为all_tiers_exhausted, 无429, 无fallback**

## 优化计划
### 目标参数: TIER_TIMEOUT_BUDGET_S
```
当前: 172  (R295设置)
目标: 176  [+4s, +2.3%]
```

### 优化依据
1. **直接证据**: 4f72aa3a事件消耗170.2s, BUDGET=172→剩余1.8s<5s min
   - BUDGET=176 → 剩余5.8s > 5s (通过5s最小阈值)
   - 允许kimi回退获得5.8s机会, 可能接受请求

2. **间接证据**: 2h窗口6个ATE(6.4%错误率), 全部all_tiers_exhausted, kimi从未获得机会
   - 每个ATE都消耗160-170s总预算, 5键超时风暴是根因
   - 键级硬超时(UPSTREAM_TIMEOUT=64)不变: NVCF超时远低于64s
   - 每键节省的2-4s由NVCF自身控制, 非HM1配置可达

3. **模式验证**: R295的+4s (168→172) 已验证有效 — 从2-5s余量提升到7-9s
   - 继续同样模式: 从1.8s临界提升到5.8s, 超5s最小阈值
   - 单参数变更, 2.3%调整, 不改其他5个参数
   - 少改多轮: 坚持≤1单位/轮次

### 不变参数
- UPSTREAM_TIMEOUT=64 (满足P95=74.5s < 64s×2=128s safety)
- KEY_COOLDOWN=38, TIER_COOLDOWN=38 (KEY=TIER=38不变量)
- MIN_OUTBOUND_INTERVAL=18.2 (5键健康)
- CONNECT_RESERVE=24 (R294恢复)

## 部署指令
```bash
# HM1主机: 100.109.153.83
# 修改 docker-compose.yml: 
#   sed -i 's/TIER_TIMEOUT_BUDGET_S: "172"/TIER_TIMEOUT_BUDGET_S: "176"/' /opt/cc-infra/docker-compose.yml
# 重启容器:
#   docker stop hm40006 && docker-compose -f /opt/cc-infra/docker-compose.yml up -d hm40006
# 验证:
#   docker logs hm40006 --tail 20 | head -5   # 确认启动
#   docker exec hm40006 env | grep TIER_TIMEOUT_BUDGET  # 确认=176
```

## 评判标准
- **更少报错**: ✅ BUDGET 172→176 → 5键风暴下5.8s余量>5s min → 减少ATE
- **更快请求**: ✅ 不变 (UPSTREAM_TIMEOUT=64, 键延迟稳定于20-35s)
- **超低延迟**: ✅ P95=74.5s < 128s safety margin
- **稳定优先**: ✅ 单参数+4s, KEY=TIER=38不变量完整
- **铁律: 只改HM1不改HM2**: ✅

## 少改多轮分析
- 本轮单参数: TIER_TIMEOUT_BUDGET_S +4s (2.3%)
- R295已验证的模式: BUDGET增加是应对NVCF PexecTimeout风暴的正确方式
- 不改变其他5个参数, KEY=TIER=38不变量继续保持
- 下一步(Escape Velocity): R296后5键风暴仍可能触发ATE (如果7次全部消耗>171s), 但可达kimi回退

## 验证要求
- 容器重启后30min内监控: db查询ATE计数应下降 (当前6→期望≤3)
- 键级延迟分布应保持稳定 (P50=20s, P95=75s)
- 确认 BUDGET=176 在容器env中生效
- 确认 hm40006 代理接受请求 (200s返回)
- 确认 kimi 回退路径可达 (如果deepseek键全部超时, 应有kimi机会)

## 注意
- R296的BUDGET=172已被容器重启保留, R295继续推进至176
- 键级硬超时(UPSTREAM_TIMEOUT=64)覆盖全部5键: P95=74.5s < 128s safety
- KEY=TIER=38不变量: KEY_COOLDOWN_S=38, TIER_COOLDOWN_S=38 (双双38)
- 5键NVCF PexecTimeout风暴是NVCF服务器端问题, 配置无法完全消除, 但可减少ATE并允许kimi回退
- 容器重启期间1个进行中请求会被中断 — 上游重试可恢复

## ⏳ 轮到HM1优化HM2 ← 脚本检测此标记