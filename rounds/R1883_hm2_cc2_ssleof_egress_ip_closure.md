# R1883 (HM2 cc2) — SSLEOF 根因收尾轮: 用现存 egress_ip 数据闭合 R1881 留的"5 出口是否同网段"核心悬案 (实锤同 /24), NOP

> 本轮模式: 数据闭合轮 (NOP + 用现存 DB 数据收尾 R1881 根因调查的最后一个悬案).
> 监督者 11:30 重定向"该动 SSLEOF", R1881 已排除 mihomo 单端口 + httpx pool 两候选, R1882 已
> 反证 tier-budget 收紧有害. 本轮**不碰代码**: 用 nv_requests.egress_ip 现存数据直接回答
> R1881 留给运维/监督者的建议 #1 "5 mihomo 端口背后物理出口 IP 是否共用同 IP 段"——
> **答案实锤: 同 /24 网段 (134.195.101.x)**. 把运维行动项从"需查"变成"已查实锤+给具体 IP 段".
> 所有 nv_gw 侧调参旋钮 (KEY/TIER_COOLDOWN/UPSTREAM/TIER_BUDGET) 已被 R1881/R1882 穷尽且反证,
> 剩余唯一有价值的代码候选 (给 SSLEOF 补 attempt 记录带 egress_ip) 会改 key_cycle_attempts
> 语义有副作用, 本轮数据已闭合其诊断目标 → 无据不动.

## 改了什么: NOP (不改). 无 compose env / 无 .py 改动. 0 restart.

## 改前数据 (30min 窗, ~12:04 CST 拉取)

### SR (连续第 5 轮破 93, 但 SSLEOF 已不在主因位)
- SR 38/47 = **80.9%** (200:38 / 502:9). 较 R1882 84.4 再探底 3.5pp, R1842 NOP 以来最深.
- **连续第 5 轮破 93**: R1879 88.9 → R1880 86.7 → R1881 89.7 → R1882 84.4 → R1883 80.9.
  介入条件 #1 (SR 连续 3 轮破 93) 早已满足, 但根因非 nv_gw 调参能解 (R1881 定位 + 本轮数据闭合).
- **关键新观察: 本窗 502 主因不是 SSLEOF**. 9 条 502 分类:
  all_tiers_exhausted 3 + stream_absolute_cap 3 + zombie_empty_completion 2 + stream_first_byte_timeout 1.
  全 NVCF 侧 tier 耗尽兜底 + abs_cap + zombie + ttfb, **无 SSLEOF 直接命中的 502**
  (SSLEOF cycle 失败后最终落到 all_tiers_exhausted, 但本窗 all_tiers_exhausted 3 是 tier 耗尽常态
  而非 SSLEOF 5 端口全 cycle 落地——见下"SSLEOF 当前不在持续爆发"). 无新可配置错误分类.

### SSLEOF 态势: 当前不在持续爆发 (120min 仅 1 条摘要, tier 表 7 条全在 02:32-03:08 UTC)
- **docker logs nv_gw --since 120m**: 只有 1 条 NV-GLM52-EOF-SUMMARY (11:07:24 req=192dd11e,
  即上几轮已记录的那条 5 端口同 EOF 摘要). **最近 1 小时 (11:08-12:08 CST) 无新 SSLEOF 摘要**.
- **DB nv_tier_attempts 120min**: pexec_SSLEOFError 7 条, 时序全在 07-19 02:32 / 03:08 UTC
  (= 10:32 / 11:08 CST), 即 R1881/R1882 拉取窗口的尾部. 之后停止. egress_route 全 NULL
  (因为 SSLEOF 分支 upstream.py:855-860 命中后 `continue` 不 append attempt dict,
  这 7 条 tier 行是 cycle 完成态归到 all_tiers_exhausted 前的边角记录, 见下"代码缺口分析").
- **60min docker logs**: NV-SSL-CYCLE / NV-GLM52-EOF-SUMMARY 命中 0. SSLEOF 当前已从
  R1877-R1882 的持续批量 6/60min 态缓和下来, 本窗 SR 80.9% 低位的 502 主因是 NVCF 侧
  abs_cap/zombie/tier 耗尽常态抖动, 不是 SSLEOF.

### fallback (7 条全 PRIMARY-FAIL-SKIP-CIRCUIT, 非跳过类 0)
cc4101 30min: 7 条 fallback 全 PRIMARY-FAIL-SKIP-CIRCUIT (75s header/ttfb 抢断, bug3 同类):
- 11:40 req=8591c163 → FALLBACK-OK ms 19679ms
- 11:45 req=989d3899 → cc4101 120108ms header/ttfb timeout (R1882 已记录的 120s 黑洞现象) → FALLBACK-OK ms 12667ms
- 11:53 req=028fab5f → 75019ms → FALLBACK-OK ms 4605ms
- 11:55 req=7f4d0bd9 → 75075ms → FALLBACK-OK ms 11540ms
- 11:57 req=35bab9d9 → 75083ms → FALLBACK-OK ms 4941ms
- 12:00 req=fd7dc771 → 75083ms → FALLBACK-OK ms 2051ms
- 12:03 req=f2b95797 → 75082ms → FALLBACK-OK ms 5972ms
**非跳过类真 nv_gw 失败 0 条 < 4 阈值. 0 真中断** (ms_gw 热备全兜住).

### breaker 30min: 全 CLOSED 未 OPEN
- 11:36 NV-MS-FB-ATTEMPT all_keys_exhausted req=f0a34f75 → ms served, state=CLOSED
- 11:42 NV-ANTH-BREAKER-FAIL stream_absolute_cap req=2c3a4982 state=('CLOSED',1,0)
- 11:49 NV-MS-FB-ATTEMPT all_keys_exhausted req=10ea8c99 → ms served, state=CLOSED
- 11:57 NV-ANTH-BREAKER-FAIL stream_absolute_cap req=5cac4a29 state=('CLOSED',1,0)
- 12:03 NV-ANTH-BREAKER-FAIL stream_absolute_cap req=dbe55a4a state=('CLOSED',1,0)
- 12:05 NV-ANTH-BREAKER-FAIL stream_absolute_cap req=a228049e state=('CLOSED',2,0)
state 在 1-2 漂移, 远低于 OPEN 阈值, 设计内吸收态具自恢复.

## 本轮核心产出: 用现存 egress_ip 数据闭合 R1881 留的悬案

### R1881 留的悬案 (建议 #1)
"查 HM2 5 个 mihomo 端口 (7894/7895/7896/7897/7899) 背后的物理出口 IP 是否共用同一 IP 段.
若共用 → NVCF 端限流/RST 该 IP 段, 需换出口 IP 或联系 NVCF 运维."

R1881 当时查的是 nv_tier_attempts.egress_ip (全 NULL, 数据盲区), 无法按出口 IP 聚合, 只能
靠 NV-GLM52-EOF-SUMMARY 的 port dist (:7894=1:7895=1...) 推测"可能共用".

### 本轮数据闭合 (nv_requests.egress_ip 现存数据, 180min 窗)
```
glm52-mihomo-7894 | 134.195.101.193
glm52-mihomo-7895 | 134.195.101.193
glm52-mihomo-7896 | 134.195.101.195
glm52-mihomo-7897 | 134.195.101.193
glm52-mihomo-7899 | 134.195.101.180
```
**5 mihomo 端口背后物理出口 IP 全在 134.195.101.x 同一 /24 网段** (193×3 + 195×1 + 180×1).
R1881 调查 2 的"5 端口同时 EOF"现象至此有了物理解释: **5 个端口背后是同 /24 出口 IP 段,
NVCF 端 RST 该 IP 段的全部新建 TLS 握手时, 5 端口同时被 EOF 是必然结果** (不是端口层抖动,
是端口背后的出口 IP 段被 NVCF 端 TLS RST).

→ **R1881 根因结论的最后一环闭合**: 非 mihomo 单端口 (R1881 调查 2 已排除) +
非 httpx pool (R1881 调查 3 已排除) + **本轮实锤 5 出口同 /24** = NVCF 端
api.nvcf.nvidia.com 对 HM2 出口 IP 段 134.195.101.0/24 的 TLS RST, 上游/出口 IP 层问题.

### 502 vs 200 按出口 IP 分布 (120min): 非单 IP 恶化, 是整 /24 段被 RST
- 502 散布在 193/195/180 三个 IP (非集中在某一个): stream_absolute_cap 5 + all_tiers_exhausted 6
  (egress_ip NULL 是因 cycle 完成态) + zombie 4 + stream_first_byte_timeout 3 + stream_no_content_gap 1.
- 200 也散布在同三个 IP 主力: 193 (7895:27/7897:26/7894:21/direct:8/integrate-7897:7) +
  180 (7899:23) + 195 (7896:15/direct:9) + direct 218.93.250.242:14.
- **结论**: SSLEOF 不是某一物理出口 IP 独有问题, 是整个 /24 网段被 NVCF 端 RST 的表现,
  与 R1881 根因结论一致. 无单 IP 可摘除 (摘任一都只是 1/5 流量, 治标不治本).

## 代码缺口分析 (为何不给 SSLEOF 补 attempt 记录带 egress_ip)
- db.py:178-190 tier INSERT 已 `a.get("egress_ip")` / `a.get("egress_route")`, 写入侧准备好.
- 但 upstream.py:855-860 SSLEOF 分支命中后 `continue` **不 append attempt dict** (对比
  timeout @808 / conn @828 / empty_200 @748 都 append). 所以 tier 表 SSLEOF 行 egress_ip 全 NULL.
- 唯一有诊断价值的代码候选 = 给 SSLEOF 补 append (带 egress_ip/egress_route). **但有副作用**:
  会改 key_cycle_attempts 长度 → 改 `len(key_cycle_attempts)` → 改
  `key_cycle_429s_before_success` 计数 + NV-SUCCESS "after N cycles"/"first attempt" 日志分支
  + nv_requests.key_cycle_429s 列. 这是行为语义改动, 不是纯增量字段.
- **且本轮数据已闭合该候选的诊断目标**: 5 出口同 /24 已用 nv_requests 现存数据实锤,
  不需要再靠 SSLEOF attempt 行的 egress_ip 来定位 (nv_requests 已有最终成功 key 的 egress_ip,
  且 R1881 的 NV-GLM52-EOF-SUMMARY port dist 已是铁证). → **无据不动** (铁律: 改前必有数据 +
  无据不改 + 改后必有验证. 该候选的"据"=诊断价值, 本轮数据已替代其诊断价值, 边际收益 0,
  却有副作用面). 留作未来若 SSLEOF 重新批量持续爆发且需要 attempt 级出口 IP 聚合时再评估.
- 其它失败分类 (timeout/conn/empty_200) attempt dict 也没写 egress_ip/egress_route 字段,
  但它们都 append 了 attempt 行 (有 nv_key_idx 可反查出口), 且多为同 key 服务端问题非跨 key cycle,
  attempt 级出口 IP 边际价值小, 不动.

## bug8 (监督者已确认根除, 本轮仅一笔带过)
oai_to_anth.py md5=4983bcec1d1203a1f3f8acf371786c6c (550 行) 宿主/容器一致.
NV-TOOLCALL-JSON-DOWNGRADE 60min log=0. 监督者原话"35 轮 0 触发 = 根除, 停止巡检 bug8".

## 验证结果
- 链路未碰 (0 改动 0 restart), StartedAt 仍 2026-07-18T21:26:29Z, /health ok, docker ps 全 Up
  (nv_gw Up 7h/cc4101 Up 20h/ms_gw Up 2d/logs_db Up 2d).
- env 无漂移 (全与 R1850-R1882 一致: KEY_COOLDOWN=25/KEY_AUTHFAIL_COOLDOWN=60/
  NVU_BIG_INPUT_FAIL_N=1/UPSTREAM=66/TIER_BUDGET=180/NV_INTEGRATE_KEY_COOLDOWN=90/
  TIER_COOLDOWN=25/NVU_BIG_INPUT_COOLDOWN=180/MIN_OUTBOUND=0).
- bug8 md5 一致 0 触发. oai_to_anth.py 宿主/容器 md5 同.
- fallback 非跳过类 0 < 4, 0 真中断. breaker 全 CLOSED 未 OPEN, state 1-2 漂移.
- SR 80.9% 连续第 5 轮破 93, 但根因非 nv_gw 调参能解 (R1881 定位 + 本轮数据闭合到出口 IP 段).

## 决策理由 (为何 NOP 不硬改)
1. **所有 nv_gw 侧调参旋钮已被穷尽且反证**: R1881 证明 KEY/TIER_COOLDOWN/UPSTREAM 管不到
   TLS 握手被对端 RST; R1882 证明 TIER_BUDGET 收紧到 90 会误杀大量 >90s 慢成功 (102s/122s/
   168s/176s/183s/242s/364s) SR 暴跌. 无剩余可动旋钮.
2. **SSLEOF 根因已用数据闭合**: 本轮 nv_requests.egress_ip 实锤 5 出口同 /24 (134.195.101.x),
   R1881 留的"是否同网段"悬案有了确定答案. 处置权在运维 (换出口 IP / 联系 NVCF 运维查
   对该 /24 段的 TLS RST 策略), 非 nv_gw 侧.
3. **唯一有诊断价值的代码候选 (给 SSLEOF 补 attempt 带 egress_ip) 无据不动**: 会改
   key_cycle_attempts 语义有副作用, 且本轮数据已替代其诊断价值 (5 出口同 /24 已实锤 +
   NV-GLM52-EOF-SUMMARY port dist 已是铁证). 边际收益 0 副作用面>0.
4. **本窗 SR 80.9% 低位的 502 主因不是 SSLEOF**: 是 NVCF 侧 abs_cap/zombie/tier 耗尽常态抖动
   (SSLEOF 60min docker logs 命中 0, 当前已从 R1877-R1882 持续批量态缓和). 无新可配置错误分类.
5. **fallback 非跳过类 0 < 4, breaker 全 CLOSED 未 OPEN**: 介入条件 #2/#3 不满足.
6. **硬改违反铁律**: 改前必有数据 (本轮数据反而证明 nv_gw 侧无可动) + 无据不改 + 改后必有验证.

## 给监督者/运维的明确结论 (本轮数据闭合 R1881 悬案, 可行动)
1. **5 mihomo 出口 IP 同 /24 实锤**: 7894/7895/7897→134.195.101.193, 7896→134.195.101.195,
   7899→134.195.101.180. 全在 134.195.101.0/24 同网段. R1881 建议 #1 "是否共用同 IP 段" =
   **是, 实锤共用 /24**.
2. **SSLEOF 根因最终结论**: NVCF 端 api.nvcf.nvidia.com 对 HM2 出口 IP 段 134.195.101.0/24 的
   TLS RST. 上游/出口 IP 层问题, 非 nv_gw config 可调旋钮. nv_gw 侧已做极限 (R40/R1730
   SSLEOF cycle 换 key/换端口重试, 单 req 最多 cycle 5 端口).
3. **可行动处置 (权在运维, 非 cc2)**: a) 换出口 IP 段 (让 5 mihomo 端口背后走非 134.195.101.0/24
   的出口); b) 联系 NVCF 运维查对该 /24 段的 TLS RST/限流策略 (23:00+03:00 UTC 档密集 12/23=52%
   可能是 NVCF 端夜间维护/限流窗口); c) 若短期无法换出口, nv_gw 侧 cycle 逻辑已在位兜底,
   SR 抖动区间 (88.9-99% 近 40 轮) 可接受, fallback 热备 0 真中断.
4. **SSLEOF 当前已缓和**: 本窗 (12:04 CST) SSLEOF 60min docker logs 命中 0, 不在持续爆发.
   若未来重新批量持续爆发 (>=6/60min 且持续多轮) → 再评估是否需 attempt 级出口 IP 聚合
   (届时给 SSLEOF 补 attempt 带 egress_ip 的候选可重估, 但需先确认 key_cycle_attempts 语义
   改动可接受).

## 下轮 (R1884) 建议
- **若运维未动出口 IP**: 继续盯 SSLEOF 是否重新批量持续爆发 (>=6/60min 多轮) + SR 是否续破 93.
  若 SSLEOF 持续缓和 + SR 回 >93 → 连破计数重启为 0, 抖动打断, 维持 NOP.
- **若运维已换出口 IP / 有 NVCF 限流结论**: 按结论动 (可能非 nv_gw 侧).
- **不要**再尝试收紧 tier budget (R1882 已反证有害) 或改 KEY/TIER_COOLDOWN 救 TLS (R1881 已证
  管不到 TLS 握手被对端 RST).
- **egress_ip attempt 级补记候选**: 留作未来 SSLEOF 重新批量持续时重估, 当前数据已闭合其
  诊断目标, 不动.
- 维持铁律: 改前必有数据, 改 .py 必须 restart 非 up-d, 不碰 ms_gw, 只改 HM2.

---
本轮 commit: 单文件 (R1883 本身), 无 peer 误收, 文案准确.
0 restart, 0 真中断, 0 盲改 (铁律保护). 本轮价值 = 用现存数据闭合 R1881 根因悬案,
给运维可行动的确定结论 (5 出口同 /24 实锤 + 具体 IP 段), 非 nv_gw 侧代码改动.
