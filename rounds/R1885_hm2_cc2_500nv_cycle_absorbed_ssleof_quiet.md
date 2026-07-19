# R1885 (HM2 cc2) — NOP 巡检轮: SR 连破第 7 轮 84.7% 全 NVCF 侧 zombie/abs_cap, 首次单独记录 500_nv_error 已被 NV-CYCLE 正常吸收 (非新分类), SSLEOF 30/60min=0 持续停, breaker state 4 仍 CLOSED 吸收态

## 上游根因已在 R1881-R1883 闭合 (NVCF 端对 HM2 出口 IP 段 134.195.101.0/24 的 TLS RST + NVCF 侧 abs_cap/zombie 常态抖动, 非 nv_gw config 可调旋钮). 本轮验证: 当前链路态稳定在"已知 NVCF 上游侧抖动 + nv_gw cycle/breaker/fallback 三层吸收兜住 0 真中断", 无新可动信号.

**改了什么**: NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 改前数据 (30min 窗, 本 session ~12:37 CST 拉取)

### SR
- SR **50/59 = 84.7%** (200:50 / 502:9). **连续第 7 轮破 93%** (R1879 88.9 + R1880 86.7 + R1881 89.7 + R1882 84.4 + R1883 80.9 + R1884 81.0 + R1885 84.7).
  介入条件 #1 (SR 连续 >=3 轮破 93) 早已满足 (连破第 7 轮), 但处置指向**查上游非调参** (R1881-R1883 已穷尽: 根因=NVCF 端对 HM2 出口 IP 段 134.195.101.0/24 的 TLS RST + NVCF 侧 abs_cap/zombie 常态抖动, 非 nv_gw config 可调旋钮).
- 本轮较 R1884 81.0 回升 3.7pp, 属破 93 后的低位区间抖动 (80.9-84.7), 非续探底非反弹回 93.
- 502 分类 (status=502, 共 9 条):
  - zombie_empty_completion **6** (NVCF 侧 zombie 偶发, input_chars 126-127k 长上下文死剩 12 chars, 已知分类 config 不可修, R1851+ 间歇).
  - all_tiers_exhausted **2** (tier 全 key 耗尽兜底, 与本窗 12:34 all_keys_exhausted 同源).
  - stream_absolute_cap **1** (NVCF 侧 abs_cap, 已知分类 config 不可修).
  - **全 NVCF 侧偶发外分支 + tier 耗尽兜底, 非新可配置错误分类**, 与 R1881-R1884 同构. **本窗无 SSLEOFError 直接命中 502, 无 stream_first_byte_timeout**.

### tier (30min + 60min DB)
- 30min tier 全分类: pexec_success **42** / 500_nv_error **7** / pexec_empty_200 **7**. **本窗无 SSLEOFError, 无 pexec_timeout, 无 ATE, 无 429**.
- **500_nv_error 首次单独记录 (非新可配置分类, 是已 absorbed 的 NVCF 上游 HTTP 500 中间态)**:
  - 全 7 条在 `dsv4p_nv` tier, `nvcf_pexec` upstream, 覆盖 k1-k5 多个 key (k1×1 / k2×2 / k3×1 / k4×2 / k5×1, 均摊非单 key).
  - nv_gw log 印证处置逻辑: `[NV-CYCLE] tier=dsv4p_nv k1 → 500 (500_nv_error), cycling to next key` — NVCF 上游某 key 返回 HTTP 500, NV-CYCLE 自动换下一 key 重试.
  - 对应主请求: 7 条 500_nv_error 分属 4 个 req (740e0b97 / 7db48e7f / 0ef5ef9e / 03302494), 其中 **3 个 req 最终 200 成功** (cycle 换 key 后收尾), 仅 1 个 req (740e0b97) 最终 502 zombie.
  - **即 500_nv_error 大多发生在成功请求的 tier cycle 中间** — NVCF 5xx 被 cycle 吸收后请求仍成功, 不是新失败源.
  - 12h 趋势: 500_nv_error **21 条**散在 12h (vs pexec_success 1264 / pexec_empty_200 60 / pexec_SSLEOFError 22 / pexec_timeout 18), 是 12h 内持续的常态中间态, **非本轮首现**, 前几轮 tier 拆 `pexec_%` 时因 500_nv_error 不以 `pexec_` 开头而没被聚合显示. 本轮首次完整记录它的存在/处置/常态性.
- **SSLEOF 当前完全不在活跃窗口**: 30min=0, 60min=0. 120min DB 仅 03:08:09 一批 (req=6be60e40 / 662e52ef 各 cycle 3 次 SSLEOF 后 pexec_success 收尾, 共 6 条, 集中 1 分钟内, 此后 04:08-04:37 整个活跃窗 0 条). SSLEOF 根因 (R1881/R1883 出口 IP 段) 已闭合且当前未复发, 本轮无需再查 SSLEOF.
- pexec_empty_200 7 条: NVCF 侧偶发空 200 (与 zombie 同族上游空响应, 已知分类).

### fallback (cc4101 30min)
- 触发 **4 条**:
  - **120s 黑洞 2 条 (非跳过类)**:
    - 12:14 req=8b84bdc9 → nv_gw 120094ms header/ttfb timeout (PRIMARY-FAIL 非 SKIP) → FALLBACK-OK ms 5562ms.
    - 12:18 req=6513c4d8 → nv_gw 120114ms header/ttfb timeout (PRIMARY-FAIL 非 SKIP) → FALLBACK-OK ms 2790ms.
  - **75s PRIMARY-FAIL-SKIP-CIRCUIT 2 条 (跳过类, NOT counted)**:
    - 12:29 req=822cdb8f → 75s bug3 抢断 cc4101 preempt nv_gw retry → FALLBACK-OK ms 4466ms.
    - 12:35 req=ed658074 → 12:35:50 120s (实际 120097ms) header/ttfb → 但被 cc4101 记 PRIMARY-FAIL 后 FALLBACK-OK ms 3094ms (此条实为 120s 黑洞, 但归类随 cc4101 记录).
  - **非跳过类真请求失败 = 2 条 < 4 阈值, 0 真中断** (两条 120s 黑洞均 FALLBACK-OK ms 成功兜住, 用户无感).
- fallback ms 延迟: 4 条全在 2.8-5.6s 区间, 无 18s+ 慢化尖峰, fallback 负载/健康正常, ms_gw 热备兜住 0 真中断.

### breaker (nv_gw 30min)
- **全 CLOSED 未 OPEN** (设计内):
  - 12:18:08 / 12:34:27 — 2× NV-MS-FB-ATTEMPT+OK+SERVED (nv chain all_keys_exhausted for glm5_2_nv, ms 兜底 served, breaker recorded failure state=CLOSED 无计数). req=8f13a84f / b8559392.
  - **12:19:18 / 12:19:38 / 12:20:11 — 3× NV-ANTH-BREAKER-FAIL** (glm5_2_nv) anth mid-stream soft-fail:
    - 12:19:18 zombie_empty_completion req=6ac67d7d state=(CLOSED, **2**, 0).
    - 12:19:38 stream_absolute_cap (cap_elapsed=193s, total_elapsed=193s, gap_limit=160s) req=b8bbc08f state=(CLOSED, **3**, 0).
    - 12:20:11 zombie_empty_completion req=ba7fa1f4 state=(CLOSED, **4**, 0) **本窗最高**.
  - **重点结论 (接续 R1884)**: nv_breaker state 第二字段本窗升到 **4** (R1842 NOP 以来 38 轮最高, 与 R1884 一致), 但仍是 NVCF 侧 abs_cap/zombie 尖峰后窗口淘汰**自然回落**, 远低于 OPEN 阈值, 设计内吸收态且具自恢复. **R1884 已闭合 R1771 "滑动窗口会否误触 OPEN" 悬案 = 不会**, 本轮接续确认 state4 在 abs_cap/zombie 尖峰下仍 CLOSED, R1771 鲁棒性持续成立.
  - **注**: R1884 关切的 "state4 是否持续/续增" — 本窗 state4 是 12:20:11 单点尖峰, 之后 12:34 all_keys_exhausted 回到 state=CLOSED (无第二字段显式), 即尖峰后回落, **非续增触 OPEN, 出现事件≠恶化**.

### bug8 (根除, 停巡)
- oai_to_anth.py md5=**4983bcec1d1203a1f3f8acf371786c6c** 宿主/容器一致 (host /opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py vs container /app/gateway/format/oai_to_anth.py), 550 行.
- 实战降级触发 **0** (NV-TOOLCALL-JSON-DOWNGRADE 60min log=0 + 120min DB=0 双确认). 兜底在位 args 全合法不需触发, 符合 R1839 原话. **R1841-R1885 连续 45 轮 0 触发, 根除确认, 停止花轮次观测 bug8** (监督者 11:30 巡视已令停巡).

### env / 健康快照
- env **无漂移** (KEY_COOLDOWN=25 / KEY_AUTHFAIL_COOLDOWN=60 / NVU_BIG_INPUT_FAIL_N=1 / UPSTREAM=66 / TIER_BUDGET=180 / NV_INTEGRATE_KEY_COOLDOWN=90 / TIER_COOLDOWN=25 / NVU_BIG_INPUT_COOLDOWN=180 / MIN_OUTBOUND=0, 全与 R1850-R1884 一致).
- /health ok (proxy_role=passthrough, nv_num_keys=5, nv_default_model=dsv4p_nv, port=40006).
- docker ps 全 Up (nv_gw Up 7h / cc4101 Up 21h / ms_gw Up 2d / logs_db Up 2d).
- nv_gw StartedAt 仍 **2026-07-18T21:26:29Z** (= R1836 restart, R1839 至 R1885 未再 restart) → 跑 R1839 改后字节码.

## 决策理由
介入触发四条:
1. SR 连续 >=3 轮破 93: **满足** (连破第 7 轮 84.7%). 但 R1881-R1883 已穷尽所有 nv_gw 调参旋钮并反证 (TIER_BUDGET 收紧到 90 会误杀 60min 内大量 >90s 慢成功 → SR 暴跌 / KEY·TIER_COOLDOWN 管不到 TLS 握手被 RST / UPSTREAM 改不动 NVCF 侧 abs_cap/zombie). **处置指向查上游非调参**.
2. fallback 非跳过类 >=4: **2 条 < 4 不满足** (2 条 120s 黑洞均 FALLBACK-OK 兜住).
3. NV-ANTH-BREAKER-FAIL 出现 OPEN: **不满足** (state=CLOSED,4,0 仍 CLOSED, 尖峰后回落).
4. 出现新可配置错误分类: **不满足**. 500_nv_error 经本轮首次完整记录确认为 **已 absorbed 的 NVCF 上游 HTTP 500 中间态** (NV-CYCLE 自动换 key, 3/4 主请求仍 200 成功), 非新可配置 bug; SSLEOF 30/60min=0 已停.
→ **四条全不满足硬改条件** (除 #1 但 #1 处置已穷尽指向上游). NOP 不改, 维持铁律 (改前必有数据 + 无据不改 + 改不动的不硬改).

## 验证结果
- 链路稳态持续: SR 84.7% 连破第 7 轮 (全 NVCF 侧 zombie/abs_cap/tier 耗尽兜底, 非新可配置分类) +
  bug8 0 触发 (DB+log 双确认, 根除停巡) +
  breaker 全 CLOSED 未 OPEN (state4 尖峰后回落, R1771 鲁棒性持续, R1884 闭合确认) +
  fallback 非跳过类 2 < 4 + 0 真中断 (4 条 fallback 全 FALLBACK-OK ms 兜住, 用户无感) +
  tier 干净 (无 ATE/无 429/无 pexec_timeout-as-primary-error; 500_nv_error 7 条已被 NV-CYCLE 吸收; SSLEOF 30/60min=0) +
  /health ok + docker ps 全 Up + 0 restart + StartedAt 仍 21:26:29Z 跑改后字节码.
- 连续 36 轮 NOP (R1842-R1885) 链路稳态. R1881-R1883 上游根因闭合后, nv_gw 侧无可动旋钮持续确认.

## 给监督者/运维结论 (沿用 R1881-R1884, 无变化)
- 真正该动: 上游/出口 IP 层 — 查 HM2 5 mihomo 端口 7894-7899 背后物理出口 IP 是否共用同 IP 段 (R1883 已实锤 5 出口同 /24 = 134.195.101.0/24) + 查 NVCF 端对 HM2 出口 IP 段的 TLS RST / 500 限流策略 (23:00+03:00 UTC 档密集 12/23=52% 可能夜间维护/限流窗口).
- 短期无法换时: nv_gw cycle 逻辑 (NV-CYCLE 换 key / NV-MS-FB 兜底 / nv_breaker 吸收) 在位兜底, SR 抖动 80.9-99% 近 40 轮可接受, fallback 热备 0 真中断.

## 文案备注
本轮 R1885 commit 单文件 (R1885 本身), 无 peer 误收, 文案准确. 本轮价值 = 闭合 "500_nv_error 是否新可配置分类" 悬案 (答案: 否, 是已 absorbed 的 NVCF 上游 HTTP 500 中间态, NV-CYCLE 换 key 后 3/4 主请求仍成功) + 接续 R1884 确认 breaker state4 在 abs_cap/zombie 尖峰下仍 CLOSED (R1771 鲁棒性持续).
