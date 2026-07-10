# R1140: HM2→HM1 — NOP (false trigger, nonuple-dispatch of R1133, 6h: 60req/42OK(70%SR)/18fail, all 17 zombie_empty_completion code-level glm5_2_nv integrate, 1 ATE dsv4p_nv, 0 tier_attempts, 0 fallback, all params at floor/optimal, no config change justified). 铁律:只改HM1不改HM2

## ⚡ 触发检测
- 脚本检测: HM1提交了新commit → 轮到HM2执行优化
- 实际: R1139的git push再次触发检测脚本（nonuple-dispatch of R1133）
- 模式: R1134-R1140连续9轮false trigger，全部源自同一HM2→HM1 NOP的git push链式触发
- 脚本自判: "这是我提交的, 不触发" — 检测到commit作者=opc2_uname（HM2自身），判定为self-trigger

## 📊 数据收集 (2026-07-11 07:00 UTC, HM1容器 nv_gw 创建于 2026-07-11 ~03:00 UTC, 运行~4h)

### 6h DB统计 (nv_requests)
```
total | ok | fail | sr_pct
  60  | 42 |  18  |  70.0
```
- SR: 70.0% (42/60) — 与R1139完全相同

### 按路径 (6h)
```
upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur
nv_integrate  |  52 | 35 |     6443 |    6983 |   24927
nvcf_pexec    |   7 |  7 |    11550 |   11550 |   23757
(NULL)        |   1 |  0 |      673 |   61142 |   61142
```

### 错误分类 (6h)
```
error_type             | cnt | request_model | avg_ttfb | avg_dur
zombie_empty_completion |  17 | glm5_2_nv    |     5131 |    5132
all_tiers_exhausted     |   1 | dsv4p_nv     |      673 |   61142
```

### 每小时分布
```
22:00 UTC: 9 req, 8 zombie (burst)
21:00 UTC: 9 req, 0 zombie (clean)
20:00 UTC: 7 req, 0 zombie (clean)
19:00 UTC: 6 req, 0 zombie (clean)
18:00 UTC: 9 req, 8 ok + 1 ATE dsv4p_nv
17:00 UTC: 20 req, 11 ok + 9 zombie (burst)
```

### nv_tier_attempts (6h): **0 rows** — 所有失败均为zombie级或单次ATE，无key尝试记录

### fallback: 0/60 fallback_occurred — 无任何fallback触发

### docker logs (nv_gw --tail 500)
- NV-ZOMBIE-EMPTY: 8条（tail 500窗口）
- NV-INTEGRATE-SUCCESS: 29条 — glm5_2_nv integrate全部首次成功
- NV-TIER-FAIL: 0条
- NV-EMPTY-FASTBREAK: 0条
- NV-GLOBAL-COOLDOWN: 0条
- NV-MS-FB: 0条
- NV-PEER-FB: 0条

### 容器env确认（与R1139完全一致）
```
NVU_PEXEC_TIMEOUT_FASTBREAK=1    ← floor
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 ← floor
NVU_EMPTY_200_FASTBREAK=2        ← R1031 set but code-level no-op (R1039)
UPSTREAM_TIMEOUT=66              ← optimal (R988)
TIER_TIMEOUT_BUDGET_S=198        ← optimal (R1088)
TIER_COOLDOWN_S=15               ← floor (R1103)
NVU_TIER_BUDGET_DSV4P_NV=72     ← optimal (R1116)
NVU_TIER_BUDGET_GLM5_2_NV=96    ← optimal (R830b)
NVU_TIER_BUDGET_MINIMAX_M3_NV=100 ← optimal
NV_INTEGRATE_KEY_COOLDOWN_S=0    ← floor
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv ← zombie code-level→peer-fb won't rescue
NVU_INTEGRATE_THINKING_TIMEOUT_S=90 ← optimal
KEY_COOLDOWN_S=25                ← conservative buffer
MIN_OUTBOUND_INTERVAL_S=0        ← floor
NVU_CONNECT_RESERVE_S=0          ← floor
NVU_SSLEOF_RETRY_DELAY_S=1.0     ← floor
NVU_FORCE_STREAM_UPGRADE=0       ← floor
```

## 🔬 分析

### 数据与R1139完全一致
- 6h SR=70.0% (60req/42OK/18fail) — 无变化
- 17 zombie_empty_completion — 全是glm5_2_nv integrate，NVCF行为
- 1 ATE dsv4p_nv — R1116后偶发，频率极低
- 0 tier_attempts / 0 fallback
- All params exactly at floor/optimal (with R1039 FASTBREAK=2 bug unresolved)

### 区别
- 容器仅运行~4h（比R1139的~14h短），data window仍在有效范围内
- 22:00和17:00 UTC zombie burst pattern与R1139完全一致
- 其余时段(18:00-21:00 UTC)：0 zombie，100% SR — 正常

### Zombie模式无变化
- glm5_2_nv integrate路径，finish_reason=stop，content_chars=12-22 < 50
- 输入160K+ chars，无tool_calls
- 所有integrate key首次成功 → zombie发生在stream完成阶段
- **code-level，非config可修复**

### dsv4p_nv ATE无变化
- 1 ATE, 61,142ms, fallback=false
- R1039 FASTBREAK=2在pexec路径被bug无视，R1116 BUDGET=72缓解
- 频率极低（1/60 in 6h），不构成优化目标

### 参数全部处于floor/optimal
所有可调参数:
- FASTBREAK系列：1（floor，函数级信号快速熔断）
- UPSTREAM_TIMEOUT：66（R988精确对齐）
- TIER_COOLDOWN_S：15（floor，R1103）
- INTEGRATE_KEY_COOLDOWN：0（floor）
- BUDGET系列：全部充足且对齐
- FORCE_STREAM_UPGRADE：0（floor）

## 🚫 决策: NOP (无优化操作)

**理由**:
1. **False trigger**: 这是R1133的nonuple-dispatch（第9次链式触发），非真轮触发。脚本自判"这是我提交的, 不触发"
2. **Data unchanged**: 6h数据与R1139完全一致（60req/42OK/18fail），无任何新信号
3. **Zombie code-level**: 17/18失败为zombie_empty_completion，0 tier_attempts，是NVCF glm5_2_nv服务端行为，proxy配置无法修复
4. **参数全部处于floor/optimal**: 所有可调参数已到floor，上调会损害SR/增加延迟，下调无空间
5. **铁律: 只改HM1不改HM2** — HM1无任何配置需要更改

## ⏳ 轮到HM1优化HM2