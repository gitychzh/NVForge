# R1878 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第34轮持续0触发 链路稳 SR94.2% 回升仍>93 nv_breaker state 仍1吸收态 出现新NV-ANTH-BREAKER-FAIL事件但state衰减非续增触OPEN pexec_SSLEOFError连续2轮单点未批量升观察项

> 本轮 = NOP (0 改动, 0 restart). 改前必有数据, 改后必有验证.

## 改前数据 (30min 窗, 本 session ~10:55 CST 拉取)

### SR
- 30min: 200:65 / 502:4 → **SR = 65/69 = 94.2%**.
  **较 R1877 93.65% 回升 0.55, 仍 >93**, 属抖动区间下沿回升.
  连续 HM2 SR 抖动序列 (R1866/R1869/R1876 为 peer HM2→HM1 轮不计入):
  R1860 96.2 / R1861 98.0 / R1862 99.0 / R1863 97.6 / R1864 98.6 / R1865 94.3
  / R1867 93.5 / R1868 93.8 / R1870 94.6 / R1871 96.8 / R1872 96.6 / R1873 95.7
  / R1874 96.0 / R1875 96.7 / R1877 93.65 / **R1878 94.2**.
  连破计数仍 0 (R1856 92.6 + R1857 90.2 连 2 轮破 93 早被 R1858 94.7 反弹打断;
  R1877 93.65 > 93 单轮未破, 本轮 94.2 > 93 亦单轮未破, 不构成连续破 93).
  **未达连续 >=3 轮破 93 触发线** (需重新累积连续 3 轮 <93 才达介入线).

### 502 分类 (4 条)
- stream_first_byte_timeout 2 (NVCF 侧 ttfb 偶发, 已知分类 config 不可修, R1851-R1877 间歇).
- all_tiers_exhausted 1 (tier 全 key 耗尽走 ms 兜底, 与 breaker 日志 NV-MS-FB-ATTEMPT/SERVED 呼应;
  tier 耗尽兜底动作本身非 nv_gw config 新可修分类).
- stream_absolute_cap 1 (NVCF 侧上游 token abs_cap, 已知分类 config 不可修, R1851-R1877 间歇).
- 4 条全 NVCF 侧偶发/tier 耗尽, 与 R1877 同构 (本窗无 zombie_empty_completion, 无新可配置分类).

### tier pexec (30min)
- pexec_success 36 (干净).
- pexec_empty_200 5 + empty_200 1 + pexec_timeout 2 (NVCF 侧偶发).
- **pexec_SSLEOFError 1**: R1877 首现后**本轮复现**, 已是"下轮复现" → 升级为持续观察项.
  但仍单点 1 条非批量 (R1877 1 条 + R1878 1 条, 2 轮各 1 条), 未达批量恶化阈值.
  SSLEOFError 是 NVCF 上游连接被掐的 tier 子分类 (NVCF 侧偶发, 非 nv_gw config 可修的新分类),
  续盯: 若下轮再复现且批量 (>=3 条/30min) 才升级为系统恶化信号.

### fallback (7 条, 全 SKIP-CIRCUIT)
全 bug3 75s header/ttfb 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted:
- 10:25 req=84c6bb92 → FALLBACK-OK ms 4630ms (R1875/R1877 跨窗复现).
- 10:31 req=6019a0eb → FALLBACK-OK ms 2717ms (R1877 跨窗复现).
- 10:33 req=ac206d92 → FALLBACK-OK ms 4219ms (R1877 跨窗复现).
- 10:36 req=32aae8eb → FALLBACK-OK ms 3351ms (R1877 跨窗复现).
- 10:37 req=b54c2b27 → FALLBACK-OK ms 9274ms (R1877 跨窗复现).
- 10:41 req=3e3843b9 → FALLBACK-OK ms 6790ms (R1877 跨窗复现).
- 10:49 req=d3ce9c44 → FALLBACK-OK ms 18009ms (**本窗新增**, 18s 单点慢化尖峰).
  **非跳过类真请求失败 0 条**, < 4 阈值. **0 中断**.
  **fallback ms 延迟趋势**: R1877 新增条均 <10s, 本窗新增 10:49 req=d3ce9c44 18009ms 又一单点 ~18s 慢化尖峰,
  其前后 (10:41 6790ms) <10s 正常 → 仍是单点尖峰非趋势, fallback 负载/健康无持续恶化, ms_gw 热备兜住 0 中断.

### bug8
- 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 60min nv_gw log + 120min DB 双确认 = 0).
  兜底保险在位但 args 全合法不需触发, 符合 R1839 round 文件原话"兜底保险就该几乎不触发".

### breaker 30min: 全 CLOSED 未 OPEN (设计内)
- 10:24:32 / 10:28:18 / 10:39:04 / 10:40:30 / 10:44:21 5× NV-MS-FB-ATTEMPT (nv chain all_keys_exhausted,
  tier 耗尽走 ms 兜底) req=3f898157 / a4dfdee0 / f9eddf69 / 2efe9c93 / 05b4db97.
- 10:24:37 / 10:28:25 / 10:39:07 / 10:40:32 / 10:44:23 5× NV-MS-FB-SERVED (ms 兜底 served,
  nv breaker recorded failure state=CLOSED 无计数).
- **10:35:42 NV-ANTH-BREAKER-FAIL** (glm5_2_nv) anth mid-stream soft-fail
  err=stream_absolute_cap -> nv_breaker recorded (state=('CLOSED', **1**, 0), req=eee8465e) **本窗新增事件**.
- **重点结论**: nv_breaker state 第二字段 R1873=2 → R1874/R1875/R1877=1 → 本轮 R1878 仍 1 (req=eee8465e).
  **本窗出现新 NV-ANTH-BREAKER-FAIL 事件 (10:35:42) 但 state 仍持 1 而非续增到 2/3 → 即"出现事件"≠"恶化"**,
  state 在 1-3 之间漂移而非单调累积, 远低于 OPEN 阈值, 设计内吸收态且具自恢复能力,
  state 重置/衰减机制正常工作, 比 R1873 漂在 2 更乐观.

### env 无漂移
- KEY_COOLDOWN_S=25 / KEY_AUTHFAIL_COOLDOWN_S=60 / NV_INTEGRATE_KEY_COOLDOWN_S=90
  / NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_COOLDOWN_S=180 / UPSTREAM_TIMEOUT=66
  / TIER_TIMEOUT_BUDGET_S=180 / TIER_COOLDOWN_S=25 / MIN_OUTBOUND_INTERVAL_S=0.
  全与 R1850-R1877 一致.

### bug8 四要素 (in-vivo 在位确认)
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致
  (host `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
   container `/app/gateway/format/oai_to_anth.py`).
- `_detect_bad_tool_args()` + finish() 正常路径 `_downgrade_to_end_turn` flag
  + 两处 final_stop 强制 end_turn (zombie 修路 / 正常完成路径) 四要素全在.
- nv_gw 真实 StartedAt = **2026-07-18T21:26:29Z** (= R1836 restart, R1839 至 R1877 未再 restart) → 跑改后字节码.
- /health ok (status=ok, nv_num_keys=5, nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"]).
- docker ps 全 Up (nv_gw Up 5h / cc4101 Up 19h / logs_db Up 2d).

## 验证结果
- 链路稳: SR 94.2% > 93 (较 R1877 93.65 回升 0.55, 抖动区间下沿回升, 连破计数 0).
- bug8 0 触发 (60min log + 120min DB 双确认).
- breaker 全 CLOSED 未 OPEN (nv_breaker state 本窗仍 1, 出现新事件但 state 持 1 非续增触 OPEN, 比 R1873 漂在 2 更乐观).
- fallback 非跳过类 0 + 0 中断 + 0 restart.
- tier pexec pexec_success 36 干净 (SSLEOFError 连续 2 轮各 1 条单点未批量, 升持续观察项).
- /health ok + docker ps 全 Up.
- StartedAt 仍 21:26:29Z 确认跑 R1839 改后字节码.
- 连续 32 轮 NOP (R1842-R1878) 链路稳态.

## 决策理由 (NOP)
介入触发四条全不满足:
1. SR 94.2% > 93 (连续未破, 连破计数 0; R1877 93.65 + R1878 94.2 均 >93 单轮未破, 需重新累积连续 3 轮 <93 才达介入线).
2. fallback 非跳过类真失败 0 < 4 (全 75s 抢断 SKIP-CIRCUIT, 非 nv_gw 失败).
3. NV-ANTH-BREAKER-FAIL 全 CLOSED 未 OPEN (state 本窗仍 1, 出现新事件但 state 持 1 非续增触 OPEN).
4. 无新可配置错误分类 (4 条 502 全 NVCF 侧 ttfb/abs_cap + tier all_keys_exhausted 耗尽兜底, 与 R1877 同构;
   SSLEOFError R1877 首现本轮复现仍单点 1 条非批量, 已升持续观察项但未达批量恶化信号).
→ 硬改违反铁律 (改前必有数据 + 无据不改). NOP.

## 下一轮重点盯
- **nv_breaker state**: 续盯是否继续漂移 (1↔2↔3) 或单调续增触 OPEN. 本窗出现新事件但 state 持 1 非续增, 比 R1873 漂在 2 更乐观.
- **SR**: 若 R1879 <93 → 只算 1 轮新破, 不能与旧 2 轮 (R1856 92.6 + R1857 90.2) 拼成 3 触发线 (R1858 94.7 已打断旧连破),
  需重新累积连续 3 轮破 93 才达介入线.
- **pexec_SSLEOFError**: 连续 2 轮单点 1 条 (R1877+R1878), 若下轮再复现且批量 (>=3 条/30min) 才升级为系统恶化信号, 否则仍单点偶发.
- **fallback ms 延迟**: 本窗 10:49 req=d3ce9c44 18009ms 单点 ~18s 慢化尖峰, 续观察是否复现/恶化 (单点非趋势).

## 介入触发条件 (任一满足才动手, 否则继续 NOP 巡检)
1. SR 连续 >=3 轮跌破 93% (系统退化信号, 非抖动).
2. fallback 中非跳过类 (FALLBACK-OK 真正 nv_gw 失败) >=4 次/30min.
3. NV-ANTH-BREAKER-FAIL 出现 OPEN (state 中第一字段变 OPEN, 超过 zombie 软挂).
4. 出现新的可配置错误分类 (非 NVCF 侧 zombie/timeout/gap/cap), 或 SSLEOFError 批量化 (>=3 条/30min).

## 备注
- 本轮 R1878 commit 单文件 (rounds/R1878_hm2_cc2_inspect.md), 无 peer 误收 (git pull 后仓库停在 R1877, 未新增 peer 轮).
- 本轮 0 改动 0 restart 0 中断, 维持 bug8 兜底在位观测 + 巡检节奏.
