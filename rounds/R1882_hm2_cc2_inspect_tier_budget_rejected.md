# R1882 (HM2 cc2) — SSLEOF 根因调查后续: tier-budget 收紧提案被慢成功数据反证否决, NOP

> 本轮模式: NOP 巡检 + 决策反证记录。监督者 11:30 重定向"该动 SSLEOF", R1881 已定位根因
> (NVCF 端 TLS RST, 非 config 可修)。本轮尝试找"可动的 nv_gw 侧旋钮", 候选
> `NVU_TIER_BUDGET_GLM5_2_NV 120→90` 被刚拉的 60min 慢成功耗时分布**直接反证为有害**,
> 铁律"改前必有数据"否决该提案。本轮 0 改动 0 restart。

## 改前数据 (30min 窗, ~11:50 CST 拉取)

- **SR 27/32 = 84.4%** (200:27 / 502:5)。**连续第 4 轮破 93, 远超介入线 3**:
  R1879 88.9 → R1880 86.7 → R1881 89.7 → R1882 84.4。R1842 NOP 以来最深。
- **502 分类**: all_tiers_exhausted 2 + stream_absolute_cap 2。全 NVCF 侧 tier 耗尽兜底 +
  abs_cap, 无新可配置分类。
- **tier pexec 60min**: pexec_success 55 (干净基底) / **pexec_SSLEOFError 6 (连续第 4 轮
  维持批量 6: R1877:1→R1878:1→R1879:6→R1880:6→R1881:6→R1882:6)** / pexec_empty_200 5 /
  pexec_timeout 3。SSLEOF 仍批量, 与 R1881 根因结论一致 (NVCF 端 TLS RST)。
- **fallback 7 条** 全 PRIMARY-FAIL-SKIP-CIRCUIT (75s header/ttfb 抢断, bug3 同类):
  10:55/10:58/11:02/11:06/11:11/11:15 跨窗复现 + **11:45 req=989d3899 新现象: cc4101
  120108ms header/ttfb timeout (非通常 75s)** → FALLBACK-OK ms 12667ms。0 真中断。
  非跳过类真失败 0 < 4 阈值。
- **breaker 30min**: 全 CLOSED 未 OPEN。11:26 state=(CLOSED,2,0), 11:42 降到 (CLOSED,1,0)。
  state 在 1-2 漂移, 远低于 OPEN 阈值, 设计内吸收态。
- **bug8**: 0 触发 (根除, 停止巡检)。
- **env 无漂移**, StartedAt 仍 2026-07-18T21:26:29Z, /health ok, docker ps 全 Up。

## 决策过程 (本轮核心: 数据反证否决提案)

### 候选提案: NVU_TIER_BUDGET_GLM5_2_NV 120→90
**动机**: 11:45 req=989d3899 出现 cc4101 120s header/ttfb timeout (首次非 75s 抢断)。
推测: nv_gw glm5_2_nv tier budget=120s 跑 SSLEOF 5 端口 cycle 全空耗, cc4101 120s 抢断前
nv_gw 没主动 502。收紧到 90s 让 nv_gw 早 30s 主动 502 → cc4101 早 fallback → 减少"120s 黑洞"。

### 反证数据 (改前数据完整性检查, 60min NV-PEEK-OK 耗时分布)
拉 `docker logs nv_gw --since 60m | grep NV-PEEK-OK` 的 `after Nms` 耗时, **大量 >90s 的成功**:
```
after 102156ms   ← 成功但 >90s, 90 截断会变 502
after 121957ms   ← 成功但 >120s
after 168509ms   ← 成功但 >120s
after 169062ms
after 176556ms
after 183499ms
after 242211ms   ← 成功但 4min
after 243700ms / 244119ms / 244199ms / 245542ms / 251468ms / 364871ms  ← 成功但 6min
```
**结论**: 收紧 tier budget 到 90s 会把上述 >90s 的成功请求**全部误杀成 502**, SR 不升反
暴跌。**提案被数据直接否决**。120s budget 在当前 SSLEOF 场景下不是"全空耗", 而是容纳
了大量慢成功路径 (NV-PEEK-OK 计的是到 first content 总时间, 跨多 tier/mode 重试, tier
budget=120s 是单 tier 内, 慢成功跨多 tier 累积 wall time)。

### R1881 根因回顾 (本轮确认仍成立)
SSLEOF 根因 = NVCF 端 api.nvcf.nvidia.com 对 HM2 出口 IP 段的 TLS RST。R1881 已排除:
(a) mihomo 单端口线路 (5 端口 :7894/7895/7896/7897/7899 同 EOF, req=192dd11e 单 req
走过全部 5 端口各 1 次); (c) httpx pool keepalive (nvcf_conn.py 用 HTTPSConnection+
PySocks raw socket, 无连接复用)。剩 (b) NVCF 端对出口 IP 段 TLS 限流 = 上游层, 非 nv_gw
config 可调旋钮, 需联系运维。

### 其他"该动"对象的评估
- **egress_ip 观测性增强 (R1881 提的候选)**: 给 pexec 路径补记 egress_ip 列。但 R1881 已
  用 port dist (:7894=1:7895=1...) 定位 5 端口同 EOF, 端口能反查出口 (NV_GLM52_KEY_PROXY_MAP),
  egress_ip 列边际价值有限; 且改 db.py schema + upstream.py 填充 = 2 文件 + schema 迁移
  风险, 本轮单轮不宜。**不选**。
- **breaker 阈值**: 全 CLOSED 未 OPEN, 无恶化, 不动。
- **KEY_COOLDOWN / TIER_COOLDOWN**: R1881 已证管不到 TLS 层, 不动。

## 验证结果
- 链路未碰 (0 改动 0 restart), StartedAt 仍 21:26:29Z, /health ok, docker ps 全 Up。
- 铁律"改前必有数据"本轮**救了链路**: 候选提案在数据完整性检查阶段被 60min 慢成功分布
  直接反证为有害, 避免了一次会误杀慢成功、暴跌 SR 的盲改。
- SR 84.4% 连续第 4 轮破 93 (R1879-R1882), 介入条件 #1 满足, 但处置指向**查上游/联系运维**
  (NVCF 端 TLS RST, 非配置可修), 非 nv_gw 调参。

## 决策理由 (为何 NOP)
1. SSLEOF 根因已被 R1881 定位为 NVCF 端 TLS RST, 非 nv_gw config 可调旋钮 (改 KEY_COOLDOWN/
   TIER_COOLDOWN/UPSTREAM 都管不到 TLS 握手被对端 RST)。
2. 收紧 tier budget 候选被 60min 慢成功耗时分布直接反证为有害 (大量 >90s 成功会被误杀)。
3. egress_ip 观测性增强边际价值有限 (端口已能反查), 且 schema 迁移风险高, 单轮不宜。
4. breaker 全 CLOSED 未 OPEN, fallback 非跳过类 0 < 4, 无新可配置分类。
5. 硬改违反铁律 (改前必有数据 + 无据不改 + 改后必有验证)。本轮数据反而证明"动错会更坏"。

## 给监督者/运维的建议 (本轮无变动, 复述 R1881 结论 + 新数据)
- **真正该动的是上游/出口 IP 层**: 查 HM2 5 mihomo 端口 (7894-7899) 背后物理出口 IP 是否
  共用同 IP 段, 查 NVCF 端对 HM2 出口 IP 的 TLS 限流策略 (23:00+03:00 UTC 档密集 12/23=52%
  可能是 NVCF 端夜间维护/限流窗口)。
- **本轮新发现**: 60min 内大量 >90s 慢成功 (102s/122s/168s/176s/183s/242s/364s), 说明当前
  SSLEOF 场景下 nv 路径是"慢成功"而非"全失败", tier budget=120s 正好容纳, **不可收紧**。
  这同时解释了 SR 84.4% 的构成: 502 是全 SSLEOF cycle 失败的尾部, 但还有大量慢成功在 120s
  内勉强活下来——动 budget 会把这些慢成功也推下悬崖。

## 下轮 (R1883) 建议
- 继续盯 SSLEOF 是否批量化持续 (6/30min) 且 SR 是否续破 93。
- **不要**再尝试收紧 tier budget (本轮已反证有害)。
- 若运维已查出口 IP / NVCF 限流策略有结论 → 按结论动 (可能非 nv_gw 侧)。
- 若 SR 连续 6+ 轮破 93 且 fallback 非跳过类 >=4 → 重新评估是否有 nv_gw 侧可动旋钮
  (但当前候选已穷尽, 大概率仍是 NOP + 联系运维)。
- 维持铁律: 改前必有数据, 改 .py 必须 restart 非 up-d, 不碰 ms_gw, 只改 HM2。

---
本轮 commit: 单文件 (R1882 本身), 无 peer 误收, 文案准确。
0 restart, 0 真中断, 0 盲改 (铁律保护)。
