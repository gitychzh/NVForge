# R1142: HM2→HM1 — NOP (false trigger, undecuple-dispatch of R1133, 6h: 47req/36OK(76.6%SR)/11fail, all 10 zombie_empty_completion code-level glm5_2_nv integrate, 1 ATE dsv4p_nv, 0 tier_attempts, 0 fallback, all params at floor/optimal, no config change justified). 铁律:只改HM1不改HM2

## ⚡ 触发检测
- 脚本检测: HM1提交了新commit → 轮到HM2执行优化
- 实际: R1141的git push触发检测脚本（undecuple-dispatch of R1133）
- 模式: R1134-R1142连续11轮false trigger，全部源自同一HM2→HM1 NOP的git push链式触发
- 脚本自判: "这是我提交的, 不触发" — 检测到commit author=opc2_uname（HM2自身），判定为self-trigger

## 📊 数据收集 (2026-07-11 ~07:20 UTC, HM1容器 nv_gw 创建于 2026-07-10 19:03 UTC, 运行~12h)

### 6h DB统计 (nv_requests)
```
total | ok | fail | sr_pct
  47  | 36 |  11  |  76.6
```
- SR: 76.6% (36/47) — 与R1141的66.7%有改善，但属正常波动（zombie burst退潮 + 窗口滑动）

### 最近10条请求 (延迟+状态)
```
ts                      | request_model | status | ttfb_ms | duration_ms | error_type               | upstream_type
2026-07-10 23:20:28     | glm5_2_nv     |    200 |    5146 |        9504 |                          | nv_integrate
2026-07-10 23:20:24     | glm5_2_nv     |    200 |    3737 |        3738 |                          | nv_integrate
2026-07-10 23:20:19     | glm5_2_nv     |    200 |    3483 |        3484 |                          | nv_integrate
2026-07-10 23:03:33     | glm5_2_nv     |    502 |    6912 |        6913 | zombie_empty_completion  | nv_integrate
2026-07-10 23:03:24     | glm5_2_nv     |    200 |    3801 |        3801 |                          | nv_integrate
2026-07-10 22:33:54     | glm5_2_nv     |    502 |    2990 |        2991 | zombie_empty_completion  | nv_integrate
2026-07-10 22:33:38     | glm5_2_nv     |    200 |   11008 |       11009 |                          | nv_integrate
2026-07-10 22:33:33     | glm5_2_nv     |    502 |    3276 |        3277 | zombie_empty_completion  | nv_integrate
2026-07-10 22:33:29     | glm5_2_nv     |    502 |    2040 |        2041 | zombie_empty_completion  | nv_integrate
2026-07-10 22:33:24     | glm5_2_nv     |    502 |    3235 |        3236 | zombie_empty_completion  | nv_integrate
```

### 按路径 (6h)
```
upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur
nv_integrate  |  39 | 29 |     5662 |    6493 |   24927
nvcf_pexec    |   7 |  7 |    11550 |   11550 |   23757
(NULL)        |   1 |  0 |      673 |   61142 |   61142
```

### 错误分类 (6h)
```
error_type             | cnt | request_model | avg_ttfb | avg_dur
zombie_empty_completion |  10 | glm5_2_nv     |     3830 |    3831
all_tiers_exhausted     |   1 | dsv4p_nv      |      673 |   61142
```

### 每小时分布
```
17:00 UTC:  2 req, 1 zombie
18:00 UTC:  9 req, 0 zombie (clean)
19:00 UTC:  6 req, 0 zombie (clean)
20:00 UTC:  7 req, 0 zombie (clean)
21:00 UTC:  9 req, 0 zombie (clean)
22:00 UTC:  9 req, 8 zombie (burst, 89%)
23:00 UTC:  5 req, 1 zombie
```
- 22:00 UTC burst与R1138-R1141模式一致，但已退潮

### nv_tier_attempts (6h): **0 rows** — 所有失败均为zombie级或单次ATE，无key尝试记录

### fallback: 0/47 fallback_occurred — 无任何fallback触发

### docker logs (nv_gw, tail 100 / --since 6h)
- [REQ]: 36条（--since 6h窗口）
- NV-INTEGRATE-SUCCESS: 33条 — glm5_2_nv integrate全部首次成功
- NV-ZOMBIE-EMPTY: 9条（tail 100）/ 9条（--since 6h）
- NV-ZOMBIE-ERROR-CHUNK: 9条 — 检测→发送content_filter SSE chunk正常
- NV-TIER-FAIL: 0条
- NV-EMPTY-FASTBREAK: 0条
- NV-GLOBAL-COOLDOWN: 0条
- NV-MS-FB: 0条
- NV-PEER-FB: 0条

### 容器env确认（与R1140-R1141完全一致）
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
NVU_STREAM_TOTAL_DEADLINE_S=42   ← optimal (R835b/R839)
NVU_STREAM_FIRST_BYTE_DEADLINE_S=20 ← optimal (R839)
NV_INTEGRATE_MODELS=glm5_2_nv    ← all glm5_2_nv integrate
NV_KEY_INTEGRATE_KEYS=dsv4p_nv:5;minimax_m3_nv:5 ← dsv4p/minimax per-key split
```

### /health
```
{"status":"ok","nv_num_keys":5,"nvcf_pexec_models":["kimi_nv","dsv4p_nv","glm5_2_nv","minimax_m3_nv"],
 "nv_model_tiers":["kimi_nv","dsv4p_nv","glm5_2_nv","minimax_m3_nv"],"nv_default_model":"dsv4p_nv","port":40006}
```

## 🔬 分析

### 数据与R1138-R1141一致（第11轮重复）
- 6h SR=76.6% (47req/36OK/11fail) — 波动向上属正常（zombie burst窗口滑动，22:00 burst退潮）
- 10 zombie_empty_completion — 全是glm5_2_nv integrate，NVCF行为
- 1 ATE dsv4p_nv — 频率极低 (1/47)，配置无关
- 0 tier_attempts / 0 fallback
- All params exactly at floor/optimal

### Zombie模式无变化
- glm5_2_nv integrate路径，NVCF服务端返回empty completion
- 所有integrate key首次成功 → zombie发生在stream完成阶段
- 22:00 UTC burst: 8/9 (89%) — 与R1138-R1141模式完全一致
- 18:00-21:00 UTC: 0 zombie (100% SR clean) — 同样一致
- **code-level，非config可修复**
- 检测→ERROR-CHUNK→openclaw fallback链正常工作

### dsv4p_nv ATE无变化
- 1 ATE, 61,142ms, 频率极低 (1/47)
- 配置无关 — 独立于所有可调参数

### 参数全部处于floor/optimal
- 所有FASTBREAK: floor (1)
- UPSTREAM_TIMEOUT: 66 (精确对齐NVCF)
- TIER_COOLDOWN_S: 15 (floor)
- BUDGET系列: 全部对齐/充足
- COOLDOWN_S/BUFFER/CONNECT: 保守配置正常
- STREAM_DEADLINE: 分工互补(20+42), optimal
- PEER_FB_SKIP_MODELS=glm5_2_nv: zombie是code-level NCFV行为，peer-fb一样会遇zombie

## 🚫 决策: NOP (无优化操作)

**理由**:
1. **False trigger**: R1133的undecuple-dispatch（第11次链式触发），非真轮触发。脚本自判"这是我提交的, 不触发"
2. **Data consistent**: 6h数据与R1138-R1141模式一致（47-60req/66-77%SR/10-19zombie），SR波动向上仅为窗口滑动效应
3. **Zombie code-level**: 10/11失败为zombie_empty_completion，0 tier_attempts，是NVCF glm5_2_nv integrate服务端行为。检测逻辑正常工作（ZOMBIE-EMPTY→ERROR-CHUNK→openclaw fallback）。任何config调参不会改变NVCF行为
4. **参数全部处于floor/optimal**: 所有可调参数已到floor，上调会损害SR/增加延迟，下调无空间
5. **铁律: 只改HM1不改HM2** — HM1无任何配置需要更改
6. **无新信号**: 11轮数据未出现任何新的错误类型、AT E模式、或参数漂移，无任何优化切入点

## ⏳ 轮到HM1优化HM2