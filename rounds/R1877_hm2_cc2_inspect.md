# R1877 (HM2 cc2): 巡检轮 bug8 降级兜底 in-vivo 后第33轮持续0触发 链路稳 SR93.65% 回93边缘偏低仍>93 nv_breaker state 本窗仍1吸收态 出现新NV-ANTH-BREAKER-FAIL事件但state衰减非续增触OPEN

> 本轮 = NOP (0 改动, 0 restart). 改前必有数据, 改后必有验证.

## 改前数据 (30min 窗, 本 session ~10:46 CST 拉取)

### SR
- 30min: 200:59 / 502:4 → **SR = 59/63 = 93.65%**.
  **较 R1875 96.7% 下降 3.05, 回 93% 边缘偏低但仍 >93**, 属抖动区间下沿.
  连续 HM2 SR 抖动序列 (R1866/R1869/R1876 为 peer HM2→HM1 轮不计入):
  R1860 96.2 / R1861 98.0 / R1862 99.0 / R1863 97.6 / R1864 98.6 / R1865 94.3
  / R1867 93.5 / R1868 93.8 / R1870 94.6 / R1871 96.8 / R1872 96.6 / R1873 95.7
  / R1874 96.0 / R1875 96.7 / **R1877 93.65**.
  连破计数仍 0 (R1856 92.6 + R1857 90.2 连 2 轮破 93 早被 R1858 94.7 反弹打断;
  本轮 93.65 > 93, 单轮偏低未破 93, 不构成连续破 93).
  **未达连续 >=3 轮破 93 触发线** (需重新累积连续 3 轮 <93 才达介入线).

### 502 分类 (4 条)
- stream_first_byte_timeout 2 (NVCF 侧 ttfb 偶发, 已知分类 config 不可修, R1851-R1875 间歇).
- all_tiers_exhausted 1 (tier 全 key 耗尽走 ms 兜底, 与 breaker 日志 NV-MS-FB-ATTEMPT/SERVED 呼应;
  **本窗新增此分类**, 属 tier 耗尽兜底动作本身非 nv_gw config 新可修分类).
- stream_absolute_cap 1 (NVCF 侧上游 token abs_cap, 已知分类 config 不可修, R1851-R1875 间歇).
- 4 条全 NVCF 侧偶发/tier 耗尽, 与 R1851-R1875 同构 (本窗无 zombie_empty_completion, 无新可配置分类).

### tier pexec (30min)
- pexec_success 28 (干净).
- pexec_empty_200 5 + empty_200 1 + pexec_timeout 2 (NVCF 侧偶发).
- **pexec_SSLEOFError 1 (本窗首现)**: R1850-R1875 一直"干净无 SSLEOF" 本轮首次出现 1 条.
  SSLEOFError 是 NVCF 上游连接被掐的 tier 子分类 (NVCF 侧偶发, 非 nv_gw config 可修的新分类),
  单点 1 条非批量, 暂列观察项, 若下轮复现/批量才升级为信号.

### fallback (8 条, 全 SKIP-CIRCUIT)
全 bug3 75s header/ttfb 抢断 cc4101 preempt nv_gw retry, 非 nv_gw 失败 NOT counted:
- 10:21 req=8c32b1bc → FALLBACK-OK ms 3678ms (R1875 跨窗复现).
- 10:25 req=84c6bb92 → FALLBACK-OK ms 4630ms (R1875 跨窗复现).
- 10:31 req=6019a0eb → FALLBACK-OK ms 2717ms (**本窗新增**, <10s 正常).
- 10:33 req=ac206d92 → FALLBACK-OK ms 4219ms (**本窗新增**, <10s 正常).
- 10:36 req=32aae8eb → FALLBACK-OK ms 3351ms (**本窗新增**, <10s 正常).
- 10:37 req=b54c2b27 → FALLBACK-OK ms 9274ms (**本窗新增**, <10s 正常, 略偏长但仍 OK).
- 10:41 req=3e3843b9 → FALLBACK-OK ms 6790ms (**本窗新增**, <10s 正常).
- (另 1 条 10:21 之前不在此 tail 窗)
**非跳过类真请求失败 0 条, < 4 阈值. 0 中断**.
fallback ms 延迟趋势: 本窗新增 5 条均 <10s (2717/4219/3351/9274/6790ms) 回正常,
R1874-R1875 的 20s 单点慢化尖峰本窗未复现 → 单点尖峰非趋势, fallback 负载/健康无持续恶化.

### bug8 (降级兜底)
- 实战降级触发 0 (NV-TOOLCALL-JSON-DOWNGRADE 120min 窗 = 0, DB 0 + nv_gw log 0 双确认).
- 兜底在位 args 全合法不需触发, 符合 R1839 round 文件原话"兜底保险就该几乎不触发".

### breaker 30min (全 CLOSED 未 OPEN)
- 10:23:11/10:24:32/10:28:18/10:39:04/10:40:30/10:44:21 6× NV-MS-FB-ATTEMPT (nv chain all_keys_exhausted → ms 兜底,
  req=e988d0b4/3f898157/a4dfdee0/f9eddf69/2efe9c93/05b4db97; 前 3 个为 R1875 跨窗复现, 后 3 个本窗新增).
  对应 10:23:13/10:24:37/10:28:25/10:39:07/10:40:32/10:44:23 6× NV-MS-FB-SERVED state=CLOSED 无计数.
  (与 502 表 all_tiers_exhausted 1 条呼应: tier 全尽走 ms 兜底是兜底动作本身非源码 bug.)
- **10:35:42 NV-ANTH-BREAKER-FAIL** (glm5_2_nv) anth mid-stream soft-fail
  err=stream_absolute_cap -> nv_breaker recorded (state=('CLOSED', **1**, 0), req=eee8465e) **本窗新增事件**.
- **重点结论**: nv_breaker state 第二字段仍 1 (R1873 的 2 → R1874 掉到 1 → R1875 仍 1 → R1877 仍 1).
  state 在 1-3 之间漂移而非单调累积 (R1871 从 3 掉回 2, R1872/R1873 漂在 2, R1874/R1875/R1877 掉到 1),
  远低于 OPEN 阗值, 设计内吸收态且具自恢复能力.
  **本窗出现新 NV-ANTH-BREAKER-FAIL 事件 (10:35:42) 但 state 仍 1 而非续增到 3 → 即"出现事件"≠"恶化"**,
  state 重置/衰减机制正常工作.

### env / md5 / StartedAt (无漂移)
- env 无漂移: UPSTREAM=66 / TIER_BUDGET=180 / KEY_COOLDOWN=25 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_FAIL_N=1,
  全与 R1850-R1875 一致.
- oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致
  (host /opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py
   container /app/gateway/format/oai_to_anth.py).
  `_detect_bad_tool_args()` + finish() 正常路径 `_downgrade_to_end_turn` flag +
  两处 final_stop 强制 end_turn (zombie 修路 / 正常完成路径) 四要素全在.
- nv_gw 真实 StartedAt = 2026-07-18T21:26:29Z (= R1836 restart, R1839 至 R1877 未再 restart).
  → 跑 R1839 改后字节码.

## 验证结果
链路稳 (SR 93.65% 回 93 边缘偏低仍 >93, 连续 16 轮在 93 上, 较 R1875 96.7 下降 3.05 属抖动区间下沿
非系统退化连破计数仍 0) +
bug8 0 触发 (DB+log 双确认) +
breaker 全 CLOSED 未 OPEN (nv_breaker state 仍 1, 出现新事件但 state 衰减非续增触 OPEN, 出现事件≠恶化) +
fallback 非跳过类 0 + 0 中断 + 0 restart +
tier pexec 无 ATE/无 429/无 timeout-as-primary-error (pexec_SSLEOFError 1 条首现单点观察项非批量) +
/health ok (5 keys, glm5_2_nv tier 在列) + docker ps 全 Up (nv_gw Up 5h / cc4101 Up 19h / logs_db Up 2d).
StartedAt 仍 21:26:29Z 确认跑 R1839 改后字节码. 连续 33 轮 NOP (R1842-R1877) 链路稳态.

## 决策理由
介入触发四条全不满足:
1. SR 连续 >=3 轮破 93: 本轮 93.65 > 93, 连破计数 0. 不满足.
2. fallback 非跳过类 >=4: 全 SKIP-CIRCUIT, 非跳过类 0. 不满足.
3. NV-ANTH-BREAKER-FAIL OPEN: 全 CLOSED, state 仍 1. 不满足.
4. 新可配置错误分类: pexec_SSLEOFError (NVCF 上游连接掐, tier 子分类, 单点 1 条非批量) +
   all_tiers_exhausted (tier 全尽走 ms 兜底动作本身) — 均属 NVCF 侧偶发/tier 耗尽兜底动作,
   非 nv_gw config 可修的新分类, 暂列观察项.
→ 硬改违反铁律 (改前必有数据 + 无据不改). NOP 巡检轮.

## 本轮新观察 (供下轮盯)
- **SR 回 93 边缘**: R1875 96.7 → R1877 93.65, 下降 3.05 回 93 边缘偏低但仍 >93.
  若下轮再 <93 才算 1 轮新破 (不能与旧 R1856/R1857 拼成 3, R1858 94.7 已打断旧连破).
  需重新累积连续 3 轮 <93 才达介入线.
- **pexec_SSLEOFError 首现**: R1850-R1875 一直干净, 本窗 1 条单点. 下轮若复现/批量才升级信号.
- **all_tiers_exhausted 步进**: 502 表 1 条 + breaker 6× NV-MS-FB-ATTEMPT/SERVED (tier 全尽走 ms 兜底).
  tier 耗尽频率较前几轮略升, 但 ms 兜底兜住 0 中断, 暂观察是否持续.
- **nv_breaker state 仍 1**: R1873 的 2 → R1874 掉到 1 → R1875/R1877 仍 1, 吸收态具自恢复, 续盯是否漂移或续增触 OPEN.

## commit
本轮 R1877 单文件 commit (rounds/R1877_hm2_cc2_inspect.md).
peer 已抢号到 R1876 (d853dd6, BIG_INPUT_THRESHOLD 130000→115000, 只改 HM1 对 HM2 0 影响).
