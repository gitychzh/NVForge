# R1842 (HM2 cc2): 巡检轮 — bug8 降级兜底持续 0 触发, 链路稳

## 性质
巡检轮 (不改代码不 restart)。R1839 bug8 真降级兜底 in-vivo 生效后第 2 轮持续观测。

## 依据
STATE R1841 "下一轮该做什么": (1) bug8 降级兜底持续观测 (grep NV-TOOLCALL-JSON-DOWNGRADE
有命中=真畸形被兜住, 0 命中=bug8 已稳到不需兜底理想态); (2) bug8 旧观测标记必带 -t 确认
restart 21:26:29Z 之后才算真实漏网; (3) 链路稳巡检 SR≥95%+fallback 低位+pexec max<60s 继续
巡检.

## 改前数据 (30min 窗, 当前 06:33 CST, StartedAt 21:26:29Z = R1836 restart 后)
- **30min SR = 79/81 = 97.5%** (200:79, 502:2). 与 R1841 98.7% (75/76) 基本持平, 远高于
  95% 安全线非边缘抖动. 2 条 502 = 1 zombie_empty_completion (NVCF 侧 tool 空内容) + 1
  all_tiers_exhausted (NVCF 多 key 连挂), **全在降级路径之外分支**, 非 R1839 降级路径问题.
- **pexec elapsed 仍自愈**: max=60561ms (~60.5s) / avg=12392ms (~12.4s) / ≥60s 1 条 / ≥200s 0
  条. 与 R1841 (max 60.5s/avg 12.8s/≥60s 1) 一致, NVCF 侧持续自愈, 远好于 R1831 (max 288s).
- **fallback 30min = 1 SKIP-CIRCUIT + 2 FALLBACK-OK**:
  - 06:29:38 f47a695b: PRIMARY-FAIL 75s timeout → SKIP-CIRCUIT (cc4101 75s ttfb 抢断甩 ms,
    bug3 75s 抢断非 nv_gw config 可控), FALLBACK-OK 6956ms 成功. **0 中断**.
  - 06:21:31 c3eea079: PRIMARY-FAIL 120s timeout → FALLBACK-OK 5342ms 成功 (nv_gw 首字节
    超 chain budget 120s 后合法故障递进, 非中断).
  - 比 R1841 (0 SKIP-CIRCUIT) 多 1 条 bug3, 但 30min 窗内 1 条非系统性, 非恶化 (R1837 阈值:
    持续多轮窗内 ≥4 才算恶化).
- **bug8 降级兜底实战 0 触发** (`docker logs -t --since 120m | grep NV-TOOLCALL-JSON-DOWNGRADE`
  全空): 120min 实战窗内 args 全合法 或 self-fb 已被 R1832/R1836 前缀过滤先吃, 降级路径未
  fire — **"兜底保险就该几乎不触发"的期望持续** (R1839 round 原话). bug8 第 7+ 轮零真畸形.
- **bug8 旧观测标记 restart 后纯净窗 0**: `docker logs -t --since 90m | grep
  NV-TOOLCALL-JSON-BAD` 仅 1 条 (`2026-07-18T21:19:32Z` rid=4e8fb7a9, 内容=STATE.md 长markdown
  自反馈 frag), **在 R1836 restart 21:26:29Z 之前** = R1832 单前缀代码历史残留 docker logs
  滞留. **restart 后纯净窗 grep = 0**.
- **cc2.log "could not be parsed" 中断 = 0** (无此文件或 0 命中).
- **NV-ANTH-BREAKER-FAIL 30min**: 1 条 (06:12:52 ad8d2ede, glm5_2_nv zombie_empty_completion
  软挂), state=('CLOSED', 1, 0) = **CLOSED 未 OPEN**, 1 次累积远未到 OPEN 阈值, 设计内兜底.

## 决策 (不改代码)
当前链路 SR 97.5% (远高于 95% 安全线) + pexec 自愈 (max 60.5s 无 ≥200s) + fallback 低位非
恶化 (1 bug3 75s 抢断 + 1 120s timeout 合法递进, 0 中断) + bug8 降级兜底在位实战 0 触发 +
旧标记 restart 后纯净窗 0 + breaker CLOSED 1 次未 OPEN + env 无漂移 (UPSTREAM_TIMEOUT=66 /
TIER_TIMEOUT_BUDGET_S=180 / KEY_COOLDOWN_S=25 全与 R1833/R1841 快照一致) → **无 nv_gw
config 可改依据**. 硬改违反"改前必有数据, 改后必有验证"铁律 → 巡检轮不动. bug8 R1839 兜底
落地后已连续 2 轮 (R1841+R1842) 0 触发 + restart 后窗 0 漏网, 治本持续确认.

## 验证 (无需 restart, 仅观测)
- `curl /health` = ok (passthrough / 5 keys / pexec_models kimi_nv/dsv4p_nv/glm5_2_nv /
  nv_default_model=dsv4p_nv / port 40006).
- `docker inspect nv_gw --format StartedAt` = **2026-07-18T21:26:29Z** (R1836 restart,
  R1839/R1841/R1842 未再 restart), 确认仍跑 R1839 改后字节码 (md5=4983bcec).
- `docker ps`: nv_gw Up ~1h, ms_gw Up 42h (热备未碰), cc4101 Up 15h, logs_db Up 2 days.
- env 无漂移: NVU_TIER_BUDGET_GLM5_2_NV=120 / UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 /
  KEY_COOLDOWN_S=25 / NVU_BIG_INPUT_FAIL_N=1 / NVU_STREAM_ABSOLUTE_CAP_S=150 /
  NVU_MS_FALLBACK_FAIL_THRESHOLD=5 全与 R1841 快照一致.
- **0 中断** (本轮无 restart, 全程直连, SR 97.5%, fallback 全 FALLBACK-OK).

## 结果摘要
SR 97.5% (79/81) 稳, bug8 降级兜底在位 0 触发, restart 后纯净窗 0 漏网, fallback 1 bug3+1
timeout 合法递进 0 中断, breaker CLOSED 1 次未 OPEN, env 无漂移. 链路稳, 无 config 可改依据
→ 巡检轮. 下一轮继续观测 bug8 实战 + SR/fallback/pexec elapsed.

## 备注
- 仓库最新轮号 R1841 (commit 3da3082), 本轮 R1842 (基于 git pull --ff-only 后).
- peer HM1 agent 持续写 HM2→HM1 调参轮 (R1840: TIER_TIMEOUT_BUDGET_S 180→178, 不碰 HM2).
- 本轮 0 代码改动 0 restart, 仅 commit round 文件.
