# R1939 (HM2 cc2): NOP 巡检 R67 — R1933 NameError 修复后稳态持续, 6h SR95.3% 0 真中断, breaker 突发自愈

**铁律遵守**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw(40006) / 所有修改写入仓库 / 只改 HM2 不改 HM1 / 改 .py 必须 restart 非 up-d / 不碰 ms_gw(40007)

## 本轮性质: NOP 巡检 (0 源码改动 0 env 改动 0 restart)

新 session 接手, 读 STATE.md 棒 + git pull 发现 git log 已推进到 R1938 (STATE.md 棒基线仍停留 R1931 "连续第 3 轮 NOP 冻结", 实际中间经历了两轮真改动 + 多轮 NOP):

- **R1932** (peer commit 2cddb85): `oai_to_anth.py finish()` 补读 `saw_real_tool_call` flag → 根治 CC SDK "tool call could not be parsed" session 中断.
- **R1933** (本 lineage, 已物理改 + restart + 验证): 紧急修复 R1928 半成品指数退避裸名 NameError — R1932 restart 重新加载源码让一直潜在未触发的 R1928 半成品 `NVU_GLM52_EXP_BACKOFF` 裸名 (upstream.py:1032 引用但 from import 列表漏) 显形 → nv_gw 每个 glm5_2_nv 请求 NameError crash → 链路半瘫痪. R1933 补 `upstream.py:57` 的 `from .config import (...)` 加 3 个名字 → 根治.
- **R1934/R1935/R1936**: NOP 巡检 R64-R66, 确认 R1933 修复后稳态持续 (SR100%/30min).
- **R1937** (peer HM1→HM1): TIER_TIMEOUT_BUDGET_S 153→152, 只改 HM1 对 HM2 0 影响.
- **R1938** (HM2): 补提交 R1932/R1933 nv_gw 源码快照入仓库 (修铁律5违规).

本轮职责: 继续巡检 R1933 修复后稳态, 确认无回归无新 bug, 0 改动 0 restart. 本轮额外发现 STATE.md 棒基线过时 (仍 R1931), 本轮覆写对齐到 R1939 真实状态.

## 数据 (本 session 拉取, DB 时钟 = 2026-07-19 ~22:57Z UTC, nv_gw StartedAt 13:33:43Z = 已起 ~9.4h)

### nv_gw 健康 + 源码状态
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (= R1933 restart, R1933→R1939 未再 restart, R1935/R1936 记录一致).
- cc4101 StartedAt = 2026-07-19T12:10:22Z (= R1926 step2.0 env up-d).
- /health ok (nv_num_keys=5, pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker ps 全 Up (nv_gw Up About an hour 显示是容器创建时刻 ~13:33, 精确以 StartedAt 为准).
- **源码状态 = R1933 已验证后状态** (无漂移):
  - upstream.py vs upstream.py.bak.R1933 diff = **仅 1 行** (line 57 R1933 import 行: `NVU_GLM52_EXP_BACKOFF, NVU_GLM52_EXP_BACKOFF_STEPS, NVU_GLM52_EXP_BACKOFF_CAP`).
  - NVU_GLM52_EXP_BACKOFF env **未设=关** (R1928 半成品冻结, 从未 in-vivo 激活, 连续第 5 轮).

### 6h nv_gw 成功率 (核心指标, 本轮主窗口 — 30min 窗口流量太稀仅 12 条, 用 6h 拿稳定样本)
- SR = 583/612 = **95.3%** (200:583 / 502:29) — 比 R1931 记录的 91.4% 中段常态明显**改善**, 链路更稳 (R1933 NameError 根治后 + R1932 tool-call fix 后持续稳态).
- 502 全程散发 09:03-14:33 (29 条散布 6h, 非集中突发, 持续散发常态).
- **502 分类全已知** (6h):
  - zombie_empty_completion ×16 (glm5_2_nv, 出口 IP 段同源快回空, R1907-R1909 起持续同段)
  - all_tiers_exhausted ×8 (dsv4p_nv, 70s ATE, NVCF 上游侧)
  - stream_first_byte_timeout ×3 (dsv4p_nv, NVCF 首字节慢)
  - stream_absolute_cap ×2 (glm5_2_nv, 192-195s, 比 R1931 记的 6h=4 略降)
- **无新可配置类** (非 zombie/empty200/timeout/SSLEOFError/abs_cap/all_tiers_exhausted).
- abs_cap 6h=2 (R1931 记 4, 略降); first_byte_timeout 6h=3 (R1931 记 4, 略降).
- tier 6h: pexec_success 436 / pexec_empty_200 46 / pexec_SSLEOFError 8 / IntegrateTimeout 3.
- 所有 502 fallback_occurred=f (DB 记 nv 层 502; 真 fallback 在 cc4101 层 ms_gw 救).

### fallback 率 (负向核心指标)
- 30min: **0** FALLBACK-OK, 0 SKIP-CIRCUIT, 0 真中断 (刚接手 30min 流量稀, 仅 11 条 nv 请求).
- 6h: **61** FALLBACK-OK + **25** SKIP-CIRCUIT, **0** fallback 失败 → ms_gw 全兜住, **0 真中断** (CC 收 0 真 502).

### breaker 状态 (本轮关键观察 — 有突发但已自愈)
- cc4101 primary circuit **OPEN 集中在 21:27-21:33 这 ~7 分钟 (14 次 OPEN)** → 之后 (21:33-现在 22:57, ~1.5h) **0 OPEN** → breaker 已 CLOSED 自愈. 这是一个过去的突发 (可能 NVCF 短暂故障 + cc2 该时段未产出流量致 primary 连续失败达阈值 OPEN), 现已恢复, 非持续退化.
- nv_gw NV-ANTH-BREAKER-FAIL 6h = 6 次 (被 CLOSED 吸收未 OPEN, R1931 同模式).
- 最近 10min (现在): 0 PRIMARY-FAIL, 0 breaker OPEN, nv_gw 持续产出 NV-PEEK-OK + NV-GLM52-SUCCESS (22:57:00/03/06 多条成功, first content 6.6-16s prebuffer 1-3.4KB) — **正反馈核心在工作: 我自己每条请求都走 glm5_2_nv 产数据**.

## 介入四条核对 → 全不满足 → NOP 无据不改
1. **SR 95.3% (6h)** 高于中段常态 (R1931 91.4%), 远未达"连续 3+ 轮跌破 80%"介入线 → 不介入.
2. **502=29 全已知分类** (zombie/ATE/first_byte_timeout/abs_cap), 无新可配置类 → 不介入.
3. **breaker OPEN**: 21:27-21:33 一次性突发 14 次已自愈, 最近 1.5h 0 OPEN, 当前 CLOSED → 不介入 (非持续 OPEN 退化).
4. **指数退避激活决策仍冻结 (连续第 5 轮)**: R1928 半成品 (upstream.py:1027-1037 + config.py:522-527) env NVU_GLM52_EXP_BACKOFF 未设=关, R1933 只修了 NameError 让潜在 bug 不 crash, 但半成品逻辑本身从未 in-vivo 激活. 激活仍需同步 4 坑 (chain_budget 120→420 / cc4101 header 60→450 / post-200 软挂换 key 未实现 / abs_cap 150→250+). 当前链路稳态 (SR95.3% 0 真中断) + 本轮无新监督者激活指令 → 继续冻结. 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动.

## 验证 (NOP 轮, 0 改动故 0 restart, 但确认稳态)
- env 无漂移: UPSTREAM_TIMEOUT=66 / NVU_TIER_BUDGET_GLM5_2_NV=120 / TIER_TIMEOUT_BUDGET_S=180 / NVU_STREAM_ABSOLUTE_CAP_S=150 / KEY_COOLDOWN_S=25 / NVU_GLM52_EXP_BACKOFF 未设=关 (与 R1931 快照完全一致).
- cc4101 env 无漂移: PRIMARY_HEADER_TIMEOUT=60 / CC4101_STREAM_TOTAL_DEADLINE_S=480 (R1926 改) / CC4101_PRIMARY_SKIP_S=30 / CC4101_PRIMARY_FAIL_THRESHOLD=3.
- /health ok, docker ps 全 Up, nv_gw StartedAt 13:33:43Z (R1933 restart 后 0 restart), cc4101 StartedAt 12:10:22Z.

## 结论
R1933 NameError 根治 + R1932 tool-call fix 后, 链路稳态持续 (6h SR95.3% 0 真中断 0 fallback 失败). 21:27-21:33 breaker OPEN 一次性突发已自愈 (非持续退化). 502 全已知 NVCF 上游侧分类散发. 指数退避半成品仍冻结 (连续第 5 轮, env 未激活). **介入四条全不满足 → NOP 无据不改**.

## commit
0 源码改动 0 env 改动, 仅 round 文件.
