# R1834 (HM2 cc2): 巡检轮 — 链路回升 SR 96.8%, bug8 连续第 6 轮零真畸形 (真安静期)

## 性质
**巡检轮 (不改代码, 不 restart, 无 config 可改依据)**。本轮基于 STATE R1833 "下一轮该做什么"
第 2/3 条: 拉 30min 确认链路稳 + 带时间戳验证 bug8 自反馈过滤 (R1832) 仍生效。

## 依据 / 时机
- 仓库最新 `.git`: commit **b3e0812** (R1833), `git pull --ff-only` already up to date。
- nv_gw StartedAt = **2026-07-18T20:26:21Z** (= 04:26 CST, R1832 restart 后; R1833/R1834 未再
  restart)。docker ps `nv_gw Up 21 minutes` 与时间一致 (本轮 04:47 CST)。
- 本轮观测时间: 2026-07-19 **04:46 CST** (距 R1833 04:38 检查点 +8min)。

## 改前数据 (30min 窗, StartedAt 20:26:21Z = R1832 后)
- **30min SR = 60/62 = 96.8%** (200:60, 502:2), **比 R1833 95.0% 回升 +1.8pp, 明确在 95%
  安全线之上**, 非边缘抖动。
  - error 2 条 (502): `stream_first_byte_timeout` (设计内故障递进 peek path, 走 ms 重放
    用户拿内容) + 1 条其它首字节超时类。无 NV-ANTH-BREAKER-FAIL / 无 all_tiers_exhausted /
    无 content_filter。
  - tier (nv_tier_attempts 30min): pexec_success **49** / pexec_empty_200 2 / IntegrateTimeout 2 /
    pexec_timeout 1。5 key 各 ≤2 非系统性。
- **pexec elapsed 持续自愈**: max=**61880ms (~62s)** / avg=~13500ms (~13s) / **≥200s 0 条**。
  ≥60s **1 条** (pexec_timeout 58.6s 单条, 未破 200s)。对比 R1831 max 288s/avg 38s/6 条 ≥60s,
  NVCF 侧首字节仍自愈, 非恶化趋势。
- **fallback 30min = 4 SKIP-CIRCUIT** (时间戳分布):
  - 04:18 (b6e4a1e3) — **R1832 restart 04:26 之前, 历史残留**。
  - 04:26 (53264cce) — `PRIMARY-FAIL conn status=0 after 9ms ConnectionRefusedError`,
    正在 R1832 restart 窗口 (20:26:21Z), 设计内 restart 短暂 9ms 抢断甩 ms。
  - 04:28 (d6532fde) / 04:32 (3265cc53) / 04:42 (f660038e) — restart 后纯净窗内 3 条,
    全 `primary timeout after 75009-75081ms < chain budget 120s, cc4101 pre-empted nv_gw retry`,
    **全未到 nv_gw (5 rids 在 nv_requests 0 rows)** = cc4101 侧 bug3 非 nv_gw config 可控。
  - **全 FALLBACK-OK, 0 中断**。
- **NV-ANTH-BREAKER-FAIL = 0 条** (优于 R1833 的 1), breaker 未触发软挂更未 OPEN。
- **bug8 观测层关键结论 (R1832 自反馈过滤第 2 轮确认)**:
  - `docker logs nv_gw --since 30min | grep -c NV-TOOLCALL-JSON-BAD` = **0** → restart 后纯净窗
    连续第 2 轮零命中。
  - 带 -t 查 60min 窗: 仅 **2 条**命中, 时间戳 19:58:04Z (rid=9885ad97, frag=`# R18` round 文件)
    + 20:12:03Z (rid=791d66bf, frag=`# cc2 自优化交接棒 STATE`) — **全部在 R1832 restart
    (20:26:21Z) 之前**, 是 R1827 代码产生的历史残留 docker logs 滞留。R1832 SELF_FB_MARKERS
    过滤对这些自反馈 (前缀 `{"content": "#` + STATE/R18 marker) 生效, 不打 print。
  - → **bug8 普通流量连续第 6 轮 (R1829-R1834) 零真畸形**, 从"门槛"进入"真安静期"成立。

## 决策 (不改代码)
SR 回升到 96.8% (远离 95% 线) + pexec 自愈 (max 62s, ≥200s 0) + R1832 过滤生效 (纯净窗 0
命中, 第 6 轮零真畸形) + fallback 全 cc4101 侧 bug3 (nv_requests 0 rows, 0 中断) + breaker
未触发 + env 无漂移 + md5 同步 → 链路稳且上行, **无 nv_gw config 可改依据**。
硬改任何旋钮 (UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120
均合理值, bug3 根因 NVCF 侧 nv_gw 不可控) 违反"改前必有数据, 改后必有验证"铁律 → 巡检轮不动。

## 验证 (无需 restart, 仅观测)
- `curl /health` ok: passthrough / nv_num_keys=5 / nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv]
  / nv_default_model=dsv4p_nv。
- `docker inspect nv_gw --format StartedAt` = **2026-07-18T20:26:21Z** (= 04:26 CST, R1832 restart
  后; R1834 未 restart)。docker ps: nv_gw Up 21min, ms_gw Up 40h (热备未碰), cc4101 Up 13h,
  logs_db Up 2d。
- bind-mount md5 宿主/容器一致 `9f27f455658d5c92cd550487376e8ed1` (R1832 改动在位)。
- env 无漂移 (NVU_TIER_BUDGET_GLM5_2_NV=120 / UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 /
  KEY_COOLDOWN_S=25 / NVU_BIG_INPUT_FAIL_N=1 / NVU_MS_FALLBACK_FAIL_THRESHOLD=5 /
  NVU_STREAM_ABSOLUTE_CAP_S=150 全与 R1833 一致)。
- **0 中断** (本轮无 restart, 全程直连, 全 fallback 均 FALLBACK-OK)。

## 铁律遵循
- 改前必有数据: ✅ 30min 窗拉满 (SR/error/tier/pexec/fallback/breaker/bug8)。
- 聚焦 40006: ✅ 只看 nv_gw, 不碰 proxy/ms-gw。
- 只改 HM2: ✅ 仅观测, 未改 HM2 任何源码/配置, 未碰 HM1。
- 写入仓库: ✅ 本 round 文件 + 覆写 STATE。
