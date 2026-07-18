# R1835 (HM2 cc2): 巡检轮 — 链路续稳 SR 97.8%, bug8 连续第 7 轮零真畸形 (真安静期延续)

## 性质
**巡检轮 (不改代码, 不 restart, 无 config 可改依据)**。本轮基于 STATE R1833 "下一轮该做什么"
第 2/3 条 + R1834 round 文件结论: 拉 30min 确认链路稳 + 带时间戳验证 bug8 自反馈过滤
(R1832) 仍生效 (restart 后纯净窗连续第 3 轮 0 真漏网)。

> ⚠️ **交接棒落差**: 本轮接手时 STATE.md 仍是 R1833 内容, 但 git log 显示 **R1834 已由
> 上一个 session 完成** (commit 2100336, round 文件 `R1834_hm2_inspect_sixth_zero.md`
> 已 commit+push)。上一个 session 写了 round 文件却**忘了覆写 STATE.md**。本轮按
> R1834 的实测结论 (SR 96.8%, bug8 真安静期成立) 顺接, 轮号取 R1834+1 = **R1835**。
> 本轮末尾必覆写 STATE.md 补回 R1834+R1835 双摘要, 防 STATE 与仓库轮号再次脱节。

## 依据 / 时机
- `git pull --ff-only` already up to date。仓库最新 `.git`: commit **2100336** (R1834)。
- nv_gw StartedAt = **2026-07-18T20:26:21Z** (= 04:26 CST, R1832 restart 后; R1833/R1834/
  R1835 均未再 restart)。docker ps `nv_gw Up 35 minutes` 与时间一致 (本轮 05:02 CST)。
- 本轮观测时间: 2026-07-19 **05:02 CST** (距 R1834 04:46 检查点 +16min; 30min 窗 04:32-05:02
  全在 R1832 restart 04:26 之后 = 纯净窗)。

## 改前数据 (30min 窗, 纯 R1832 restart 后, StartedAt 20:26:21Z)
- **30min SR = 45/46 = 97.8%** (200:45, 502:1), **比 R1834 96.8% 再升 +1.0pp, 比 R1833
  95.0% 升 +2.8pp**, 明确远离 95% 安全线, 非边缘抖动。
  - error 1 条 (502): req=7bb2dbf0 @04:52, `stream_absolute_cap` (R1797 cap=150 留作 pexec
    偶发真快挂兜底, 设计内)。无 all_tiers_exhausted / 无 content_filter。
    同一请求触发 `NV-ANTH-BREAKER-FAIL` 1 条记录 (nv_breaker state=('CLOSED',1,0) 未 OPEN,
    设计内"记录软挂但不 OPEN", 合法, 与 R1833 同形)。
  - tier (nv_tier_attempts 30min): pexec_success **34** / 500_integrate_error 1 /
    IntegrateTimeout 1 / pexec_timeout 1 / pexec_empty_200 1 / empty_200 1。5 key 各 ≤2
    非系统性。
- **pexec elapsed 持续自愈**: max=**66902ms (~67s)** / avg=~18365ms (~18s) / **≥200s 0 条**。
  ≥60s **2 条** (未破 200s)。对比 R1831 max 288s/avg 38s/6 条 ≥60s, NVCF 侧首字节仍自愈,
  非恶化趋势 (max 在 R1834 62s→R1835 67s 小幅波动, 均远低于 200s 恶化线)。
- **fallback 30min = 5 SKIP-CIRCUIT** (时间戳分布, 全 restart 后纯净窗内):
  - 04:32 (3265cc53) / 04:42 (f660038e) / 04:50 (904e8352) / 04:54 (36360e73) / 04:57 (79303549)
  - 全 `primary timeout after 75009-75081ms < chain budget 120s, cc4101 pre-empted nv_gw retry`,
    **5 rids 全部在 nv_requests 0 rows** = 未到 nv_gw 写库 = cc4101 侧 bug3 非 nv_gw config 可控。
  - **全 FALLBACK-OK, 0 中断**。restart 后纯净 30min 窗内 fallback 5 条 (比 R1834 窗内
    3 条 +2, 但均 NVCF pexec 首字节偶发慢触发, 非 config 可修, 非恶化趋势)。
- **NV-ANTH-BREAKER-FAIL = 1 条** (req=7bb2dbf0, 即上面 502 stream_absolute_cap 那条):
  nv_breaker state=('CLOSED', 1, 0) 未 OPEN。设计内"记录软挂但不 OPEN", 合法, 非恶化。
- **bug8 观测层关键结论 (R1832 自反馈过滤第 3 轮确认, 纯净窗连续第 3 轮 0 命中)**:
  - `docker logs nv_gw --since 30min | grep -c NV-TOOLCALL-JSON-BAD` = **0** → 30min 纯净窗
    0 命中。
  - 带 `-t` 查 60min 窗: 仅 **1 条**命中, 时间戳 **20:12:03Z** (rid=791d66bf, frag=`# cc2
    自优化交接棒 STATE` 全文) — **在 R1832 restart (20:26:21Z) 之前 14 分钟**, 是 R1827
    代码产生的历史残留 docker logs 滞留。R1832 SELF_FB_MARKERS 过滤对此自反馈 (前缀
    `{"content": "#` + STATE marker) 生效, 不打 print。
  - → **bug8 普通流量连续第 7 轮 (R1829-R1835) 零真畸形**, "真安静期"延续 (R1834 成立,
    R1835 延续)。

## 决策 (不改代码)
SR 回升到 97.8% (远离 95% 线, 连续 3 轮 R1833 95.0/R1834 96.8/R1835 97.8 上行) + pexec 自愈
(max 67s, ≥200s 0) + R1832 过滤生效 (纯净窗连续第 3 轮 0 命中, 第 7 轮零真畸形) + fallback
全 cc4101 侧 bug3 (5 rids nv_requests 0 rows, 0 中断) + breaker 软挂 1 条未 OPEN (设计内) +
env 无漂移 + md5 同步 → 链路稳且持续上行, **无 nv_gw config 可改依据**。
硬改任何旋钮 (UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120
均合理值, bug3 根因 NVCF 侧 nv_gw 不可控) 违反"改前必有数据, 改后必有验证"铁律 → 巡检轮不动。

## 验证 (无需 restart, 仅观测)
- `curl /health` ok: passthrough / nv_num_keys=5 / nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv]
  / nv_default_model=dsv4p_nv。
- `docker inspect nv_gw --format StartedAt` = **2026-07-18T20:26:21Z** (= 04:26 CST, R1832
  restart 后; R1833/R1834/R1835 均未 restart)。docker ps: nv_gw Up 35min, ms_gw Up 41h
  (热备未碰), cc4101 Up 13h。
- bind-mount md5 宿主/容器一致 `9f27f455658d5c92cd550487376e8ed1` (R1832 改动在位, R1835 未碰)。
- env 无漂移 (NVU_TIER_BUDGET_GLM5_2_NV=120 / UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 /
  KEY_COOLDOWN_S=25 / NVU_BIG_INPUT_FAIL_N=1 全与 R1833/R1834 一致)。
- **0 中断** (本轮无 restart, 全程直连, 全 fallback 均 FALLBACK-OK)。

## 铁律遵循
- 改前必有数据: ✅ 30min 纯净窗拉满 (SR/error/tier/pexec/fallback/breaker/bug8)。
- 聚焦 40006: ✅ 只看 nv_gw, 不碰 proxy/ms-gw。
- 只改 HM2: ✅ 仅观测, 未改 HM2 任何源码/配置, 未碰 HM1。
- 写入仓库: ✅ 本 round 文件 + 覆写 STATE (补回 R1834 落差的摘要)。
