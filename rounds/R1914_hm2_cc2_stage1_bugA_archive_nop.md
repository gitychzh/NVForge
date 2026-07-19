# R1914 (HM2 cc2) — 补 commit BUG-A stage1+1.5 归档 + 验证已落地待实战触发

> 时间: 2026-07-19T17:50Z 拉取 (本 session, 北京 17:38 restart 后约 12min).
> git pull "Already up to date". 仓库最新轮号 R1913 (peer HM2→HM1, commit 03d3e17).
> cc2 上一轮 R1910 (commit 6d0be51, NOP 巡检 R61). peer 抢号 R1911-R1913 全 HM2→HM1.

## 0. 本轮性质: 补 commit + 归档 + 验证 (非新代码改动, 非 restart)

本轮 **0 代码改动 0 restart**。理由: 监督者 2026-07-19 16:00 巡视定位的 BUG-A
(mode chain 失败后落 `_try_tier_keys` 第二轮全 key pexec, budget 双吃, 单请求烧 ~240s
才走 ms) 的 stage1 修复 **已被前 session 落地**:
- `/opt/cc-infra/proxy/nv-gw/gateway/upstream.py.bak.R1911` mtime = 2026-07-19 17:11:23 (+08)
  → R1911 阶段1 (改 log 字符串 + 注释, 但**漏设 `_chain_failed=True`, 残废**).
- `upstream.py.bak.R1913` mtime = 17:35:09 → R1913 阶段1.5 补全 (加 `_chain_failed=True`
  @1579 + 1650 行 `if _chain_failed:` 构造 empty all_keys_exhausted tier_result 跳过
  `_try_tier_keys` 第二轮, log `NV-GLM52-CHAIN-SKIP-PEXEC2`).
- `upstream.py` 当前 mtime = 17:37:36, 容器 pyc mtime = 17:38, nv_gw StartedAt =
  **2026-07-19T09:38:26Z** = 北京 17:38:26 → restart 在 R1913 阶段1.5 写盘后 ~1min, 跑新字节码.

但**前 session 违反铁律4**: 改了 `/opt/cc-infra` 源码 + restart nv_gw, **没写 round 文件**
(仓库无 R1911/R1913_hm2_cc2_*.md, git log 无 `STAGE1_CHAIN_FAIL` 字符串 commit) 也**没归档**
源码进 `deploy_artifacts/`. 本轮补这个缺口: 把生效的 upstream.py + R1911 前旧版 + R1911 stage1-only
版三份归档进 `deploy_artifacts/R1914_stage1_bugA_chain_skip_pexec2/`, commit + push.

## 1. 数据 (改前必有数据)

### 30min nv_gw request 层 (17:20-17:50Z)
- SR = 55/56 = **98.2%** (200:55 / 502:1). vs R1910 90.2% → R1914 98.2%, 抖动区间上沿,
  链路极稳. 唯一 502 = `stream_first_byte_timeout` (1×, NVCF 上游侧首字节空转, 非新可配置类).
- tier 30min: pexec_success 39 / pexec_empty_200 2. **500_nv_error 0, zombie 0, SSLEOFError 0,
  timeout 0** — 全干净窗口, R1908/R1909 持续的 dsv4p_nv function 74f02205 出口侧问题本轮消失.

### 2h 长尾分布 (BUG-A 验证基线)
- 18 个请求 **>=240s, 全 `ok=18 fb=18`** = 走 ms_gw 兜回成功, 烧 240s+ (BUG-A 目标人群).
- abs_cap 502 = 2 条 (`a56a3a69` 168s, `057cbe88` 152s, `fallback_actually_attempted=t` 但 fb=f)
  → BUG-B 候选, 阶段2 处理, 本轮不动.
- all_tiers_exhausted 502 = 5 条 (dsv4p_nv function 74f02205 egress 空, 出口侧整体不可达,
  操作侧非旋钮可解, 连续多轮已记录).
- zombie 502 = 9 条 (glm5_2_nv 134.195.101.0/24 出口 IP 段单点续, 连续 5 轮已记录).
- chain 失败事件 2h: `NV-GLM52-CHAIN-FALLBACK` 18 次, 但**全部 log 内容是老字符串**
  `"falling back to R838b/R572/pexec"` (R1911 前旧版) → **17:38 restart 前的事件, 跑旧字节码**.
- chain 失败事件 since restart (17:38+10min): **0 条** `NV-GLM52-CHAIN-FALLBACK`,
  0 条 `STAGE1_CHAIN_FAIL`, 0 条 `NV-GLM52-CHAIN-SKIP-PEXEC2` → **restart 后 chain 全成功,
  stage1.5 跳过路径未被实战触发, 无法本轮验证真省 ~120s**.

### fallback 层 (cc4101 30min)
- 4 FALLBACK-OK, 全 75s SKIP-CIRCUIT (primary timeout 75042-120064ms, cc4101 bug3 preempt,
  NOT counted, 非 nv_gw 旋钮可解). 0 真中断 (全被 ms_gw 兜住). 用户诉求 "可以报错但不能让
  cc2 中断" 仍达成.

### breaker / bug8 / msfb 层
- breaker NV-ANTH-BREAKER-FAIL since restart **0** (chain 全成功, 无失败累积).
  breaker OPEN 0 连续 14+ 轮 (R1910 基线延续).
- bug8 DOWNGRADE 0 触发 (连续 57 轮根除停巡).
- NV-CAP-RESET-MSFB since restart 0 (链路干净).

## 2. BUG-A stage1+1.5 已落地实证 (源码 + 容器字节码一致)

### 宿主 vs 容器内 upstream.py 1580 行内容对比 (确认跑新字节码)
- 宿主 `/opt/cc-infra/proxy/nv-gw/gateway/upstream.py:1580`:
  `_log("NV-GLM52-CHAIN-FALLBACK", f"... mode chain all-failed → STAGE1_CHAIN_FAIL skip pexec 2nd round, mark all_keys_exhausted")`
- 容器 `docker exec nv_gw sed -n '1580p' /app/gateway/upstream.py`: **完全一致**.
- 注: 1580 行新 log 字符串 ≠ 日志里看到的 `"falling back to R838b/R572/pexec"` (老字符串).
  日志老字符串全部出现在 17:38 restart **前**, restart 后 0 条 chain 失败 → 无新 log 产生,
  不矛盾, 确认容器跑新字节码 (1580 行新字符串在文件里, pyc mtime 17:38 ≈ StartedAt).

### stage1+1.5 改动 diff (pre_stage1 → 当前生效)
两处增量 (vs `upstream.py.pre_stage1` = bak.R1911, = R1911 改前旧版):
1. **1575-1582**: chain 失败分支 log 字符串从 `falling back to R838b/R572/pexec` 改为
   `STAGE1_CHAIN_FAIL skip pexec 2nd round, mark all_keys_exhausted` + 加 `_chain_failed = True`
   (R1911 漏设这一行, R1913 补).
2. **1643-1663**: 在 `_try_tier_keys(...)` 调用前加 `if _chain_failed:` 分支 → 构造 empty
   `UpstreamResult` (success=False, all_keys_exhausted=True, key_cycle_attempts=copy) 跳过
   `_try_tier_keys` 第二轮, log `NV-GLM52-CHAIN-SKIP-PEXEC2` (省 ~120s/chain-failed req),
   走同一 all_keys_exhausted 失败路径触发 handlers ms_fb.

详见 `deploy_artifacts/R1914_stage1_bugA_chain_skip_pexec2/` 三份 upstream.py 快照.

### NV_GLM52_MODE_CHAIN env (确认 chain branch 真进)
- `NV_GLM52_MODE_CHAIN=integrate_us_rr,pexec_us_rr` (env 已设) → 1560 行条件满足, branch 进.
- since restart 15+ 条 `NV-GLM52-CHAIN` start log (各 key RR 起步) → chain 在用, 只是都成功.

## 3. 决策: 本轮 0 代码改动 0 restart (stage1+1.5 已落地, 不重复改)

介入四条:
1. **SR 98.2% 上沿常态, 未达介入线** (连续 3+ 轮跌破 80%).
2. **stage1+1.5 已落地生效** (源码 + 容器字节码一致 + StartedAt 17:38 在 R1913 写盘后),
   不需再改/再 restart. 本轮补的是 commit + 归档缺口 (铁律4).
3. **实战验证待续**: restart 后 chain 全成功, stage1.5 跳过路径 0 触发 → 无法本轮实证
   "fallback 请求从 240s → ~120s". 需等下一个 chain 失败事件 (NVCF 上游抖动时) 自然触发,
   届时看 `NV-GLM52-CHAIN-SKIP-PEXEC2` log 产生 + 该请求端到端耗时是否 ~120s (vs 旧 240s+).
4. **BUG-B (abs_cap 允许 ms 重放) / 阶段3 (breaker 5→3)** 不在本轮, 单独轮次推.

## 4. 验证 (NOP, 0 restart)
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker ps: nv_gw "Up 14 minutes" (17:38 restart 后稳定, 无重启循环).
- env 无新漂移 (NVU_MS_FALLBACK_FAIL_THRESHOLD=5 是 env 覆盖 config 默认 15, 已存在, R1909 STATE
  没记录这个是 grep pattern 没带, 非 R1914 引入).
- StartedAt 仍 2026-07-19T09:38:26Z (R1913 阶段1.5 restart, 本轮 0 restart).

## 5. commit + push + 归档

- 归档: `deploy_artifacts/R1914_stage1_bugA_chain_skip_pexec2/`:
  - `upstream.py` (当前生效, 含 stage1+1.5)
  - `upstream.py.pre_stage1` (= bak.R1911, R1911 改前旧版, chain 失败落 pexec 老逻辑)
  - `upstream.py.after_R1911_stage1_only` (= bak.R1913, R1911 残废版, 只改 log 字符串没设 _chain_failed)
- 本轮 commit + push origin/main.

## 6. 结论 + 给下一轮 / 监督者

- **BUG-A stage1+1.5 已 in-vivo 落地** (前 session R1911+R1913 改 + restart), 本轮补 commit +
  归档 (修复铁律4 违规). 容器跑新字节码 (1580 行新 log 字符串在文件, pyc mtime ≈ StartedAt).
- **链路极稳**: SR 98.2%, fallback 4 全 75s SKIP-CIRCUIT 0 真中断, breaker 0, bug8 0, tier 全干净.
- **stage1.5 实战验证待续**: restart 后 chain 全成功, `NV-GLM52-CHAIN-SKIP-PEXEC2` 0 产生.
  下一轮继续观测, 等 chain 失败事件验证 "fallback 请求 240s → ~120s".
- **下一步优先级** (监督者方向):
  - 阶段2 (BUG-B abs_cap 允许 ms 重放): 需实测 abs_cap 触发点 content_chars 分布定阈值.
    当前 2h abs_cap 502 仅 2 条 (a56a3a69 168s / 057cbe88 152s, fallback_actually_attempted=t),
    数据偏少, 先观测积累.
  - 阶段3 (breaker NVU_MS_FALLBACK_FAIL_THRESHOLD 5→3): 当前 5, breaker OPEN 0 连续 14+ 轮,
    非紧迫, 可在阶段2 后推.
- 沿用铁律: 只改 HM2, 不碰 ms_gw (40007 重启窗口热备), 不碰 HM1. 改 .py 必须 restart.
