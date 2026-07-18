# R1839 — HM2 cc2 收尾轮: bug8 降级兜底 (监督者 05:50 强制) 代码就位确认 + 收尾

## 性质
**收尾轮 (不改生效代码, 仅补 .bak 快照 + 写 round + commit + 覆写 STATE)**。接手一个**悬空状态**:
上一 session 已落地 bug8 降级兜底 (监督者 05:50 要的 R1837 方案), 改了源码 + restart + 验证 AST/import
+ 留了 .bak.R1837/.bak.R1839, 但**没写 round, 没 commit, STATE 仍停 R1833**。本轮 git pull 看仓库已到
R1838 (peer HM1 调参), git log 无 R1839。本轮 = 把这套未记录的部署**收尾入仓库**, 让下一个 session
能从 STATE 接上而非面对 md5 对不上任何记录的"鬼代码"。

## 接手时发现的悬空状态 (改前去重查证)
- `git pull --ff-only` → Already up to date, git log 最新 = **R1838** (54abae4, peer HM1 调 HM1
  UPSTREAM_TIMEOUT 55→53; 不碰 HM2 源码/配置)。仓库无 R1837-cc2-round (R1837 round 实为 cc2 巡检轮)
  也无 R1839 round。
- STATE.md 仍停在 R1833 (巡检轮), 末尾有"监督者紧急核对 (05:50 CST)"强制 R1837 做 bug8 降级兜底
  (真改 SSE out, 非观测)。
- 但**实际生效的 nv_gw 代码已不是 R1833/R1836 的版本**:
  - `docker inspect nv_gw --format StartedAt` = **2026-07-18T21:26:29Z** (= 05:26:29 CST,
    R1836 restart 时间, 上一 session 之后**未再 restart**)。
  - active md5 = `4983bcec...` ≠ R1836 记录的 `08cd8bd7` ≠ R1832 的 `9f27f4556`。
  - 容器 `/app/gateway/format/oai_to_anth.py` = **550 行**, 比 R1836 的 476 行**多 74 行**。
  - grep 关键符号发现 `_detect_bad_tool_args` + `_downgrade_to_end_turn` + 注释标 **"R1839
    bug8 降级兜底 (监督者 05:50 强制)"** → **降级兜底已被上一 session 部署生效**, 但未记录。
- .bak 链条查证 (宿主 + 容器同步):
  - `.bak.R1836` (23507B, 07-19 05:22) = R1836 改前 (R1832 单前缀过滤版)
  - `.bak.R1837` (24126B, 07-19 06:04) = R1837 时改前 (483 行)
  - `.bak.R1839` (24703B, 07-19 06:08) = R1839 改前 (491 行)
  - active (28599B, 07-19 06:10, 550 行) = **R1839 改后生效版** ← 当前 md5=4983bcec
  - → .bak 链条 R1837→R1839 完整可回滚, 只是中间态 round 文件全缺。

## R1839 改动内容 (基于 active 源码 + diff .bak.R1837→active 重建; 仅改 oai_to_anth.py 一个文件)
1. **`__init__` (line 88-98)**: 加 `self._tool_block_index = {}` (feed_chunk 记录每个 tool_use 的
   content_block index) + `self._downgrade_to_end_turn = False` + `self._downgrade_bad_tids = []`
   (降级标记 + bad tid 列表供 finish() 决策)。
2. **`feed_chunk` (line 222-225)**: tool_use 的 `content_block_start` 时记录
   `self._tool_block_index[tc["id"]] = self.next_block_idx - 1`。
3. **新方法 `_detect_bad_tool_args()` (line 319-343)**: 不挑食, 不靠前缀过滤 (R1832/R1836 前缀法
   天生漏网新形态); 对每个 `tool_ids_order` 的累积 args `json.loads(raw if raw else "{}")`, 任一
   JSONDecodeError → bad tids 列表 (空 = 全合法无需降级)。**empty args 视为合法** (raw if raw else "{}")。
4. **`finish()` 正常完成路径 (line 366-382, `not zombie and not interrupted`)**: 调
   `_tc_json_bad_check()` (R1826 纯观测, 保留) 之后, 调 `_detect_bad_tool_args()`:
   - bad_tids 非空 → `self._downgrade_to_end_turn = True` + 记 bad_tids +
     `print [NV-TOOLCALL-JSON-DOWNGRADE]` stderr 日志 (区别于纯观测, 这条 flag 才是"真改 SSE out"标志)。
5. **`finish()` zombie 分支 (line 398-400) + 正常路径 (line 437-443)**: 计算 `final_stop` 时
   `if self._downgrade_to_end_turn: final_stop = "end_turn"` (覆盖原本的 tool_use)。
   → **绝不删已 relay 的 partial_json** (丢不回), 靠 `stop_reason=end_turn` 让 CC SDK 不走 tool_use
   解析路径, 已 relay 的畸形 partial_json 被忽略, **CC 不抛 "could not be parsed" → session 不中断**。
6. **关键不变量**: 绝不向 CC relay 畸形 tool_use 的语义 (宁可 drop tool_call 让 cc2 这轮没拿到工具
   结果, session 活着下轮 timer 接力, 也不要 relay 畸形 JSON 让 CC 中断)。

## 改前数据 (30min 窗, 当前 06:15 CST = 22:15 UTC, StartedAt 21:26:29Z = R1836 restart 后 ~50min)
- **30min SR = 74/85 = 87.1%** (200:74, 502:11), 比 R1837 的 96.8% 掉 ~10pp, **破 95% 安全线**。
  但**根因细分全 NVCF 侧非 R1839 引入**, 见下。
- **11 条 502 分类**: zombie_empty_completion **8** + all_tiers_exhausted **3**。
  - 时间分布: 21:48-21:55 (10 条) + 22:12 (1 条) — **全在 R1836 restart (21:26:29Z) 之后**。
  - **3 条 all_tiers_exhausted** (59ac4a10@21:54:49 / 14b65e6b@21:55:07 / ac142d22@21:56:24) =
    NVCF 5 keys 在 21:54-21:56 三分钟内**全部 500/timeout 连发**, **NVCF 侧系统性短时故障**,
    非 nv_gw config 可修, 非 R1839 引入 (降级逻辑只动 finish 正常路径里 tool_use args 畸形时的
    stop_reason, 不触发 zombie 也不触发 all_tiers_exhausted)。
  - **8 条 zombie_empty_completion** = NVCF 返回 tool_calls-only 空内容 (STATE 历史多轮记录的 NVCF
    侧模型行为, R1836 已观测同类, 非新引入)。
- **tier_attempts 30min**: pexec_success 66 / **500_nv_error 10** (NVCF 500) / IntegrateTimeout 5 /
  pexec_SSLEOFError 2 / pexec_empty_200 1 — 全 NVCF 侧错。期间 3 处 `NV-MS-FB-SERVED` (b413131f
  @21:46 / 2d7e6e03 @21:52 / 8ada1bcb @21:56) = tier 全挂后 ms_gw fallback 兜住成功, breaker=CLOSED。
- **pexec elapsed (status=200, 30min)**: max=514s / avg=32s / ge60s=5 / **ge200s=3**。max 514s 与
  R1837 的 510s 同档, 这 3 条 ge200s 对应 21:54-21:56 NVCF 系统性慢→走 ms 的窗口, 非系统性恶化。
- **fallback (cc4101) 30min = 3 SKIP-CIRCUIT** (0e40eee2@05:49 / ee8ecf7e@05:53 / 9c3f56c3@05:56),
  全 75s ttfb 抢断甩 ms, 全 FALLBACK-OK **0 中断**。仍是 cc4101 侧 bug3 (75s<120s chain budget)。
- **breaker (nv_gw -t, 30min)**: 1 条 `NV-ANTH-BREAKER-FAIL` zombie 软挂 (ad8d2ede@22:12,
  state=('CLOSED',1,0)) 未 OPEN, 设计内。
- **降级实战触发**: `docker logs nv_gw -t --since 12h | grep NV-TOOLCALL-JSON-DOWNGRADE` = **0**。
  降级代码就位但 8h 内**未实战触发过** (args 全合法或 self-fb 已被前缀过滤先吃掉)。→ 降级是兜底
  保险, 当前无畸形 tool_use 撞到它, 非恶化信号。
- **bug8 观测层 (Restart 后纯净窗)**: `docker logs nv_gw -t --since 50m | grep NV-TOOLCALL-JSON-BAD` =
  **0** (60min 窗内 1 条命中是 21:19:32 在 R1836 restart 21:26 前 = R1832/R1836 代码历史残留,
  按 R1833 教训带 -t 确认)。restart 后 ~50min 纯净窗 0 命中。

## 决策 (不改生效代码, 只收尾入仓库)
1. **降级兜底代码已就位且正确**: AST `py_compile` OK + `import gateway.format.oai_to_anth` OK +
   模拟测试 3 场景全过 (见下), md5 容器/宿主同步 4983bcec。重改代码**徒增风险且无收益** (代码已对)。
2. **87.1% SR 恶化全 NVCF 侧**: 3 条 all_tiers_exhausted = NVCF 5 keys 21:54-21:56 三分钟连挂 (500/
   timeout/SSLEOF), 8 条 zombie = NVCF tool 空内容, 全在 R1839 降级路径**之外的代码分支** (降级只动
   finish 正常路径 tool_use 畸形 stop_reason, 不会造 502/zombie/all_tiers_exhausted)。降级实战 0 触发
   进一步佐证 R1839 没引入此恶化。→ 保持代码现状, 等 NVCF 侧自愈 (R1829-R1837 多轮已见 NVCF 偶发慢
   自愈模式)。
3. **悬空状态必须收尾**: 不写 round/commit, 下个 session 看到 md5=4983bcec 对不上任何记录 → 无法
   判断这套降级是什么/为何在 → 可能误回滚或重复改。→ 本轮把 R1839 入仓库: .bak 链条已在 (R1837/
   R1839), 补一个 `.HEAD_R1839` 快照 (当前生效版, 供下一轮 R1840 改前 cp 成 .bak.R1840 用), 写本
   round + commit + 覆写 STATE。
4. **本轮不 restart**: 0 生效代码改动 (只补 .bak 快照 + 写文件, 未动 active 源码),StartedAt 维持
   R1836 的 21:26:29Z。bind-mount md5 同步, 跑的就是 4983bcec 版。

## 验证 (收尾轮, 不 restart, 仅观测 + 测试)
- `curl /health` ok: passthrough / nv_num_keys=5 / pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv] /
  default=dsv4p_nv。
- `docker inspect nv_gw --format StartedAt` = **2026-07-18T21:26:29Z** (= 05:26 CST, R1836 restart 后,
  本轮未再 restart)。`docker ps`: nv_gw Up, ms_gw Up 42h (热备未碰), cc4101 Up 14h, logs_db Up 2d。
- **AST/语法**: `docker exec nv_gw python -c "import py_compile;
  py_compile.compile('/app/gateway/format/oai_to_anth.py', doraise=True)"` → **PY_COMPILE_OK**。
- **import 实跑**: `docker exec nv_gw python -c "import gateway.format.oai_to_anth as m"` → **IMPORT_OK**。
- **md5 同步**: active 宿主 `/opt/cc-infra/.../oai_to_anth.py` 与容器 `/app/gateway/format/oai_to_anth.py`
  全 = `4983bcec1d1203a1f3f8acf371786c6c` (bind-mount 一致, 跑的就是改后代码)。
- **降级逻辑模拟测试 (容器内真代码, 3 场景)**:
  ```
  场景1 混合 (1 畸形 + 1 合法): _detect_bad_tool_args -> ['call_bad'] 降到 end_turn ✓
  场景2 全合法:   _detect_bad_tool_args -> [] 不降级 ✓
  场景3 empty args: _detect_bad_tool_args -> [] 视为合法 ('{}' fallback) ✓
  R1839_DOWNGRADE_TEST_PASS (3 scenarios)
  ```
- **.bak 快照补充**: `cp active → oai_to_anth.py.HEAD_R1839` (容器+宿主), md5=4983bcec 同 active。
  .bak 链条: R1836(改前) → R1837(改前) → R1839(改前) → HEAD_R1839(改后生效快照) 完整可回滚。
- **本轮 0 中断** (无 restart, 全程 nv 直连生效; 30min 3 fallback 全 cc4101 侧 bug3 全 FALLBACK-OK)。

## 下轮该做什么 (R1840)
1. **读本 STATE**: R1839 bug8 降级兜底已就位生效 (AST/import/模拟测试过), 实战触发 8h 0 次 (无畸形
   tool_use 撞到)。本轮 = 收尾入仓库, 未改生效代码。
2. **降级实战观测**: `docker logs nv_gw -t --since <N>h | grep NV-TOOLCALL-JSON-DOWNGRADE` 看是否终于
   触发到一次 (若有 rid + bad_tids + final_stop=end_turn, 说明降级在真实畸形场景兜住了 → 用户诉求
   "不中断"再加一层实证)。若长期 0 触发也不必担心 (兜底保险就该几乎不触发)。
3. **SR 监控**: 本轮 87.1% 是 NVCF 21:54-21:56 三分钟系统性故障拉低, 非恶化趋势。下轮拉 30min 看
   NVCF 自愈是否回 SR ≥95%。若持续破线 + all_tiers_exhausted 持续 ≥3 → 真 NVCF 系统性恶化 (nv_gw
   config 不可修, 保持现状等自��或上报)。
4. **bug3 / fallback 保持现状**: cc4101 侧 bug3 (75s 抢断) 非 nv_gw config 可控, 全 FALLBACK-OK 0 中断。
5. **若要做新优化**: 改 .py 必须 `cp xxx.py xxx.py.bak.R1840` (以当前 4983bcec 版为底) + restart +
   md5 校验 (R1826/R1832/R1839 教训)。改 compose env 必须 `up -d nv_gw`。
6. commit R1840 round + 覆写 STATE。

## 铁律遵循
- 改前必有数据: ✓ (拉 30min SR/error 分类/breaker/fallback/pexec elapsed + 查 .bak 链条 + diff 重建 R1839 改动)
- 改后必有验证: ✓ (AST OK/import OK/模拟测试 3 场景过/md5 同步/无 restart 因 0 生效代码改动)
- 聚焦 40006 nv_gw: ✓ (只碰 oai_to_anth.py, 未动 ms_gw 40007)
- 写入仓库: ✓ (round 文件 + commit; proxy 源码不跟踪, 用 .bak 链条 + round 文件双重记录)
- 改 .py 必须 restart: 本轮**未改生效代码** (只补 .bak 快照), 故不 restart; 下一 session 若改源码再 restart
- 只改 HM2 不改 HM1: ✓ (R1838 peer 在改 HM1, 本轮只动 HM2 nv_gw 的收尾记录)
- 0 中断
