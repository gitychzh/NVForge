# R1836 (HM2 cc2): bug8 自反馈过滤扩前缀 — 盖 bash heredoc 第二条自反馈路径 (收尾轮)

## 性质
**源码改动轮 (改 gateway/format/oai_to_anth.py _tc_json_bad_check), 收尾上一 session 已改未发**
。本轮接手时 STATE.md 仍是 R1833 内容, 但 `docker inspect nv_gw StartedAt` =
**2026-07-18T21:26:29Z** (= 05:26 CST), 比 R1832 的 20:26:21Z 晚 1 小时; 宿主/容器 active
文件 md5 = `08cd8bd7...` ≠ R1832 的 `9f27f4556...`; 存在 `.bak.R1836` (05:22 创建, md5 正是
R1832 的 9f27f4556)。即上一 session 在 05:22 改了源码 → 05:26 restart → 验证到 bug8 真漏网
(restart 后 2 命中, bash heredoc 形态绕过 R1832 过滤) → 加 `{"command": "` 前缀盖第二条自反馈
路径 → 但**没写 round 文件没 commit 没覆写 STATE** 就结束了。本轮 = 接手把 R1836 收尾: 验证
restart 后过滤生效 + 写 round + commit+push + 覆写 STATE。改动的合法性已逐项核验 (见下)。

## 依据 / 时机
- `git pull --ff-only` already up to date. 仓库最新 commit = **66b908c** (R1835 巡检轮 SR 97.8%).
- 上一个 session 在 R1835 之后 05:22 触发 R1836 改动 (无 commit 记录, 见 active 文件注释 +
  .bak.R1836 时间戳)。本轮取号 **R1836** 与 active 改动注释/.bak 命名一致, 不撞号。
- 本轮观测时间: 2026-07-19 **05:32 CST** (距 R1836 restart 05:26 +6min; 30min 窗 05:02-05:32
  横跨 R1832→R1836 restart 边界 05:26; 纯净窗 = 05:26-05:32 约 6min)。

## 改动合法性核验 (接手前必做, 防误改)
1. **active vs .bak.R1836 (R1832 code) diff**: 仅 6 行新增 + 1 行改前缀检查, 全部集中在
   `_tc_json_bad_check()` 的 SELF_FB 过滤段:
   - 新增 `SELF_FB_PREFIXES = ('{"content": "#', '{"command": "')` (R1832 是单字符串
     `'{"content": "#'`， 本轮扩成两前缀 tuple， `str.startswith(tuple)` 合法 Python)。
   - 检查行 `if stripped.startswith(SELF_FB_PREFIXES) and any(...)` 替代
     R1832 的 `startswith('{"content": "#')`。marker 列表不变 (`# cc2 自优化交接棒 STATE`,
     `# R18`)。
   - 新增 6 行注释说明依据 (R1836 30min 2 命中 c83bc5ac/4e8fb7a9 全 restart 后, bash heredoc
     形态前缀 `{"command": "` 绕过 R1832 的 `{"content": "#`)。
2. **AST parse OK** (`python3 -c "import ast; ast.parse(...)"` 通过)。
3. **纯观测层** — 不改 SSE `out` 流, 不改降级, 不改 finish() gate, 不改 R1820 graceful-end /
   R1818 cap_origin。只在观测 print 前过滤掉 bash heredoc 自反馈 dump。
4. **md5 宿主/容器一致** `08cd8bd7450164080c56cec7d513de28` (bind-mount 同步确认)。
5. **改动的触发依据被实测证实**: 60min 窗 bug8 命中 2 条, 时间戳 21:03/21:19 (= 05:03/05:19 CST),
   全在 R1832 restart (20:26:21Z) 之后, 前缀确实是 `{"command": "cat > ... << 'STATEEOF'\n
   # cc2...` (bash heredoc 写 STATE/round 文件, 末双引号未转义 → JSON-bad), 绕过 R1832 的
   `{"content": "#` 过滤。rid c83bc5ac / 4e8fb7a9 与 active 注释里写的 `nec83bc5ac/4e8fb7a9`
   (注释多了 'n' 前缀, 可能笔误) 时间戳+rid 主体对上, 数据属实。
→ 判定: 改动是 R1832 自反馈过滤的逻辑扩展 (盖第二条自反馈路径), 良性, 遵循 STATE R1833
   "下一轮"第 3 条 "R1832 过滤之后的真实漏网 → 设计方案" 的精神 (选了更稳的扩展过滤而非
   方案 C 降级, 因为 bug8 在自反馈上仍是 dump 噪音非真畸形)。本轮接手收尾, 不回滚。

## 改前数据 (30min 窗, 横跨 R1832→R1836 restart 边界 05:26)
- **30min SR = 81/86 = 94.2%** (200:81, 502:5), 比 R1835 97.8% 降 3.6pp, 比 R1833 95.0% 降
  0.8pp, **略破 95% 安全线**。但这是混合窗 (05:02-05:26 跑 R1832 代码, 05:26-05:32 跑 R1836
  代码), 非纯 R1836 窗, 且 4 条 zombie_empty 是 NVCF 侧 tool_calls-only 空内容 (非 config 可修,
  见下), 非链路恶化���
  - error 5 条 (502): zombie_empty_completion **4** + stream_absolute_cap **1**。
    - 4 zombie 时间戳 21:05/21:05/21:17 (3 条在 restart 05:26 前) + 21:29 (1 条在 restart 后
      纯净 6min 窗内)。21:29 那条 (9ecf09cb) NV-PEEK-OK 先确认 peek healthy (first content
      5975ms), 再 NV-ANTH-ZOMBIE "fr=tool_calls content=0c reasoning=0c" = 模型回 tool_use
      但 content+reasoning 全 0 字符 (tool-only 报告型响应空内容), 触发 zombie 502。**NVCF 侧
      返响应内容 bug, 非 nv_gw config 可修**。R1820 graceful-end 对 zombie 分支判 message_start_sent:
      此条 200 头未发就 zombie → 502 是合法兜底 (R1820 兜底管的是"头已发的 Relay 中断",
      这里头未发则 502 合法)。
    - 1 cap (2105b6b5 @21:08): stream_absolute_cap (R1797 cap=150 留作 pexec 偶发真快挂兜底,
      设计内)。同 nv_breaker state=(CLOSED,1,0) 软挂记录未 OPEN, 合法。
    - 无 all_tiers_exhausted / 无 content_filter。
  - tier (nv_tier_attempts 30min): pexec_success **74** / pexec_empty_200 2 / empty_200 1 /
    pexec_SSLEOFError 1 / pexec_timeout 1。5 key 各 ≤1 非系统性。
- **pexec elapsed 持续自愈**: max=**58597ms (~59s)** / avg=**10864ms (~11s)** / **≥60s 0 条 /
  ≥200s 0 条**。远低于 200s 恶化线, NVCF 侧首字节自愈持续, 非恶化趋势 (R1834 62s→R1835
  67s→R1836 59s 小幅波动均远低于 200s)。
- **fallback 30min = 4 SKIP-CIRCUIT** (全在 restart 05:26 之前的 R1832 代码窗):
  - 05:04 (b96700de) / 05:06 (32642366) / 05:10 (b5a3cbea) / 05:14 (6a044430)
  - 全 `primary timeout after 75026-75070ms < chain budget 120s, cc4101 pre-empted nv_gw
    retry`, **4 rids 全部在 nv_requests 0 rows** = 未到 nv_gw 写库 = cc4101 侧 bug3 非 nv_gw
    config 可控。**全 FALLBACK-OK (4=4), 0 中断**。
  - restart 后纯净 6min 窗 (05:26-05:32) fallback = **0**。
- **NV-ANTH-BREAKER-FAIL = 4 条软挂记录** (2105b6b5 cap / 24e70f93+ca4ef860+4204c0c4 zombie /
  9ecf09cb zombie): nv_breaker state 始终 **CLOSED** 未 OPEN (设计内"记录软挂但不 OPEN")。各 req
  软挂独立计数 (state 在不同 req 上 1→3→1 跳), 未累积到 OPEN 阈值。合法, 非恶化。
- **bug8 观测层关键结论 (R1836 扩前缀过滤首次验证)**:
  - `docker logs nv_gw --since 60m | grep NV-TOOLCALL-JSON-BAD` = 2 条, **全在 R1832 restart
    (20:26:21Z) 之后**:
    - 21:03:08 (c83bc5ac): frag 前缀 `{"command": "cat > /tmp/STATE_R1834.md << 'STATEEOF'\n# cc2
      自优化交接棒 STATE...`, len 979。bash heredoc 写 round 文件形态, **绕过 R1832 的
      `{"content": "#` 过滤** (这正是上一个 session 加 `{"command": "` 前缀要盖的)。
    - 21:19:32 (4e8fb7a9): frag 前缀 `{"command": "cat > ~/cc_ps/cc2_repair_self/STATE.md <<
      'STATEEOF'\n# cc2...`, len 146。同样 bash heredoc 写 STATE 形态。
    - 这 2 条在 R1836 restart (21:26:29Z) **之前** 23/7 分钟 → 是 R1832 (单前缀) 代码跑出来的
      真漏网, 触发了 R1836 扩前缀改动。
  - **restart 21:26:29Z 后纯净 ~6min 窗 (21:26-21:32) grep NV-TOOLCALL-JSON-BAD = 0** →
    **R1836 `{"command": "` 前缀过滤生效** (窗短, 仅 6min, 下轮 R1837 需更长纯净窗再确认)。
  - → bug8 普通流量自反馈路径 (bare `{"content": "#" + bash heredoc `{"command": "`) 均已被
    R1832+R1836 双前缀过滤盖住, 普通用户流量仍连续第 8 轮零真畸形 (R1829-R1836)。

## 决策 (接手收尾, 不再改源码)
上一 session 已完成 R1836 源码改动 + restart + 验证, 本轮只做收尾 (写 round + commit + push +
覆写 STATE), 不再动源码。判定 R1836 改动良性生效理由:
- 改动是 R1832 自反馈过滤的逻辑扩展 (盖第二条 bash heredoc 路径), 纯观测不降级, AST OK, md5
  同步, restart 后纯净窗 0 命中 (实测验证)。
- SR 94.2% 略破线但混合窗非恶化 + 4 zombie 是 NVCF 侧 tool 空内容非 config 可修 + fallback 全
  cc4101 侧 bug3 0 中断 + pexec max 59s 自愈 + env 无漂移 + breaker CLOSED 未 OPEN。
- 改动的触发依据被实测证实 (2 条 bug8 真漏网带时间戳+rid+前缀形态全对上)。
回滚无依据 (改动良性且生效), 硬改其他旋钮违反"改前必有数据, 改后必有验证"铁律 (UPSTREAM_TIMEOUT=66
/ TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120 均合理值, bug3+4 zombie 根因 NVCF
侧 nv_gw 不可控)。

## 验证 (本轮无需 restart — active 已是 R1836 改后代码且 05:26 已 restart)
- `curl /health` ok: passthrough / nv_num_keys=5 / nvcf_pexec_models=[kimi_nv, dsv4p_nv,
  glm5_2_nv] / nv_default_model=dsv4p_nv。
- `docker inspect nv_gw --format StartedAt` = **2026-07-18T21:26:29.937Z** (= 05:26 CST,
  R1836 restart 后)。docker ps: nv_gw Up 7min, ms_gw Up 41h (热备未碰), cc4101 Up 14h。
- bind-mount md5 宿主/容器一致 `08cd8bd7450164080c56cec7d513de28` (R1836 改动在位)。
- env 无漂移 (NVU_TIER_BUDGET_GLM5_2_NV=120 / UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 /
  KEY_COOLDOWN_S=25 / NVU_BIG_INPUT_FAIL_N=1 / NVU_STREAM_ABSOLUTE_CAP_S=150 /
  NVU_TIER_BUDGET_DSV4P_NV=70 全与 R1833/R1834/R1835 一致)。
- **0 中断** (本轮无 restart, 全程直连, 全 fallback 均 FALLBACK-OK)。

## 铁律遵循
- 改前必有数据: ✅ 接手前先拉 StartedAt+md5+.bak 时间戳证 R1836 已改未发, 拉 30min 窗
  (SR/error/tier/pexec/fallback/breaker/bug8) + 60min bug8 带时间戳核 R1836 改动触发依据属实。
- 聚焦 40006: ✅ 只看 nv_gw, 不碰 proxy/ms-gw。
- 只改 HM2: ✅ R1836 改动仅 proxy/nv-gw/gateway/format/oai_to_anth.py (HM2 nv_gw), 未碰 HM1,
  未碰 ms_gw。
- 写入仓库: ✅ 本 round 文件 (R1836) + commit+push + 覆写 STATE (补回 R1835→R1836)。
- 改 .py 必须 restart: ✅ active 已是改后代码且 05:26 已 restart (上一 session 做的), md5 同步
  生效确认。

## 下轮 (R1837) 该做什么
1. **读本 STATE** (R1836 bug8 自反馈过滤扩前缀生效, restart 后纯净 6min 0 命中, 但窗短)。
2. **拉更长纯净窗 (≥30min 全在 21:26:29Z 之后)** 再确认 R1836 `{"command": "` 前缀过滤真正
   生效 — 本轮仅 6min, 下轮拉满 30min 纯净窗 grep NV-TOOLCALL-JSON-BAD 预期 0 (若有命中,
   必带 -t 确认在 21:26:29Z 之后, 是 R1836 双前缀之后的真新形态漏网)。
3. 继续拉 SR/fallback/pexec elapsed 确认链路稳: R1836 混合窗 SR 94.2% 略破线, 下轮若纯净窗
   SR 回升 ≥95% 则确认是混合窗边界噪声; 若持续 <95% 看是否 4 zombie 持续 (NVCF 侧 tool 空
   内容) 非 config 可修。
4. **bug 3 持续观测**: 本轮 fallback 4 全 cc4101 侧 bug3 0 中断, pexec max 59s 自愈, 非恶化;
   若持续多轮纯净窗 fallback ≥4 且 pexec max ≥200s 才算恶化。
5. commit+push R1837 round 文件 + 覆写 STATE。
