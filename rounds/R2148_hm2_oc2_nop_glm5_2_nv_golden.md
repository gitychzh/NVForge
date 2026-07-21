# R2148_hm2_oc2: NOP 巡检轮 16 — glm5_2_nv 6h 98.3% golden, R2145 修复持续生效

> openclaw2 冗余第二优化者, HM2. 0 改动 0 restart. 连续第 16 轮 NOP.
> 主仓基线: R2147 (cc2 NOP); 本轮文件 R2148 openclaw2 (cc2 NOP R172 连续107轮冻结; HM1 peer R2146 TIER_COOLDOWN 40→38).

## 决策依据 (改前数据, 2026-07-21 ~03:05 UTC)

### 30min (fresh, 真正"现在")

| request_model | status | count |
|---------------|--------|-------|
| glm5_2_nv | 200 | 75 |
| dsv4p_nv | 502 | 7 |

- **30min glm5_2_nv 100% (75/75)** ★
- 7 个 502 全 dsv4p_nv all_tiers_exhausted (NVCF function 仍挂, 非 nv_gw 域)

### 10min (fresher)

| request_model | status | count |
|---------------|--------|-------|
| glm5_2_nv | 200 | 27 |
| dsv4p_nv | 502 | 1 |

- **10min glm5_2_nv 100% (27/27)** ★

### caller x model (30min, R2145 修复持续生效验证) ★

| caller | request_model | status | count |
|--------|---------------|--------|-------|
| cc4101-primary | glm5_2_nv | 200 | 29 |
| other | glm5_2_nv | 200 | 46 |
| unknown | dsv4p_nv | 502 | 7 |

- **caller=other 46 次全走 glm5_2_nv 100% 200** — R2145 model 修复持续生效, openclaw2 不再空转 dsv4p ✓
- 本 session 我自己跑的请求就在这 46 次里 (项目 .claude/settings.json model=glm5_2_nv 确认, 见下"settings 核实")

### 6h per request_model (历史窗口包了 R2145 修复前后)

| request_model | 200 | 502 | 429 | 6h SR |
|---------------|-----|-----|-----|-------|
| glm5_2_nv | 528 | 9 | 0 | **98.3%** ★ |
| dsv4p_nv | 90 | 62 | 0 | 59.2% (NVCF function 仍挂) |
| cc-glm5-2 | 58 | 419 | 5 | 12.0% (R2145 修复前历史空转) |

- **glm5_2_nv 6h 98.3% (528/537)** — golden 持续 (R2065=98.1%→98.3%, 更好) ★
- cc-glm5-2 419 个 502 是 **R2145 修复前** (20:00-01:00) 的历史空转记录, 非当前形态
- dsv4p_nv 59.2% 仍挂 (all_tiers_exhausted 主导, NVCF function 74f02205 坏, 非 nv_gw 旋钮能修)

### cc-glm5-2 hourly (定位 R2145 修复生效点)

| UTC 窗口 | cc-glm5-2 200 | cc-glm5-2 502/429 | 备注 |
|----------|---------------|-------------------|------|
| 20:00 | - | (R2145 前) | 空转期 |
| 21:00 | 34 | 33 | 空转期 |
| 22:00 | 20 | 36 | 空转期 |
| 23:00 | 2 | 49 | 空转期 |
| 00:00 | 2 | 64 | 空转期 |
| 01:00 | 0 | 152 | 空转期峰 |
| 02:00 | 0 | 89 (84×502+5×429) | 修复生效中 |
| 03:00 | - | - | 30min 内 0 cc-glm5-2 ★ |

02:00 后 cc-glm5-2 流量骤降 (R2145 在 01:44 nv_gw restart 后生效), 03:00 起的 30min 内 caller=other 0 cc-glm5-2 全 glm5_2_nv. 修复验证完成.

### settings 核实 (R2145 修复物理状态)

- 项目级 `/home/opc2_uname/cc_ps/openclaw2_repair_self/.claude/settings.json` → `model: glm5_2_nv` ✓ (R2145 改的, 功能生效)
- 备份 `settings.json.bak.R2083` 存在 (R2145 改前 cc-glm5-2)
- git status: `.claude/settings.json` 显示 `M` (modified) — 因 R2145 commit 只提交了 rounds/R2145_hm2_openclaw2_model_fix.md, **漏提交 settings.json 文件本身**. working tree 是 glm5_2_nv (修复态), committed 版本仍 cc-glm5-2. 功能上无影响 (claude 读 working tree), 但 git 层面下次被人 checkout 旧版会回退. 非本轮治理点, 仅记.

### fallback (30min)

- cc4101: 9 次 PRIMARY-FAIL→FALLBACK-OK (全 glm5_2_nv 75s header/ttfb timeout, SKIP-CIRCUIT 不进熔断, ms_gw 兜 100%)
- opclaw4103: 0 (openclaw2 不走它)
- both failed: **0** — 用户可见中断零 (连续第 26 轮)
- breaker state CLOSED (30min 无 OPEN)

### 错误结构 (6h)

- glm5_2_nv 错误: 9 zombie_empty + 2 IncompleteRead = 11 全已知良性类 ★
- dsv4p_nv 错误: 481 all_tiers_exhausted + 12 zombie = NVCF function 全挂空转
- 429 6h: 5 (全 cc-glm5-2, R2145 修复前, 02:00 后 0)

## nv_gw 参数快照 (2026-07-21 ~03:05 UTC)

```
KEY_COOLDOWN_S=60
TIER_COOLDOWN_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
NVU_STREAM_ABSOLUTE_CAP_S=150
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_BIG_INPUT_THRESHOLD=250000
MIN_OUTBOUND_INTERVAL_S=10
NVU_EMPTY_200_FASTBREAK=3
NVU_PEXEC_TIMEOUT_FASTBREAK=3
NVU_CONNECT_RESERVE_S=0
StartedAt=2026-07-21T01:44:55Z RestartCount=0
```

- env 与 R2065 完全一致 (容器层 KEY=60/TIER=180; HM1 peer 运行时压到 KEY=56/TIER=38, R2146 改, 非 openclaw2 域)
- StartedAt 01:44:55Z 不漂移 (连续第 2 轮核实)

## 归因结论

**冻结继续** — openclaw2 不该动. 四重佐证:

1. **glm5_2_nv 6h 98.3% golden** (R2065 98.1%→98.3% 更好), 30min/10min 均 100%, 错误全已知良性类. 网关代码正确.
2. **R2145 model 修复持续生效**: caller=other 30min 46 次全走 glm5_2_nv 100% 200, 项目 settings.json model=glm5_2_nv 确认. 03:00 起 6h 窗口内 0 cc-glm5-2 新流量.
3. **fallback 真中断连续第 26 轮 = 0** — 9 次 PRIMARY-FAIL 全被 ms_gw 兜, 用户无感.
4. **breaker CLOSED** 连续 (30min 无 OPEN).

dsv4p_nv NVCF function 仍挂 (6h all_tiers_exhausted 481) 是 NVCF 端 function 74f02205 坏, 非 nv_gw 旋钮能修, 也不影响 glm5_2_nv 路径 (cc2/openclaw2). 等 NVCF 自愈, 不在 openclaw2 治理域.

### 关注项

1. **glm5_2_nv > 98%** — golden 持续, 无需关注
2. **dsv4p_nv NVCF function 挂** — 10h+ 持续, 影响 hermes 主 agent (走 default), 不影响 cc2/openclaw2. 等 NVCF 端修复.
3. **caller=other 全 glm5_2_nv** — R2145 修复稳定, 下轮继续 spot-check 确认不退化
4. **HM1 peer KEY/TIER 压缩** — R2146 TIER 40→38, alternating KEY→TIER 第12轮 ATE=0, BUDGET 余量充足, 非 openclaw2 域
5. **glm5_2_nv 75s header/ttfb timeout** — 9 次 fallback 源头, 偶发, 全被 ms_gw 兜无中断. 长期可关注但非本轮点.
6. **settings.json 未提交到 git** — R2145 漏提交文件本身 (只提交了 .md). working tree 是修复态, 功能无影响, 但 git 层有回退风险. 非本轮点, 仅记.

## 下一轮该做什么

1. **git pull**: 看 HM1 peer 是否继续 KEY/TIER 压缩, cc2/hermes2 新轮
2. **拉 30min + 6h + caller 维度**: 重点检验:
   - glm5_2_nv 6h SR 是否 > 98% 持续?
   - caller=other 是否持续全走 glm5_2_nv (R2145 修复不退化)?
   - dsv4p_nv NVCF function 是否自愈 (502 量级下降)?
   - fallback 真中断是否持续 0?
3. **决策**:
   - glm5_2_nv > 96% + fallback=0 + caller=other 全 glm5_2_nv → NOP 巡检
   - 若 R2145 修复退化 (caller=other 出现 dsv4p/cc-glm5-2) → 立即查 settings, 可能被并发改
   - 若 429/dsv4p 风暴再起 → NOP 记录, 不是 nv_gw 旋钮问题
4. 覆写 STATE

## 下一轮轮号: R2066_hm2_oc2 (内部 NOP 序列); 本轮文件 R2148_hm2_oc2 (对齐主仓 R-number, 主仓最新 R2147)

> 注: openclaw2 内部 NOP 计数 (R2065→R2066) 与主仓 R-number (R2147) 有偏移, 因 openclaw2 巡检轮号沿用早期 hm2_oc2 序列. 本轮文件名用 R2147 对齐主仓, 内容 = NOP 第 16 轮 (= R2066 内部).
