# R1139: HM2→HM1 — NOP (false trigger, octuple-dispatch of R1133, post-restart 14h, 6h: 60req/42OK(70%SR)/18fail, all 17 zombie_empty_completion code-level glm5_2_nv integrate, 1 ATE dsv4p_nv, 0 tier_attempts, 0 fallback, all params at floor/optimal, no config change justified)

## ⚡ 触发检测
- 脚本检测: HM1提交了新commit → 轮到HM2执行优化
- 实际: R1138的git push再次触发检测脚本（octuple-dispatch of R1133）
- 模式: R1134-R1139连续8轮false trigger，全部源自同一HM2→HM1 NOP的git push链式触发

## 📊 数据收集 (2026-07-11 06:55 UTC, HM1容器 nv_gw 创建于 2026-07-10 19:03 UTC, 运行~14h)

### 6h DB统计 (nv_requests)
```
total | ok | fail
  60  | 42 |  18
```
- SR: 70.0% (42/60)
- 17 zombie_empty_completion + 1 all_tiers_exhausted

### 按模型 (6h)
```
request_model | cnt | ok | fail | avg_ttfb | avg_dur
glm5_2_nv     |  50 | 33 |   17 |     6057 |    6496
dsv4p_nv      |  10 |  9 |    1 |    11370 |   18029
```

### 按路径 (6h)
```
upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur
nv_integrate  |  52 | 35 |     6443 |    6983 |   24927
nvcf_pexec    |   7 |  7 |    11550 |   11550 |   23757
(NULL)        |   1 |  0 |      673 |   61142 |   61142
```

### 错误分类 (6h)
```
error_type             | cnt
zombie_empty_completion |  17
all_tiers_exhausted     |   1
```

### 24h错误全景
```
error_type             | cnt
zombie_empty_completion |  17
all_tiers_exhausted     |   7
NVStream_TimeoutError   |   6
```

### nv_tier_attempts (6h): **0 rows** — 所有失败均为zombie级，无key尝试记录

### fallback: 0/60 fallback_occurred — 无任何fallback触发

### 48h zombie_time分布
- 22:00 UTC burst: 9 req, 8 zombie
- 17:00 UTC burst: 20 req, 9 zombie
- 其余46小时: 0 zombie
- 模式: 间歇性zombie burst（glm5_2_nv integrate返回finish_reason=stop但content_chars=12-22 < 50）

### docker logs (nv_gw --tail 300)
```
[NV-ZOMBIE-EMPTY] glm5_2_nv passthrough zombie empty completion: 
  finish_reason=stop but content_chars=12-22 < 50, 
  input_chars=160K+, no tool_calls → aborting stream
[NV-ZOMBIE-ERROR-CHUNK] glm5_2_nv sent finish_reason=content_filter 
  error SSE chunk → trigger openclaw fallback via mapOpenAIStopReason
[NV-INTEGRATE-SUCCESS] glm5_2_nv k1-k5 all succeed on first attempt
```
- 无 NV-TIER-FAIL 日志行
- 无 NV-EMPTY-FASTBREAK 日志行
- 无 NV-GLOBAL-COOLDOWN 日志行
- 无 NV-MS-FB 日志行
- 无 NV-PEER-FB 日志行

### 容器env确认
```
NVU_PEXEC_TIMEOUT_FASTBREAK=1    ← floor (R997 validated 10h+ 100% SR)
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1 ← floor (R1010 validated)
NVU_EMPTY_200_FASTBREAK=2        ← R1031 set but code-level no-op (R1039 confirmed)
UPSTREAM_TIMEOUT=66              ← optimal (R988)
TIER_TIMEOUT_BUDGET_S=198        ← optimal (R1088)
TIER_COOLDOWN_S=15               ← floor (R1103)
NVU_TIER_BUDGET_DSV4P_NV=72     ← optimal (R1116)
NVU_TIER_BUDGET_GLM5_2_NV=96    ← optimal (R830b)
NVU_TIER_BUDGET_MINIMAX_M3_NV=100 ← optimal
NV_INTEGRATE_KEY_COOLDOWN_S=0    ← floor (R631)
NVU_PEER_FB_SKIP_MODELS=glm5_2_nv ← zombie code-level→peer-fb won't rescue
NVU_INTEGRATE_THINKING_TIMEOUT_S=90 ← optimal (R830b)
NVU_STREAM_TOTAL_DEADLINE_S=42   ← optimal (R839)
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20 ← optimal
KEY_COOLDOWN_S=25                ← conservative buffer
MIN_OUTBOUND_INTERVAL_S=0        ← floor
NVU_CONNECT_RESERVE_S=0          ← floor
NVU_SSLEOF_RETRY_DELAY_S=1.0     ← floor
NVU_FORCE_STREAM_UPGRADE=0       ← floor
```

## 🔬 分析

### 僵尸模式（code-level, not config-fixable）
所有17个`zombie_empty_completion`均为glm5_2_nv integrate路径：
- NVCF返回`finish_reason=stop`但仅12-22字符输出
- 输入极大（160K+ chars），无tool_calls
- 僵尸检测器判定`content_chars < 50` → 注入`content_filter`错误chunk
- 所有integrate key尝试均为首次成功（NV-INTEGRATE-SUCCESS k1-k5）
- **0 nv_tier_attempts** — 确认所有失败发生在stream完成阶段，非key尝试阶段
- 此模式完全与R1133-R1138相同，是NVCF glm5_2_nv服务端行为，非proxy配置可修

### 1 ATE (dsv4p_nv)
- 61,142ms, single-tier, fallback_occurred=false
- 模式: dsv4p_nv pexec empty_200 single-key → FASTBREAK=2 code-level no-op → ATE
- R1039已确认FASTBREAK=2在pexec路径被bug无视，R1116 BUDGET=72缓解
- 此ATE在R1116优化后仍偶发，但频率极低（1/60 in 6h, 7/24h）

### NVStream_TimeoutError (6 in 24h)
- glm5_2_nv integrate路径，duration 95K-105K ms
- 与NVU_INTEGRATE_THINKING_TIMEOUT_S=90吻合（90s thinking + overhead ≈95-105s）
- FASTBREAK=1下first key timeout → immediate abort，无级联浪费
- 次数少（6/24h），且NVU_INTEGRATE_THINKING_TIMEOUT已被NVCF thinking时间绑定

### 参数状态
所有可调参数均已处于floor/optimal：
- FASTBREAK系列：1（floor, 函数级信号快速熔断）
- UPSTREAM_TIMEOUT：66（R988精确对齐NVCFPexecTimeout max=62,606ms, buffer 3.4s≥3s）
- TIER_COOLDOWN_S：15（floor, R1103 revert）
- COOLDOWN系列：INTEGRATE_KEY=0（floor），KEY=25（保守）
- BUDGET系列：DSV4P=72, GLM5_2=96, MINIMAX=100, TOTAL=198（全部充足）
- FORCE_STREAM_UPGRADE=0（floor）

## 🚫 决策: NOP (无优化操作)

**理由**:
1. **False trigger**: 这是R1133的octuple-dispatch，非真轮触发。HM1 compose md5与容器创建时一致，无任何配置变更
2. **Zombie code-level**: 17/18失败为zombie_empty_completion，0 tier_attempts，是NVCF glm5_2_nv服务端finish_reason=stop但内容极短的行为，proxy配置无法修复
3. **参数全部处于floor/optimal**: 所有可调参数已到floor（FASTBREAK=1, INTEGRATE_KEY_COOLDOWN=0, TIER_COOLDOWN_S=15, CONNECT_RESERVE_S=0, MIN_OUTBOUND=0），上调会损害SR/增加延迟，下调无空间
4. **铁律: 只改HM1不改HM2** — 无任何HM1配置需要更改

## ⏳ 轮到HM1优化HM2