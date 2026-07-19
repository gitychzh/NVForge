# R1916 (HM2 cc2) — STAGE1(BUG-A) 上线后 25min 巡检 + 补提交 R1914 + STATE 纠偏

> 时间: 2026-07-19T10:05Z 拉取 (本 session, 北京 18:05, restart 09:38Z 后约 27min).
> git pull "Already up to date". 仓库最新 HEAD = `b4cd735 R1915 fix: trailing newline`.
> cc2 上一轮实际 = **R1914** (commit 未落地, 见下). peer 抢号 R1911-R1915 全 HM2→HM1 (改 HM1 侧,
> 对 HM2 0 影响, 符合铁律6). cc2 下一轮从 R1916 起 (本轮).

## 0. 本轮性质: 补提交 R1914 (铁律4 缺口) + STAGE1 上线巡检 + STATE 纠偏. 0 代码改动 0 restart.

### STATE.md 纠偏 (核心): 我接手的 STATE.md 严重过期
- STATE.md (17:06 写) 说 "StartedAt 仍 2026-07-18T21:26:29Z, R1839→R1909 未再 restart,
  cc2 上一轮 R1909 NOP". **三处过期**:
  1. StartedAt 实际 = **2026-07-19T09:38:26Z** (北京 17:38), 非 21:26:29Z. 今天 restart 过了.
  2. cc2 上一轮实际 = **R1914** (stage1 bugA archive nop, 本 session 前写的轮文件),
     非 R1909. R1911-R1913 是 peer HM2→HM1 轮 (HM1 侧), 不是 cc2 轮.
  3. R1914 轮文件 + STAGE1 归档目录 (deploy_artifacts/R1914_*) **从未 commit** (git status
     显示 `??`, untracked). R1914 自己写 "本轮 commit + push origin/main" 但没执行 →
     铁律4 违规未收尾. 本轮补这个缺口.

### 为什么本轮 0 代码改动 0 restart (而非推阶段2/3)
- 监督者 2026-07-19 16:00 巡视给的优化路径: 阶段1(修 BUG-A) → 阶段2(修 BUG-B abs_cap 允许
  ms 重放) → 阶段3(breaker 5→3) → 阶段4(目标态 ms 变瞬时兜底). **阶段1 已由前 session
  落地** (R1911 改 log+注释但漏设 _chain_failed / R1913 补全 _chain_failed=True + 1650 行
  if 分支 / 17:38 restart 生效字节码). 本轮**不该重复改**.
- 阶段1 实战验证**需攒 STAGE1 真触发样本** (NV-GLM52-CHAIN-SKIP-PEXEC2 log) 才能确认
  "fallback 请求 240s → ~120s" + "无新真中断". 当前 restart 后 25min chain 全成功,
  stage1 跳过路径 0 触发 → 无对比基线 → **阶段2/3 无据动手** (违反铁律1). 必须先攒数据.

## 1. 数据 (改前必有数据, restart 后 25min 窗 09:38Z+)

### nv_gw request 层 (09:38:26Z+ ~27min)
- SR = 50/52 = **96.2%** (200:50 / 502:2). vs R1910 90.2% / R1914 98.2% → R1916 96.2%,
  抖动区间上沿常态, STAGE1 上线后链路稳无退化.
- 502=2 全 NVCF 上游侧:
  (1) `all_tiers_exhausted`×1 (NVCF 上游侧整体不可达, 已知分类非新可配置类).
  (2) `stream_absolute_cap`×1 (502, avg 192598ms ≈ 193s) → **BUG-B 目标人群仍在产真中断**
      (abs_cap 截断后 85% 真 502, 与监督者 12h 数据 20 条 abs_cap 全 502 avg 226s 一致).
- restart 后 25min **0 条 NV-GLM52-CHAIN-FALLBACK** (chain 全成功), 0 条
  NV-GLM52-CHAIN-SKIP-PEXEC2 (stage1 跳过路径未被实战触发). 符合 R1914 预期: 链路稳时
  chain 全成功, stage1 兜底保险该几乎不触发, 等下一个 chain 失败事件才验证.

### 12h BUG-A/B 基线确认 (监督者巡视数据复算)
- 24h NV-GLM52-CHAIN-FALLBACK 147 条 (但**全 restart 前旧字节码产**, 跑老 log 字符串
  "falling back to R838b/R572/pexec" — 源码里 grep 此字符串 0 匹配, 确认是旧版).
- 24h NV-MS-FB-ATTEMPT 120 条. 差 27 个 chain 失败没走 ms: 其中 10 个被第二轮 pexec 救回
  200, 17 个仍 abs_cap 502 (与监督者算的 27 一致).
- 12h abs_cap 20 条全 502, avg 224s, max 414s (BUG-B 完全成立).
- **BUG-C 更正**: 监督者巡视说 "今日 0 条 NV-TIER-BUDGET". 实测 24h NV-TIER-BUDGET
  **132 条** (00:02/00:12/00:16 等都有 budget break 触发). budget break **在工作不是绕过**,
  监督者 "0 条" 判断是窗口不同 (他拉的可能更窄日间窗). 此更正写进 STATE 供监督者复核.

### fallback 层 (cc4101 30min)
- 2 FALLBACK-OK, 全 75s SKIP-CIRCUIT (cc4101 bug3 preempt, NOT counted, 非 nv_gw 旋钮可解).
- 0 真中断 (全被 ms_gw 兜住). 用户诉求 "可以报错但不能让 cc2 中断" 仍达成.

### breaker / bug8 / msfb 层
- breaker NV-ANTH-BREAKER-FAIL since restart **1** (glm5_2_nv abs_cap 触发, state
  CLOSED (1,0) 吸收未 OPEN). breaker OPEN 0 连续 14+ 轮 (R1910 基线延续).
- bug8 DOWNGRADE 0 触发 (连续 57 轮根除停巡).
- NV-CAP-RESET-MSFB since restart 监督者巡视说 3, 本轮 30min 窗数据未单独复算 (非介入类).

## 2. STAGE1(BUG-A) 已 in-vivo 落地实证 (沿用 R1914, 本轮复算源码+容器一致)
- 宿主 `/opt/cc-infra/proxy/nv-gw/gateway/upstream.py` mtime 17:37:36, 容器 pyc mtime 17:38,
  nv_gw StartedAt 09:38:26Z = 北京 17:38 → restart 在写盘后 ~1min, 跑新字节码.
- 源码 STAGE1 闭环 3 要素全在: 1580 行 `NV-GLM52-CHAIN-FALLBACK ... STAGE1_CHAIN_FAIL
  skip pexec 2nd round` log + 1582 行 `_chain_failed = True` + 1650 行 `if _chain_failed:`
  构造 empty all_keys_exhausted 跳过 _try_tier_keys 第二轮 + 1660 行 `NV-GLM52-CHAIN-SKIP-PEXEC2`.
- `NV_GLM52_MODE_CHAIN=integrate_us_rr,pexec_us_rr` env 已设 → 1560 行条件满足, chain branch 进.
- 容器内 1580 行内容与宿主一致 (R1914 已对比, 本轮沿用未改此文件).

## 3. 决策: 本轮 0 代码改动 0 restart

介入四条全不满足:
1. SR 96.2% 上沿常态, 未达介入线 (连续 3+ 轮跌破 80%).
2. 502=2 全 NVCF 上游侧 (ATE/abs_cap), 非新可配置类 (abs_cap 是 BUG-B 范围, 但阶段2 需
   STAGE1 触发样本作对比基线, 当前 0 触发无据动手).
3. breaker OPEN 0 连续 14+ 轮, 本轮 BREAKER-FAIL 1 被 CLOSED 吸收未 OPEN.
4. STAGE1(BUG-A) 已落地生效, 不重复改. 阶段2/3 待攒数据. 本轮补 R1914 commit 缺口.

## 4. 验证 (NOP, 0 restart)
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker ps: nv_gw "Up 25 minutes" (17:38 restart 后稳定无重启循环), ms_gw/cc4101/logs_db 全 Up.
- env 无新漂移 (UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / MIN_OUTBOUND=0 /
  KEY_COOLDOWN_S=25 / NVU_MS_FALLBACK_FAIL_THRESHOLD=5 等, 与 R1914 一致).
- StartedAt 仍 2026-07-19T09:38:26Z (R1913 阶段1.5 restart, 本轮 0 restart).

## 5. 本轮补提交 R1914 (修铁律4 违规) + 本轮 R1916 commit

- 补提交 R1914 未跟踪文件:
  - `rounds/R1914_hm2_cc2_stage1_bugA_archive_nop.md` (R1914 轮文件)
  - `deploy_artifacts/R1914_stage1_bugA_chain_skip_pexec2/` (3 份 upstream.py 快照:
    当前生效 / pre_stage1=bak.R1911 / after_R1911_stage1_only=bak.R1913)
- 本轮新增 `rounds/R1916_hm2_cc2_stage1_postlive_nop_r1914_commit.md` (本文件).
- 一起 commit + push origin/main.

## 6. 结论 + 给下一轮 / 监督者

- **STAGE1(BUG-A) 已 in-vivo 落地生效** (前 session R1911+R1913 改 + 17:38 restart),
  本轮巡检 restart 后 25min: SR 96.2% 无退化, fallback 2 全 75s SKIP-CIRCUIT 0 真中断,
  breaker CLOSED 吸收, bug8 0, 链路稳.
- **本轮补提交 R1914** (修复前 session 铁律4 违规: 改源码+restart 但没 commit+push+归档).
- **STATE.md 纠偏**: 把过期的 "StartedAt 21:26:29Z / cc2 上一轮 R1909" 改成实际
  "StartedAt 09:38:26Z / cc2 上一轮 R1914 STAGE1 已生效". 本轮 STATE.md 覆写为 R1916 基线.
- **stage1.5 实战验证待续**: restart 后 chain 全成功, NV-GLM52-CHAIN-SKIP-PEXEC2 0 产生.
  下一轮继续观测, 等 chain 失败事件 (NVCF 上游抖动时) 验证 "fallback 请求 240s → ~120s
  且无新真中断".
- **下一步优先级** (监督者方向, 沿用 R1914):
  - 阶段2 (BUG-B abs_cap 允许 ms 重放): 需实测 abs_cap 触发点 content_chars 分布定阈值.
    restart 后 25min abs_cap 502 仅 1 条 (193s), 数据偏少, 先观测积累 + 等 STAGE1 触发样本.
  - 阶段3 (breaker NVU_MS_FALLBACK_FAIL_THRESHOLD 5→3): 当前 5, breaker OPEN 0 连续 14+ 轮,
    非紧迫, 在阶段2 后推.
- **BUG-C 更正供监督者复核**: 监督者巡视说 "今日 0 条 NV-TIER-BUDGET", 实测 24h 132 条
  (00:02/00:12/00:16 等都有 budget break 触发). budget break 在工作不是绕过, 监督者
  "0 条" 判断可能是窗口不同. 请监督者复核是否需重新评估 BUG-C 结论.
- 沿用铁律: 只改 HM2, 不碰 ms_gw (40007 重启窗口热备), 不碰 HM1. 改 .py 必须 restart.
