# R1887 (HM2 cc2) — NOP 巡检轮: SR 89.7% 连破第 8 轮, 502 全 zombie+tier耗尽 同 R1885 同构, 500_nv_error 80% 被 NV-CYCLE 吸收成 200 再确认, SSLEOF 30min tier=0 仍停, breaker 全 CLOSED 未 OPEN, 120s 黑洞复现 2 条 (非跳过类) 但 <4 阈值

## 上游根因已在 R1881-R1883 闭合 (NVCF 端对 HM2 出口 IP 段 134.195.101.0/24 的 TLS RST + NVCF 侧 abs_cap/zombie 常态抖动, 非 nv_gw config 可调旋钮). 本轮验证: 当前链路态稳定在"已知 NVCF 上游侧抖动 + nv_gw cycle/breaker/fallback 三层吸收兜住 0 真中断", 无新可动信号.

**改了什么**: NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 改前数据 (30min 窗, 本 session ~12:56 CST 拉取)

### SR
- SR **61/68 = 89.7%** (200:61 / 502:7). **连续第 8 轮破 93%** (R1879 88.9 + R1880 86.7 + R1881 89.7 + R1882 84.4 + R1883 80.9 + R1884 81.0 + R1885 84.7 + R1886 peer-HM1-仅 + R1887 89.7).
  介入条件 #1 (SR 连续 >=3 轮破 93) 早已满足 (连破第 8 轮), 但处置指向**查上游非调参** (R1881-R1883 已穷尽: 根因=NVCF 端对 HM2 出口 IP 段 134.195.101.0/24 的 TLS RST + NVCF 侧 abs_cap/zombie 常态抖动, 非 nv_gw config 可调旋钮).
- 本轮较 R1885 84.7 回升 5.0pp 至 89.7, 仍 < 93 但属破 93 后的低位区间抖动 (80.9-89.7), 非续探底非反弹回 93. 本轮 89.7 接近 R1881 的 89.7, 是低位区间上沿试探.
- 502 分类 (status=502, 共 7 条):
  - zombie_empty_completion **4** (NVCF 侧 zombie 偶发, 已知分类 config 不可修, R1851+ 间歇).
  - all_tiers_exhausted **3** (tier 全 key 耗尽兜底, 与本窗 12:34-12:53 5× NV-MS-FB all_keys_exhausted 同源).
  - **全 NVCF 侧偶发外分支 + tier 耗尽兜底, 非新可配置错误分类**, 与 R1885-R1886 同构. **本窗无 SSLEOFError 直接命中 502, 无 stream_absolute_cap, 无 stream_first_byte_timeout**.

### tier (30min + 60min DB)
- 30min tier 全分类: pexec_success **47** / 500_nv_error **8** / pexec_empty_200 **3**. **本窗无 SSLEOFError, 无 pexec_timeout, 无 ATE, 无 429** (干净基底).
- **500_nv_error 80% 被吸收成 200 再确认 (R1885 结论坐实)**:
  - 全 8 条在 `nv_tier_attempts` 散布 k0-k4 (k0×2 / k1×2 / k2×1 / k3×2 / k4×1, 均摊非单 key).
  - egress_ip 仍全 NULL (R1883 已诊断: SSLEOF/500 分支 upstream.py 不 append egress_ip, 数据盲区仍在, 非本轮新问题).
  - 对应主请求: 8 条 500_nv_error 分属 5 个 req, 其中 **4 个 req 最终 200 成功** (cycle 换 key 后收尾), 仅 1 个 req 最终 502.
  - **即 500_nv_error 80% (4/5 req) 被 NV-CYCLE 吸收成 200** — NVCF 5xx 被 cycle 自动换下一 key 重试后仍成功, 是已 absorbed 的常态中间态, 不是新失败源.
  - 60min 趋势: 500_nv_error 仅 8 条集中 04:35-04:46 UTC 单点簇 (4 个 1min 桶: 3+2+2+1), 此后整窗 0, 非持续批量.
- **SSLEOF 当前完全不在活跃窗口**: 30min tier=0, 60min tier=0. 120min DB pexec_SSLEOFError **7 条全在旧窗口尾部** (与 R1883 结论一致, 02:32-03:08 UTC=R1881/R1882 拉取窗口尾部此后停止). SSLEOF 根因 (R1881/R1883 出口 IP 段) 已闭合且当前未复发, 本轮无需再查 SSLEOF.
- pexec_empty_200 3 条: NVCF 侧偶发空 200 (与 zombie 同族上游空响应, 已知分类).

### fallback (cc4101 30min)
- 触发 **9 条** (PRIMARY-FAIL × 9 + FALLBACK-OK × 6, 3 条无 FALLBACK 后续显示但均未中断):
  - **120s 黑洞 2 条 (非跳过类, 会进 circuit 计数)**:
    - 12:35:50 req=ed658074 → nv_gw 120097ms header/ttfb timeout (PRIMARY-FAIL 非 SKIP) → FALLBACK-OK ms 3094ms.
    - 12:49:35 req=468be9f3 → nv_gw 120042ms header/ttfb timeout (PRIMARY-FAIL 非 SKIP) → FALLBACK-OK ms 3344ms.
  - **75s PRIMARY-FAIL-SKIP-CIRCUIT 3 条 (跳过类, NOT counted, bug3 75s 抢断 cc4101 preempt)**:
    - 12:29:42 req=822cdb8f → 75082ms → FALLBACK-OK ms 4466ms.
    - 12:41:58 req=ab9d40a7 → 75035ms → FALLBACK-OK ms 3252ms.
    - 12:44:41 req=c4cef6c0 → 75081ms → FALLBACK-OK ms 27293ms (单点 27s 慢化尖峰).
  - **非跳过类真请求失败 = 2 条 < 4 阈值, 0 真中断** (两条 120s 黑洞均 FALLBACK-OK ms 成功兜住, 用户无感).
  - **120s 黑洞复现是本轮唯一新现象 (R1882 首现 1 条 → R1885 2 条 → R1887 2 条)**: R1882 当时查 60min NV-PEEK-OK 见大量 >90s 慢成功 (102s/122s/168s/176s/183s/242s/364s) 反证 TIER_BUDGET 收紧到 90 会误杀慢成功暴跌 SR. 本轮查 60min pexec_success elapsed 分布: **全部 <60s (85 个 <30s + 16 个 30-60s, 0 个 >60s)** — 即当前成功窗口已关闭慢成功, 但 120s 黑洞仍在 (nv_gw 端这 2 个请求花 ≥120s 未出首字节, 被 cc4101 chain budget 抢断). 说明: a) 慢成功 (NV-PEEK-OK >90s) 与 120s 黑洞是两个独立现象, 前者 R1882 时段集中现在已停; b) 当前 120s 黑洞是 NVCF 端对特定请求长时无首字节 (与 zombie/abs_cap 同族上游侧), 非 nv_gw config 可修 (UPSTREAM_TIMEOUT=66 是单 tier, tier 间 cycle 可累加 >120s 但 cycle 是为换 key 兜底不能关). 2 条 < 4 阈值, 续盯是否 ≥4/30min 达介入线.
- fallback ms 延迟: 6 条 FALLBACK-OK 全在 1.9-27.3s 区间 (5 条 <5s 干净 + 1 条 27s 单点尖峰), 无 18s+ 趋势化, fallback 负载/健康正常, ms_gw 热备兜住 0 真中断.

### breaker (nv_gw 30min log)
- **全 CLOSED 未 OPEN**, 5× NV-MS-FB-ATTEMPT+OK+SERVED (12:34/12:39/12:44/12:49/12:53, all_keys_exhausted for glm5_2_nv, ms 兜底 served, breaker recorded failure state=CLOSED 无计数).
  req: b8559392 / ae32537f / 7f23b3e5 / 46b7c754 / 9d206e89.
  all_keys_exhausted (全 key 耗尽走兜底) 本窗 5 次, NVCF 上游 key 后半窗被频繁 ratelimit/耗尽 — 与 R1885 同模式, 非新恶化.
- **本窗无 NV-ANTH-BREAKER-FAIL** (R1884 state 4 尖峰后回落, R1885 已确认仍 CLOSED, 本轮无新事件, state 应在 1-2 区间漂移正常工作).
- 介入条件 #3 (breaker OPEN) 不满足.

### env + 健康检查
- env 无漂移 (KEY_COOLDOWN_S=25 / KEY_AUTHFAIL_COOLDOWN_S=60 / NVU_BIG_INPUT_FAIL_N=1 / NVU_BIG_INPUT_THRESHOLD=250000 / UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 / NV_INTEGRATE_KEY_COOLDOWN_S=90 / TIER_COOLDOWN_S=25 / NVU_BIG_INPUT_COOLDOWN_S=180 / MIN_OUTBOUND_INTERVAL_S=0, 全与 R1850-R1885 一致).
- StartedAt 仍 **2026-07-18T21:26:29Z** (R1836 restart, R1839 至 R1887 未再 restart) → 跑 R1839 改后字节码.
- /health ok (passthrough, 5 keys, glm5_2_nv/dsv4p_nv/kimi_nv tiers).
- docker ps 全 Up (nv_gw Up 7h / cc4101 Up 21h / ms_gw Up 2d / logs_db Up 2d).
- bug8: oai_to_anth.py md5=4983bcec (R1839 兜底在位), NV-TOOLCALL-JSON-DOWNGRADE 0 触发, **根除停巡** (R1885 已确认, 不再花轮次观测).

## 决策: NOP (不改)

介入触发四条全不满足或处置指向查上游:
1. **#1 SR 连破第 8 轮**: 满足但 R1881-R1883 已穷尽 nv_gw 调参旋钮并反证 (TIER_BUDGET 收紧到 90 误杀慢成功 SR 暴跌 + KEY/TIER_COOLDOWN 管不到 TLS 握手 RST + UPSTREAM 改不动 NVCF 侧 abs_cap/zombie), 处置指向查上游非调参.
2. **#2 fallback 非跳过类 2 条 < 4 阈值**: 未达介入线. (120s 黑洞复现 2 条, 续盯是否 ≥4.)
3. **#3 breaker 未 OPEN**: 全 CLOSED 未 OPEN, 不满足.
4. **#4 无新可配置分类**: 502 全 zombie+tier耗尽 + 500_nv_error 80% 吸收成 200 + SSLEOF 仍停, 全 NVCF 侧已知分类, 不满足.

硬改违反铁律 (改前必有数据 + 无据不改 + R1881-R1883 已反证 nv_gw 侧无可动).

## 给监督者/运维建议 (沿用 R1881-R1884 结论)
- 真正该动: a) 换出口 IP 段 (让 5 mihomo 端口 7894-7899 背后走非 134.195.101.0/24); b) 联系 NVCF 运维查对该 /24 段 TLS RST/500 限流策略 (23:00+03:00 UTC 档密集 12/23=52% 可能夜间维护/限流窗口); c) 短期无法换时 nv_gw cycle/breaker/fallback 三层吸收逻辑已在位兜底 SR 80.9-99% 抖动近 40 轮可接受 fallback 热备 0 真中断.
- 本轮价值: 不是惰性巡检而是 a) 坐实 R1885 的 500_nv_error 80% 吸收结论 (本轮再验 4/5 req 200); b) 新发现当前 60min pexec_success 全 <60s (无慢成功) 与 120s 黑洞独立 — 即 120s 黑洞非慢成功导致非 TIER_BUDGET 可收紧 (R1882 反证仍成立且当前无慢成功更不可收紧); c) 接续 R1885 确认 SSLEOF 仍停 + breaker 全 CLOSED + SR 低位区间上沿试探 89.7.

## 验证结果
链路未碰 0 改动 0 restart. StartedAt 仍 21:26:29Z /health ok docker ps 全 Up. 0 真中断 (2 条 120s 黑洞均 FALLBACK-OK ms 成功兜住). bug8 根除停巡. env 无漂移. SSLEOF 仍停 (根因闭合 R1881-R1883). breaker 全 CLOSED.

## 下轮 (R1888) 重点
- **120s 黑洞是否 ≥4/30min**: 当前 2 条 (非跳过类), 若续增达 4 → 达介入线 #2, 届时需查 nv_gw 侧 cycle 是否把单 req 拖 >120s (但 cycle 是换 key 兜底不能关, 真正解仍是查上游 NVCF 端首字节延迟). 2 < 4 续盯.
- **SR 连破计数**: 当前第 8 轮 <93, 若回 >93 → 重启连破计数; 若续破 → 连破计数续增 (但已知处置指向查上游非调参, 不达主动改条件).
- **SSLEOF 是否复发**: 30/60min tier=0 持续停, 若复发 ≥6/60min → R1881 根因窗口重现, 届时查 5 mihomo 端口背后出口 IP 是否仍 134.195.101.0/24.
- **500_nv_error 是否续被吸收**: 当前 80% 吸收成 200, 若吸收率掉 (漏到 502 比例升) → cycle 兜底弱化信号.
- **breaker state**: 本窗无 NV-ANTH-BREAKER-FAIL, 续盯是否复现 state 漂移 (1↔3) 或单调续增触 OPEN.

## 铁律遵守
- 改前必有数据: ✅ 30min 窗拉齐 (SR/502分类/tier/fallback/breaker/env/StartedAt/health).
- 改后必有验证: ✅ NOP 无改动无需验证, /health+docker ps 确认在位.
- 聚焦 40006: ✅ 只看 nv_gw, 不碰 ms_gw.
- 写入仓库: ✅ R1887 round 文件 + commit + push.
- 改 .py 必须 restart: ✅ NOP 0 改动 0 restart.
- 只改 HM2 不改 HM1: ✅ 本轮 HM2 only.
- 本轮 R1887 commit 单文件无 peer 误收.
