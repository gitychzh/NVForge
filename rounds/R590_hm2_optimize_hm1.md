# R590: HM2→HM1 — NOP (Post-Deploy Unmeasurability). R589 cooldown 95→90  Post-deploy sample极小，保护实验完整性; 完整候选评估表; 铁律:只改HM1不改HM2

## 漂移检测

### 四源交叉验证
| 源 | 检查项 | 状态 | 备注 |
|---|---|---|---|
| 源1: 容器env | NV_INTEGRATE_KEY_COOLDOWN_S=90 | ✅ 通过 | R589值生效 |
| 源2: compose文件 | NV_INTEGRATE_KEY_COOLDOWN_S: "90" | ✅ 通过 | 第487行，与env一致 |
| 源3: 容器StartedAt | 2026-07-02T22:02:46.467702901Z | ✅ 通过 | 与R589部署时间吻合 |
| 源4: 运行时日志 | 零ERROR/WARN | ✅ 通过 | 仅NV-INTEGRATE-SUCCESS/NV-SUCCESS |

**结论**: R589部署无漂移，env/compose/StartedAt/日志四源一致。

## 数据采集 (R590)

### 预检
- HM1 Tailscale可达: ✅ SSH成功，docker正常
- 容器状态: nv_40006_uni Up (healthy)

### 关键数据问题: PostgreSQL 时钟偏移
执行 `docker exec cc_postgres psql -U litellm -d hermes_logs -c "SELECT NOW()"` 返回 `2026-07-02 22:17:21.950481+00`。
而HM2本地脚本时间戳 `[2026-07-03 06:10:08]` 表明真实UTC约为 07-03 06:10。
**DB服务器NOW()比真实时间慢约8小时**，导致 `ts > NOW() - interval '1 hour'` 查询实际返回约 **9小时跨度** 的历史数据（725 requests），而非真实的最近1小时。

### Post-Deploy 样本
使用固定时间过滤（基于容器StartedAt推断的实际部署时间 `ts > '2026-07-03 06:02:00+00'`）:
| 指标 | 值 |
|---|---|
| post-deploy total | 7 |
| success | 7 (100%) |
| fail | 0 |
| integrate error | 0 |
| 429 rate limit | 0 |

**post-deploy n=7，全部成功，零失败。关键路径（integrate错误/429/ATE）样本为零。**

### 历史数据快照 (NOW()-1h错位查询结果，含大量旧regime，仅供参考)
| 模型 | total | success | fail | SR% | ATE min_fail_ms | note |
|---|---|---|---|---|---|---|
| dsv4p_nv | 494 | 477 | 17 | 96.6% | 61560 | integrate覆盖率~31% |
| kimi_nv | 170 | 120 | 50 | 70.6% | 61911 | 小时级SR剧烈波动(16%→100%)，系NVCF function级surge |
| glm5_1_nv | 27 | 18 | 9 | 66.7% | 485 | NVCF EOL/410 |
| glm5_2_nv | 55 | 54 | 1 | 98.2% | 34750 | 新模型表现良好 |
| **Total** | **746** | **669** | **77** | **89.7%** | — | 含硬故障恢复期旧数据 |

- nv_tier_attempts 1h: dsv4p_nv 16×429 attempts (k0/k1/k2/k4分布), 2×empty_200, 1×502_integrate_error
- 但上述429 attempts可能大部分来自R589部署前的旧regime(95/100/105/110/120s cooldown)，不可作为90s效果的评估依据。

## 候选参数评估表

| 参数 | 旧值 | 候选新值 | 评估 | 决策 |
|------|------|----------|------|------|
| NV_INTEGRATE_KEY_COOLDOWN_S | 90 | 85 (-5s) | **Post-deploy n=7, zero integrate errors/429 → 无数据判断方向。若90已触发429 surge, 无样本无法发现。** | ❌ (unmeasurable) |
| NV_INTEGRATE_KEY_COOLDOWN_S | 90 | 95 (+5s) | 同样无post-deploy数据证实90过短，盲调会浪费R589实验 | ❌ (unmeasurable) |
| MIN_OUTBOUND_INTERVAL_S | 0.4 | 0.3 (-0.1s) | Post-deploy zero-error，但刚在R582改0.5→0.4，连续两轮同一参数违反铁律 | ❌ |
| UPSTREAM_TIMEOUT | 28 | 26 (-2s) | Zero ceiling binding证据(min_fail=61.6s>2×28); 21 integrate/pexec success零timeout | ❌ |
| TIER_TIMEOUT_BUDGET_S | 90 | 85 (-5s) | 历史硬故障期min_fail=61.6s，90余量28.4s安全; 但成功请求kimi max=351s属integrate streaming，BUDGET不binding | ❌ |
| TIER_TIMEOUT_BUDGET_S | 90 | 95 (+5s) | 无regime变化证据(post-deploy 7 req全成功); R576已回调至90，无需继续放宽 | ❌ |
| NVU_EMPTY_200_FASTBREAK | 2 | 1 (-1) | Zero empty_200 in post-deploy; 历史R567→0后被surge期证伪有害; 2为平衡点 | ❌ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | 2 (+1) | R553→2被R559证伪; R559后长期稳定; post-deploy零pexec timeout | ❌ |
| NVU_PEER_FALLBACK_TIMEOUT | 25 | 20 (-5s) | Post-deploy zero peer-fb触发; 但降5s需零成功证据支撑 | ❌ |
| NVU_CONNECT_RESERVE_S | 2 | 1 (-1s) | Zero connection error; 但2已为保守值(实测connect max=2.1s)，降1s余量微负边际 | ❌ |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | 0.8 (-0.2s) | Zero SSLEOF; 但1.0为HM2对称值，R543后长期稳定，微降无显著收益 | ❌ |

**所有候选均因 post-deploy unmeasurability 或 data-veto 被否。**

## 分析与决策

1. **R589部署状态**: 已生效，无漂移，四源一致。
2. **Post-deploy可测性**: n=7, 0 failure, 0 integrate error/429/timeout. 无法评估 NV_INTEGRATE_KEY_COOLDOWN_S=90 的真实效果（是否引发429增加或integrate覆盖率提升）。
3. **历史数据污染**: 由于DB时钟偏移，`ts > NOW() - interval '1 hour'` 包含了16:00-06:00（硬故障恢复期+surge期）的大量旧regime数据，不能用于R589后参数决策。
4. **关键教训**: 后续数据采集应使用固定时间字符串过滤（`ts > '2026-07-03 06:02:00+00'`）而非`NOW()-interval`，直至DB时钟修复。
5. **零错误状态**: post-deploy 100% SR（7/7），但样本极小。不应在零样本上做micro-trimming，避免R589效果被污染。

**决策: R590 = 完整NOP。不写任何HM1参数，不写任何HM1代码，只做验证+记录。**

## 执行记录

- `ssh -p 222 opc_uname@100.109.153.83`: ✅ HM1可达，Tailscale正常，docker健康
- `docker exec nv_40006_uni env`: ✅ R589全参数与compose一致
- `docker inspect StartedAt`: ✅ 2026-07-02T22:02:46Z
- Docker logs (tail 300): 仅2个NV-SUCCESS/1个NV-INTEGRATE-SUCCESS，零ERROR/WARN/429/empty200/peer-fb
- DB `\dt`: nv_requests / nv_tier_attempts ✅
- Post-deploy数据: 7 requests, 7 success, 0 fail, 0 integrate error, 0 429
- **未修改任何HM1文件**
- **未重启HM1容器**

## ⏳ 轮到HM1优化HM2
