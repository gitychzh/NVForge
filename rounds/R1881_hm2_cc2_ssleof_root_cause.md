# R1881 (HM2 cc2) — 监督者重定向的上游 TLS 根因调查轮: SSLEOFError 排除 httpx pool / 排除 mihomo 单端口, 定位为 NVCF 端 RST 全出口 (非 nv_gw 调参能解) NOP

## 触发: SR 连续 3 轮破 93 达介入线 + 监督者 11:30 巡视明确重定向优先级为 SSLEOFError 根因调查 (非再 NOP 巡检)

**改了什么**: NOP (不改). 无 compose env / 无 .py 改动. 0 restart.
本轮是**根因调查轮而非盲改轮** — 监督者 11:30 巡视明确指令: "R1880 优先: 取 SSLEOF 对应 key/port, 判定 mihomo 线路 vs httpx pool, **改前必有数据**". 本轮做了完整根因定位, 结论是**两个候选根因 (mihomo 单端口 / httpx pool) 都被数据排除**, 真正根因指向 NVCF 端 RST 全出口 IP 段, 属"联系运维/换出口 IP"范畴非 nv_gw 调参旋钮能解.

## 改前数据 (30min 窗, 本 session ~11:38 CST 拉取)

### SR (连破计数首达介入线 3)
- SR 35/39 = **89.7%** (200:35 / 502:4).
- **连续第 3 轮破 93%**: R1879 88.9 + R1880 86.7 + R1881 89.7 → **连破计数 = 3, 首次达介入线** (铁律介入触发条件 #1: SR 连续 >=3 轮破 93).
- 但本轮较 R1880 86.7 **回升 3.0pp**, 非"续跌"而是"低位反弹但仍<93". 旧 2 轮 (R1856 92.6 + R1857 90.2) 早被 R1858 94.7 打断, 不能拼入当前连破序列.

### 502 分类 (4 条)
- all_tiers_exhausted 2 (tier 全 key 耗尽兜底, **本窗 SSLEOF cycle 5 端口全 EOF 后落到 all_keys_exhausted → all_tiers_exhausted**, 即 SSLEOF 的下游表现)
- stream_absolute_cap 1 (NVCF 侧 abs_cap)
- stream_no_content_gap 1 (NVCF 侧 content gap)
- **全 NVCF 侧 tier 耗尽兜底 + abs_cap/gap, 无新可配置错误分类, 本窗无 zombie_empty_completion 无 stream_first_byte_timeout**.

### tier pexec 30min
- pexec_success 24 (干净基底, 较 R1880 31 略降 7)
- **pexec_SSLEOFError 0 (本窗 DB tier 表)** — 但 docker logs 11:06-11:08 显示 req=192dd11e 走全 5 端口各 1 次 SSLEOF (cycle 完后该 req 最终落到 all_tiers_exhausted), 所以本窗 SSLEOF 实际发生在 11:17 之前的窗口边界, 本轮 30min 窗 DB tier 表 cycle 完后归到 all_tiers_exhausted 而非 SSLEOFError 本身 (cycle 完成态).
- pexec_empty_200 1 + pexec_timeout 1 (NVCF 侧偶发)
- **无 ATE 无 429 无 pexec_timeout-as-primary-error** (主路径干净).

## 根因调查 (监督者指令的核心, 改前必有数据)

### 调查 1: SSLEOFError 12h 按 key 集中度 — **散在全部 5 key, 非单 key**
docker logs nv_gw --since 12h grep SSLEOFError: 23 条散在 k1/k2/k3/k4/k5 全部 5 个 key. **不是集中在同 1-2 个 key** → 排除"单 key/单 NVU_PROXY_URL 抖动".

### 调查 2: SSLEOFError 12h 按 mihomo 端口集中度 — **5 端口同时 EOF, 非单端口**
**R1730 NV-GLM52-EOF-SUMMARY 输出铁证**:
```
[11:07:24.2] [NV-GLM52-EOF-SUMMARY] req=192dd11e ssl_eof=5 cycles dist :7894=1 :7895=1 :7896=1 :7897=1 :7899=1
```
单个 req=192dd11e 走过**全部 5 个 mihomo 端口 (7894/7895/7896/7897/7899) 每个各 1 次 SSLEOF**. 即 5 个端口在那一刻**同时** TLS EOF → **排除监督者方案 a (mihomo 单端口线路抖动)**: 若是单端口线路问题, 不可能 5 端口同时 EOF.

### 调查 3: httpx pool keepalive 复用撞 EOF 假设 — **彻底排除 (根本不是 httpx)**
监督者方案 c 假设 "httpx pool keepalive 被 NVCF 单方面 close 后下次复用撞 EOF".
**实际 nvcf_conn.py 全文 83 行, NVCF 连接根本不用 httpx.AsyncClient**, 是用 **`http.client.HTTPSConnection` + PySocks raw socket**, 每次请求 `_make_nvcf_proxy_conn` **新建 socket + 全新 `ctx.wrap_socket()` SSL 握手**, 无连接复用, 无 keepalive, 无连接池. grep `AsyncClient|Limits|max_keepalive` 在 gateway/ 全目录**无命中** (只在 .bak.R1388 历史备份里). → **httpx pool 假设不成立**, 没有 keepalive 可关, 没有 pool max 可缩.

### 调查 4: SSLEOF 12h 时序分布 — 整 12h 散布但 23:00+03:00 UTC 档密集
DB nv_tier_attempts 按小时聚合 (UTC):
- 07-18 16:00=1, 17:00=1, 18:00=1, 19:00=2, 20:00=2, 21:00=1, 22:00=2, **23:00=6**
- 07-19 02:00=1, **03:00=6**
23:00 + 03:00 两档 = 12/23 = 52%, 与监督者 12h 复核一致. 但**这两档之外整 12h 都有散布**, 且最近 (10:30/11:06/11:07/11:08) 又开始增多 — 非仅夜间两档, 是**持续性 NVCF 端 RST**.

### 调查 5: egress_ip 是否能区分出口 — **无法用 (egress_ip 列全 NULL)**
nv_tier_attempts.egress_ip 列在 pexec 路径未填充 (成功+SSLEOF 都 NULL), 无法用出口 IP 区分. 这是**数据盲区**, 但调查 2 的"5 端口同时 EOF"已足以定位: 不是端口层, 是端口背后的出口 IP 段或 NVCF host 层.

## 根因结论 (三个候选排除两个, 剩下的是 nv_gw 调参救不了的)

| 监督者候选根因 | 本轮调查结论 |
|---|---|
| a) mihomo SOCKS5 单端口线路抖动 | **排除** — req=192dd11e 5 端口同时 EOF (调查 2) |
| b) NVCF 端对单 IP 频繁建连 TLS 限流 | 部分支持但 KEY_MODE_BINDING=R1809 全 pexec_us_rr 已均摊, 不应是单 IP; 且 5 端口同 EOF 说明不是单 IP 限流而是 IP 段/host 层 |
| c) python httpclient TLS 复用策略 (httpx pool keepalive) | **彻底排除** — 根本不是 httpx, 是 raw HTTPSConnection+PySocks 每请求新建握手 (调查 3) |
| **真正根因 (剩余)** | **NVCF 端 (api.nvcf.nvidia.com) 对 HM2 出口 IP 段的 TLS RST**, 5 mihomo 端口背后可能共用同一物理出口 IP 段, NVCF 端瞬时/限流性 RST 该 IP 段的全部新建 TLS 握手. **这是上游/出口 IP 层问题, 非 nv_gw config 可调旋钮, 需联系运维查出口 IP 健康或换出口 IP**. |

### nv_gw 侧已做的极限 (代码层)
upstream.py 已有 R40/R1730 的 SSLEOF cycle 逻辑 (NV-SSL-CYCLE / NV-INTEGRATE-SSL-CYCLE / NV-GLM52-EOF-SUMMARY): SSLEOF 触发后**自动换 key/换端口重试**, 一个 req 内最多 cycle 5 端口 (req=192dd11e 就是 5 端口全 cycle 完才落到 all_tiers_exhausted). 这是 nv_gw 源码层能做的最大努力 — 已经在做了, 再改也只是在已有的 cycle 上加 cycle (边际收益 0). **改 UPSTREAM_TIMEOUT / TIER_TIMEOUT_BUDGET / KEY_COOLDOWN 都管不到 TLS 握手被对端 RST** (监督者原话, 本轮数据证实).

## fallback (7 条全 PRIMARY-FAIL-SKIP-CIRCUIT, 非跳过类 0)
breaker 30min 日志显示 11:17/11:24/11:29/11:33/11:36 共 5× NV-MS-FB-ATTEMPT all_keys_exhausted → ms_gw served (req=66525f8e/a75641c2/1bce7e80/9cf4a7b2/f0a34f75), ms 延迟 1.9-5.3s 全 ok. 11:26:08 NV-ANTH-BREAKER-FAIL stream_absolute_cap req=8e3cbd11 state=('CLOSED', 2, 0) (较 R1880 的 3 回降到 2, 仍 CLOSED 未 OPEN). **非跳过类真 nv_gw 失败 0 条 < 4 阈值. 0 真中断.**

## bug8 (监督者已确认根除, 本轮仅一笔带过)
oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致, 四要素 (_detect_bad_tool_args + finish() _downgrade_to_end_turn flag + 两处 final_stop 强制 end_turn) 全在. NV-TOOLCALL-JSON-DOWNGRADE 60min log=0. 监督者原话"35 轮 0 触发 = 根除, 停止巡检 bug8".

## 验证结果
- 链路稳态持续 (SR 89.7% 本窗回升 3.0pp 但仍<93, 连破计数达 3 触介入线, 但根因调查证明非 nv_gw 调参能解).
- 0 restart, 0 真中断 (ms_gw 热备兜住 all_keys_exhausted 全部 served).
- /health ok, docker ps 全 Up (nv_gw Up 6h/cc4101 Up 20h/ms_gw Up 47h/logs_db Up 2d).
- StartedAt 仍 2026-07-18T21:26:29Z, 跑 R1839 改后字节码未变.
- env 无漂移 (全与 R1850-R1880 一致).

## 决策理由 (为何 NOP 不硬改)
1. **监督者指令是"调查"非"盲改"**: 原话"**不要**盲目改 KEY_COOLDOWN/TIER_COOLDOWN 去救 TLS 错(铁律1: 改前必有数据, SSLEOF 不是 cooldown 能救的)". 本轮完成调查, 数据证明三个候选根因排除两个, 剩下的是上游 NVCF 端 RST 出口 IP 段.
2. **nv_gw 侧 cycle 逻辑已在位**: R40/R1730 SSLEOF cycle 换 key/换端口已是源码层极限, 再改边际收益 0.
3. **硬改旋钮违反铁律**: 改 UPSTREAM_TIMEOUT/TIER_TIMEOUT_BUDGET/KEY_COOLDOWN 都管不到 TLS 握手被对端 RST (本轮数据证实 + 监督者原话).
4. **SR 连破 3 轮虽达介入线, 但根因非 nv_gw 可控**: 介入触发条件 #1 (SR 连续 3 轮破 93) 满足, 但该条件的处置本就指向"查上游/联系运维"而非"改 nv_gw 调参" (介入条件 #4 注释原话: "SSLEOFError 属 NVCF 侧 TLS 层非 config 可修, 若批量化需查 upstream / 联系运维, 不是改 nv_gw 调参旋钮").
5. **peer 抢号**: 本 session git pull 见 peer 推 R1879 HM2→HM1 (277707f, UPSTREAM_TIMEOUT 49→47 只改 HM1 对 HM2 0 影响), 本轮 R1881 commit 单文件无 peer 误收.

## 给监督者/运维的明确建议 (本轮调查产出, 非 nv_gw 自优化范畴)
1. **查 HM2 5 个 mihomo 端口 (7894/7895/7896/7897/7899) 背后的物理出口 IP**: 是否共用同一 IP 段. 若共用 → NVCF 端限流/RST 该 IP 段, **需换出口 IP 或联系 NVCF 运维**.
2. **查 NVCF 端 (api.nvcf.nvidia.com) 对 HM2 出口 IP 的 TLS 限流策略**: 23:00+03:00 UTC 档密集 (12/23=52%), 可能是 NVCF 端夜间维护或限流窗口.
3. **数据盲区**: nv_tier_attempts.egress_ip 列在 pexec 路径未填充, 建议后续在 nvcf_conn.py 或 upstream.py pexec 路径补记 egress_ip (出口 IP), 这样下次能直接按出口 IP 聚合判定是 IP 段问题还是 host 问题. **这是源码可改的观测性增强, 但本轮先不改 (避免调查轮叠加代码改动混淆根因结论), 留作 R1882+ 候选**.

## 下一轮 (R1882) 该做什么
1. **等运维响应**: 本轮根因结论已明确指向 NVCF 端 RST 出口 IP 段, 处置权在运维不在 cc2. R1882 若运维未动 → 继续观测 SSLEOF 时序是否仍在 23:00+03:00 档密集, 是否扩散到白天档.
2. **egress_ip 观测性增强 (R1882 候选代码改动)**: 若本轮结论被监督者认可, 下轮可在 upstream.py pexec 路径补记 egress_ip 到 nv_tier_attempts, 让下次能直接按出口 IP 聚合. 但需先确认这是监督者想要的方向.
3. **SR 连破计数**: 本轮达 3 触介入线但根因非 nv_gw 可控. 若 R1882 SR 回 >93 → 连破计数重启为 0 (抖动打断); 若续 <93 → 连破计数=4, 但处置仍是查上游非调参.
4. **nv_breaker state**: 本轮从 R1880 的 3 回降到 2, 仍在 1-3 漂移区间. 续盯是否继续漂移或单调续增触 OPEN.
5. **不重启 nv_gw**: 改前无 .py 改动, StartedAt 仍 21:26:29Z.

**介入触发条件复查** (本轮):
1. SR 连续 3 轮破 93 — **满足** (R1879 88.9 + R1880 86.7 + R1881 89.7), 但处置指向查上游非 nv_gw 调参.
2. fallback 非跳过类 >=4 — 不满足 (0 < 4).
3. NV-ANTH-BREAKER-FAIL OPEN — 不满足 (state CLOSED,2,0 仍 CLOSED).
4. 新可配置错误分类 — 不满足 (SSLEOF 已证实非 config 可修, all_tiers_exhausted/abs_cap/gap 全 NVCF 侧已知分类).
**结论**: 介入条件 #1 满足但根因调查证明非 nv_gw 调参能解, 处置权在运维. 本轮 NOP + 根因调查报告, 不硬改违反铁律.
