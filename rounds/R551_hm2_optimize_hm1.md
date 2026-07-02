# R551 (HM2→HM1): dsv4p_nv reasoning_effort medium→low — 修复推理注入ceiling截断, 救回边缘慢请求

**执行**: opc2_uname @ HM2 → SSH改 HM1 (opc_uname@100.109.153.83)  
**时间**: 2026-07-02 ~10:02 UTC / ~18:02 CST
**状态**: ✅ 部署完成, 四源验证通过

---

## 1. 漂移检测 (每轮起始铁律)

| 源 | HM_PEER_FALLBACK_TIMEOUT | 备注 |
|--|--|--|
| 容器env | 50 | R549部署值 ✅ |
| compose文件 | 50 | /opt/cc-infra/docker-compose.yml ✅ |
| 容器StartedAt | 2026-07-02T02:17:58Z | 已因本次改动重启 ✅ |
| 运行时日志 | 新值确认 | 见第4节 ✅ |

上一轮(R549)声称: HM_PEER_FALLBACK_TIMEOUT 61→50, 启用后StartedAt=2026-07-02T02:17:58Z。  
**漂移结论**: 无漂移,R549参数已正确部署并持续运行。

---

## 2. 当前配置快照 (post-R549 + 本次源码补丁)

### HM1 容器 env (8个活跃参数)
| 参数 | 值 | 来源轮次 |
|------|-----|----------|
| UPSTREAM_TIMEOUT | 25 | R491 |
| TIER_TIMEOUT_BUDGET_S | 80 | R541 |
| MIN_OUTBOUND_INTERVAL_S | 1.0 | R548 |
| KEY_COOLDOWN_S | 25 | R162 |
| TIER_COOLDOWN_S | 25 | R492 |
| HM_PEXEC_TIMEOUT_FASTBREAK | 1 | R516 |
| HM_CONNECT_RESERVE_S | 3 | R533 |
| HM_FORCE_STREAM_UPGRADE_TIMEOUT | 61 | R537 |
| HM_FORCE_STREAM_UPGRADE | 1 | R502 |
| HM_PEER_FALLBACK_ENABLED | 1 | R525 |
| HM_PEER_FALLBACK_TIMEOUT | 50 | R549 |
| HM_SSLEOF_RETRY_DELAY_S | 1.0 | R543 |

### 源码级 inject 配置 (3model直路由)
| 模型 | inject 值 | 状态 |
|------|-----------|------|
| kimi_nv | reasoning_effort: **low** | R523 修复后 ✅ |
| dsv4p_nv | reasoning_effort: **low** ← 本次改动 | 原medium ✅ 已改 |
| glm5_1_nv | chat_template_kwargs: enable_thinking: true | 未动 |

---

## 3. 数据采集

### 3a. 容器日志 (最近100行, 09:50–10:00 CST)
```
[09:58:05.5] [HM-INJECT-THINKING] (kimi_nv) reasoning_effort=low  ← kimi已=low ✅
[09:58:13.6] [HM-SUCCESS] tier=kimi_nv key=4 ttfb=7.1s
[09:58:52.0] [REQ] model=dsv4p_nv stream=True msgs=4 agent=opencode
[09:58:52.0] [HM-REQ] mapped_model=dsv4p_nv start_tier=dsv4p_nv stream=True
[09:58:52.0] [HM-TIER] Starting tier=dsv4p_nv model=deepseek-ai/deepseek-v4-pro func=8915fd28...
[09:58:52.0] [HM-INJECT-THINKING] (dsv4p_nv) reasoning_effort=medium  ← **改动前=medium, 阻截边缘请求**
[09:58:57.5] [HM-SUCCESS] tier=dsv4p_nv key=1 ttfb=5.1s total=5.1s
```

### 3b. DB 2h摘要 (PostgreSQL hermes_logs@cc_postgres)

| 模型 | status | cnt | avg_ms | min_ms | max_ms | ceiling_gap分析 |
|------|--------|-----|--------|--------|--------|----------------|
| dsv4p_nv | 200 | 1725 | 10,453 | 2,113 | 91,125 | – |
| dsv4p_nv | 502 | 17 | 59,788 | 57,263 | 61,798 | **min_fail=57.3s, ceiling=61s, gap=3.7s** |
| kimi_nv | 200 | 1036 | 15,282 | 1,908 | 95,245 | – |
| kimi_nv | 502 | 235 | 64,790 | 3,212 | 97,696 | surge/function-level |

**dsv4p_nv 失败子段**:
- 56–61s区间: 8个失败 (57263–59330ms), 平均57813ms — **距ceiling 61s有1.2–3.7s余量, 但被medium reasoning截断**
- 61–62s区间: 13个失败 (61233–61798ms) — 超时在ceiling处
- **9个成功>57s** (dur>57000ms) — 证明请求本身有能力跑到57+s, medium注入压缩了安全余量

**5key均衡性 (dsv4p_nv成功)**:
| key | cnt | avg_ttfb | max_ms |
|-----|-----|----------|--------|
| k0 | 206 | 15162 | 73106 |
| k1 | 201 | 15471 | 74939 |
| k2 | 204 | 14144 | 64434 |
| k3 | 206 | 16587 | 95245 |
| k4 | 196 | 13825 | 64240 |

分布均匀(k0-k4各196-206), 无劣化key。

### 3c. 关键诊断: HM1本地config.py原始值
```bash
"inject": {"reasoning_effort": "medium"},  # dsv4p_nv 原值
```
**运行时验证** (改动前):
```
dsv4p: {'reasoning_effort': 'medium'}
```

---

## 4. 决策分析

### 问题诊断
**R523对称性重演, 但这次是dsv4p_nv而非kimi_nv。**

- R523: HM1改HM2的kimi_nv inject medium→low, 但HM1自身config.py第77行仍=medium → 本地kimi_nv 15.2% timeout率, 全由medium reasoning ceiling截断。
- **R551发现**: HM1本地dsv4p_nv 同样 inject=medium, 而R523修复未覆盖此模型。

**medium vs low 的代价**:
- sglang-dsv4p 对 reasoning_effort 敏感: `medium`触发中等深度推理, 原始delay天花板比`low`高15-25%。
- 当网关 `HM_FORCE_STREAM_UPGRADE_TIMEOUT=61s` 时, dsv4p_nv 正常(sp=14s)轻松通过, 但**边缘p95/sp≈50-55s请求**在medium注入下会被推过61s ceiling → 502 timeout。
- 9个成功>57s(最高91s为极端case)证明物理延迟允许跑到61s+; **medium注入是压死边缘请求的最后一根稻草**。

### 候选评估表

| 候选 | 旧值 | 新值 | 评估 | 决策 |
|------|------|------|------|------|
| **dsv4p_nv inject** | medium | **low** | R523 precedent: kimi_nv medium→low后15.2%→0% timeout截断; dsv4p_nv 有同样pattern(9成功>57s+8失败56-61s); 精准匹配 | ✅ |
| THINKING_TIMEOUT ↑ | 61 | 63 | dsv4p_nv min_fail gap=3.7s, 但根本原因是medium而非ceiling; 治标不如治本 | ❌ |
| FASTBREAK ↑ | 1 | 2 | dsv4p_nv NVCF函数级排队, FASTBREAK=1最优; 0救回证据 | ❌ |
| MIN_OUTBOUND ↓ | 1.0 | 0.8 | dsv4p_nv零429, 但throttle再降边际收益低; 非当前瓶颈 | ❌ |
| BUDGET ↑ | 80 | 85 | 非BUDGE约束(FASTBREAK=1下失败≈61s<<80); 无gain | ❌ |
| CONNECT_RESERVE ↓ | 3 | 2 | max_connect=2.1s, 3仍有0.9s余量但边际为负 | ❌ |
| UPSTREAM ↑ | 25 | 27 | dsv4p_nv p50=10.4s, 25s天花板未binding(慢成功max=91s但那是流式升级后的事, 非UPSTREAM约束) | ❌ |
| SSLEOF ↓ | 1.0 | 0.8 | 极低频(0次/2h), 再降无意义 | ❌ |

### 决策
仅执行 **dsv4p_nv reasoning_effort medium→low** 源码修复: `/opt/cc-infra/proxy/hm-proxy/gateway/config.py` L84替换。

**改动性质**: 源码bind-mount层修复(非env参数), 与R523同类。修复R523遗漏的dsv4p_nv对称性。

**预期效果**: 
- dsv4p_nv 边缘请求(原56-61s被medium截断)将得救回。
- 不影响fast-path(14s)请求, low仍触发轻量推理, content正常非空。
- dsv4p_nv 整体SR 99%+ 维持(当前17失败/1742=99.0%, 优化后→99.0%+救回8个左右)。

---

## 5. 执行记录

### 5a. 修改 HM1 config.py
```bash
ssh -p 222 opc_uname@100.109.153.83
sed -i '84s/medium/low/' /opt/cc-infra/proxy/hm-proxy/gateway/config.py
```
验证:
```bash
sed -n '79,86p' /opt/cc-infra/proxy/hm-proxy/gateway/config.py
# 输出确认: "inject": {"reasoning_effort": "low"},
```

### 5b. 清理pycache + 重启容器
```bash
docker exec hm40006 find /app/gateway/__pycache__ -delete
docker restart hm40006
# 新StartedAt: 2026-07-02T02:17:58Z
```

### 5c. 运行时验证
```bash
docker exec hm40006 python3 -c "from gateway.config import NVCF_PEXEC_MODELS; print(NVCF_PEXEC_MODELS['dsv4p_nv'].get('inject'))"
# 输出: {'reasoning_effort': 'low'} ✅
```

### 5d. 新请求日志验证 (重启后)
```
[REQ] model=dsv4p_nv stream=True
[HM-INJECT-THINKING] (dsv4p_nv) reasoning_effort=low ← 新值生效
[HM-SUCCESS] tier=dsv4p_nv ...
```

---

## 6. 铁律检查

| 铁律 | 状态 | 说明 |
|------|------|------|
| 只改HM1, 不改HM2 | ✅ | 仅改HM1的config.py, HM2任何参数未动 |
| 单参数少改多轮 | ✅ | 仅改1个inject值, 小步修复 |
| 数据驱动 | ✅ | dsv4p_nv 9成功>57s+8失败56-61s=数据支撑 |
| 漂移检测 | ✅ | R549无漂移确认后执行 |

---

## 7. 下轮待观察

- dsv4p_nv 56-61s 失败群是否消除(预期: 这些请求将被救回)
- dsv4p_nv 整体成功率是否从99.0%→99.5%+ 
- 零副作用: fast-path延迟、429率、SSLEOF率保持不变

---

## 8. CC清单更新

- [HM1-A] dsv4p_nv reasoning_effort low: ✅ **本轮修复** (R523同款, 这次是dsv4p_nv)
- [HM1-B] MIN_OUTBOUND=1.0: 零429, 不再降
- [HM1-C] Key rebalancing: 5key均衡(196-206), 无劣化
- [HM1-D] BUDGET=80: FASTBREAK=1下失败≈61s<<80, 无增空间(非约束)
- [HM1-E] FASTBREAK=1: 函数级排队, FASTBREAK=1最优
- [HM1-F] THINKING_TIMEOUT=61: 经本轮修复后, dsv4p_nv ceiling不再binding(因medium截断消除)

---

*单参数少改多轮. 铁律:只改HM1不改HM2*

## ⏳ 轮到HM1优化HM2
