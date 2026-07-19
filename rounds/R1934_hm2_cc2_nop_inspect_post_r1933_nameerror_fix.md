# R1934 (HM2 cc2): NOP 巡检 R64 — 补提交 R1933 round 文件 + 验证 R1933 NameError 修复稳态 + R1932 tool-call fix 无回归

**铁律遵守**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw(40006) / 所有修改写入仓库 / 只改 HM2 不改 HM1 / 改 .py 必须 restart 非 up-d / 不碰 ms_gw(40007)

## 本轮性质: NOP 巡检 + 补提交 (0 源码改动 0 restart)

本轮新 session 接手时发现: 上 session 已完成 R1932 (commit 2cddb85, peer) + R1933 (NameError 紧急修复, 已物理改 + restart + 验证, 但 **R1933 round 文件从未 git commit/push** — 违反铁律4)。本轮职责:

1. 拉数据验证 R1933 修复稳态 (NameError 根治 + SR 回升 + fallback 回归 + R1932 tool-call fix 无回归).
2. 补提交 R1933 round 文件 (rounds/R1933_hm2_cc2_fix_exp_backoff_nameerror.md, 114 行, untracked → 入库).
3. 写本轮 R1934 巡检记录.
4. 覆写 STATE.md 对齐到 R1934.
5. **0 源码改动 0 env 改动 0 restart** — 指数退避 env 开关仍关 (NVU_GLM52_EXP_BACKOFF 未设=关), 冻结决定连续第 4 轮保持.

## 数据 (R1933 restart 后 ~14min 稳态窗口, 本 session 21:47Z 拉取)

### nv_gw 健康 + 源码状态
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (= R1933 restart, 与 R1933 round 文件记录一致, 未被后续再 restart).
- cc4101 StartedAt = 2026-07-19T12:10:22Z (= R1926 step2.0 env up-d).
- /health ok (nv_num_keys=5, pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker ps: nv_gw Up 14min / cc4101 Up 2h / ms_gw Up 2d / logs_db Up 2d.
- **源码状态 = R1933 已验证后状态** (无漂移):
  - upstream.py vs upstream.py.bak.R1933 diff = **仅 1 行** (line 57 的 R1933 import 行).
  - config.py vs config.py.bak.R1933 diff = **0** (R1933 不改 config).
  - oai_to_anth.py (R1932 改动) in place: line 400-405 saw_real_tool_call fix 在位, oai_to_anth.py.bak.R1932 备份在位.

### 30min nv_gw 成功率 (核心指标)
- SR = 32/32 = **100%** (200:32 / 502:**0**) — **比 R1931 91.4% 更好**, R1933 NameError 根治后 nv_gw 恢复正常处理请求.
- abs_cap 30min = **0** (R1918 方案0 持续归零, 连续多轮).
- tier 30min: pexec_success 19 / pexec_empty_200 3 (glm5_2_nv 首字节快回空中间态被 retry 吸收到 200) / pexec_SSLEOFError 1 (出口 IP 段 134.195.101.0/24 续抬头).
- 6h SR = 614/655 = **93.7%** (200:614 / 502:41), 与 R1931 6h (93.7%) 完全一致, 非退化.
- 6h 502 分类: zombie_empty_completion×21 / all_tiers_exhausted×12 / stream_absolute_cap×4 / stream_first_byte_timeout×4 — 全 NVCF 上游侧已知类 (zombie 出口 IP 段同源 / abs_cap R1918 方案0 已让 30min 归零 6h=4 残留 / all_tiers_exhausted 链路兜底 / first_byte_timeout 指数退避靶子但未激活).

### NameError 根治验证 (R1933 核心目标)
- since 14m (R1933 restart 后): `grep -cE "NameError|Traceback"` = **0** ← R1933 import 修复完全生效.
- since 30m: 16 条 NameError 全集中在 **13:17-13:33Z** (R1933 restart 前 NameError crash 残留窗口) — restart 后 14min 内 0 新增, 稳定根治.
- nv_gw 日志 21:45-21:46 正常 NV-REQ 流 (mapped_model=glm5_2_nv stream=True), 无 Traceback 跟随 ← nv_gw 正常处理请求.

### fallback 率 (负向核心指标)
- 30min: **34** FALLBACK-OK, 但时间分布高度集中:
  - 21:27-21:33 (8min 窗口, 含 R1933 restart 前后): 32 条 — R1933 restart 前 NameError crash 期 nv_gw 毫秒级 RemoteDisconnected 触发 cc4101 breaker 连失败 → breaker OPEN (14 次) 直走 ms.
  - 21:37 + 21:40 (2 条): `PRIMARY-FAIL primary timeout after 120112ms header/ttfb timeout` — **正常超时路径** (cc4101 PRIMARY_HEADER_TIMEOUT=120s 抢断, 非 NameError 崩溃), ms 2.5-27s 兜住.
  - since 20m: 22 / since 10m: **1** / since 5m: **0** ← **稳态 fallback 已回归 ≤1/10min 低位**, 远好于 R1931 的 10/30min.
- breaker OPEN 14 次全在 21:27-21:33, **21:33 后 0 新 OPEN** ← cc4101 circuit breaker 已从 OPEN cool-down 恢复 CLOSED, nv 流量回流 nv_gw.
- **0 真中断**: 所有 34 fallback 全 FALLBACK-OK (ms 2-27s 救回), 0 fallback 失败 → CC 收 0 真 502.
- 用户诉求 (2026-07-19 01:40) "可以报错但不能让 cc2 中断" 仍达成.

### R1932 tool-call fix 无回归验证 (R1932 目标)
- R1932 restart 时间 = 2026-07-19T13:20:36Z.
- cc2 jsonl "could not be parsed (retry also failed)" 最后时间戳 = **2026-07-19T12:01:05Z** (R1932 restart 前), restart 后 ~1.5h 内 **0 新增** ← R1932 saw_real_tool_call fix 有效根治, 无回归.
- 502 的 finish_reason=tool_calls 类: 30min 0 条 (R1932 改的是 converter 输出给 CC 的 stop_reason, zombie 在 DB 层仍记 NVCF 原始 stop; 当前窗口无 zombie, 无回归验证压力).

## 介入四条全不满足 → NOP 无据不改

1. **SR 100%/30min** (R1931=91.4%), 远高于"连续 3+ 轮跌破 80%"介入线 — 链路稳态甚至好转.
2. **502=0/30min**, 6h 502 全 NVCF 上游侧已知类 (zombie/abs_cap/first_byte_timeout/all_tiers_exhausted), 非新可配置类.
3. **breaker OPEN 14 次全 R1933 restart 窗口期残留, 21:33 后 0 新 OPEN** — 已恢复 CLOSED, 非 nv_gw 旋钮可解的持续 OPEN.
4. **指数退避 env 仍关 (NVU_GLM52_EXP_BACKOFF 未设=关)**, R1928 半成品现在"可安全冻结加载" (R1933 import 修复后), 激活决策仍冻结 (连续第 4 轮), 无新监督者激活指令.

## 为何本轮 = 巡检 + 补提交而非激活指数退避

- R1928/R1929/R1930/R1931/R1933 冻结理由仍成立: 半成品指数退避 (R1928 写入 + R1933 import 修复) 现在"可安全加载"但**从未 in-vivo 激活** (env 开关未设). 激活需同步: (1) chain_budget NVU_TIER_BUDGET_GLM5_2_NV 120→420 (2) cc4101 PRIMARY_HEADER_TIMEOUT 120→450 (3) post-200 软挂换 key 未实现 (handlers.py 5 处 zombie/abs_cap/no_content_gap 分支) (4) abs_cap NVU_STREAM_ABSOLUTE_CAP_S 150→250+ 容指数退避. R1926 已铺路 cc4101 STREAM_TOTAL_DEADLINE 360→480 扫清坑 (1)(2) 的 cc4101 抢断前提.
- 当前链路稳态 (SR 100%/30min + fallback 稳态 ≤1/10min + 0 真中断) + 本轮无新监督者激活指令 → 继续冻结. **等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动**.
- **本轮核心修复 (R1933) 已由上 session 完成**: NameError 根治 (since 14m=0), fallback 从 R1931 的 10/30min 抖动降至稳态 ≤1/10min (排除 restart 窗口残留). 这正是"指数退避冻结但链路仍稳"的正反馈证据 — 不激活半成品, 只修 import 让它"可安全冻结", 链路照常稳.

## 关联

- **R1932** (2cddb85, peer): 改 oai_to_anth.py finish() 补读 saw_real_tool_call flag, 根治 CC SDK "could not be parsed (retry also failed)" session 中断. restart 触发 R1928 半成品 NameError 显形 (非 R1932 引入). 本轮验证 R1932 fix 无回归 (restart 后 0 新增).
- **R1933** (本轮补提交, round 文件 114 行): 紧急修 R1928 半成品指数退避裸名 NameError (upstream.py:57 补 import NVU_GLM52_EXP_BACKOFF + STEPS + CAP). 物理改 + restart (13:33:43Z) + 验证 (NameError since 14m=0, fallback 大降, SR 回升) 已由上 session 完成, 但 **round 文件从未 commit/push** (上 session 漏 commit). 本轮补提交修复 (铁律4).
- **R1928** (b7fbf30): 指数退避冻结轮, 写入半成品 config.py:522-527 + upstream.py:1027-1037 但漏 import → R1933 根因. R1933 修后"可安全冻结".
- **R1918**: nv_gw cap_origin 重置 (方案0) 让 abs_cap 30min 持续归零, 连续多轮.
- 监督者 21:00/21:15 指数退避方案: NVU_GLM52_EXP_BACKOFF 是其开关, R1933 后半成品可安全冻结, 激活决策仍冻结.

## 教训 (继承自 R1933, 本轮再次印证)

- **半成品代码即使"冻结(env 关)"也必须保证 import 完整** — Python 运行时求值裸名, 不等 if 条件. R1928 漏 import → R1932 restart 显形 NameError → 半瘫痪 (0 真中断但 100% nv 数据空洞). R1933 已修.
- **连续 NOP 轮 (R1929-R1931) 未 restart 是 NameError 没早暴露的直接原因** — 冻结半成品应至少 restart 一次验证"可加载". R1933 restart 后已验证可加载.
- **改后必须 commit/push** (铁律4) — R1933 上 session 物理改 + restart + 验证全做了, 唯独漏 commit round 文件. 本轮补提交修复, 让下一个 session 能 git pull 看到完整 R1933 记录.
