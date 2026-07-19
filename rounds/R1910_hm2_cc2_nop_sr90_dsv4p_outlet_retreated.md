# R1910 (HM2 cc2) — NOP 巡检 R61

> 时间: 2026-07-19T09:02Z 拉取 30min 窗口 (本 session). git pull "Already up to date".
> 仓库最新轮号 R1909 (commit 4b8e359). cc2 续 R1910.
> 上一轮 R1909 commit 4b8e359. nv_gw StartedAt 仍 21:26:29Z (R1836 restart, R1839→R1910 未再 restart).

## 1. 数据 (改前必有数据)

### 30min nv_gw request 层
- SR = 55/61 = **90.2%** (200:55 / 502:6). vs R1908 87.3% → R1909 91.9% → R1910 90.2%, 抖动区间中段常态, 非退化.
- 502=6 全 NVCF 上游侧, 三分类:
  - **zombie_empty_completion×4**:
    - 3× glm5_2_nv, egress 134.195.101.195/193/180 (同 134.195.101.0/24 出口 IP 段单点续, R1907→R1908→R1909→R1910 连续 **4** 轮同段同源), function 3b9748d8, ttfb 4404-12761ms (快回空 body)
    - 1× dsv4p_nv, egress **218.93.250.242 (非空, 新 IP 段, R1909 首现本轮续)**, function **74f02205-c7b**, ttfb 1938ms (快回空). 与 R1909 完全一致的新形态续抬头第 2 轮.
  - **all_tiers_exhausted×1 (dsv4p_nv)**, egress 空, function **74f02205-c7b**, duration 68060ms, tiers_tried=1, key_cycle=[] (出口侧整体不可达, 与 R1908/R1909 同源)
  - **stream_first_byte_timeout×1 (dsv4p_nv)**, egress **134.195.101.193** (新: dsv4p_nv 走了 glm5_2_nv 同段出口 IP), duration 103138ms, tiers_tried=1, key_cycle=[] — 本轮新出现的子分类, 1×, 首字节 103s 全程空转超时.

### 30min nv_gw tier 层
- pexec_success 48 / pexec_empty_200 1 (仅 1, vs R1909=2 微降)
- **500_nv_error 本轮 0** (vs R1908=9 / R1909=9 全 dsv4p_nv function 74f02205 egress 空). **dsv4p_nv 出口侧问题本轮明显回落** — 上两轮持续 9 个 500_nv_error 的同源中间态本轮消失, 被 retry 吸收到 200 的负担减轻.
- pexec_SSLEOFError 本轮 0 (vs R1909=1 微降)
- pexec_timeout 本轮 0

### 30min fallback 层 (cc4101 日志)
- **5 FALLBACK-OK**, 全 75s SKIP-CIRCUIT (primary timeout 75030-75080ms < chain budget 120s, cc4101 bug3 preempt, NOT counted toward circuit).
- 微升 R1908=5→R1909=4→R1910=5. 0 真中断 (全被 ms_gw 兜住, 0 非跳过类).
- 用户诉求 "可以报错但不能让 cc2 中断" 仍达成.

### 15min breaker / bug8 / MSFB 层
- NV-ANTH-BREAKER-FAIL **1 次** (glm5_2_nv zombie 触发, state CLOSED 吸收未 OPEN).
- breaker **OPEN 0 连续 14+ 轮** (R1909=13+ → R1910=14+).
- bug8 DOWNGRADE **0 触发 (连续 57 轮根除停巡)**.
- NV-CAP-RESET-MSFB **3 次** (持平 R1909=3, bug7 已修路径).

## 2. env / 健康快照 (无漂移)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=180
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90
TIER_COOLDOWN_S=25
```
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker inspect StartedAt = 2026-07-18T21:26:29Z (R1836 restart, R1839→R1910 未再 restart, 跑改后字节码).
- env 与 R1909 完全一致, 0 漂移.

## 3. 决策: NOP 无据不改

介入四条全不满足 → NOP R61, 0 改动 0 restart:
1. **SR 90.2% 抖动区间中段常态非退化**, 未达"连续 3+ 轮跌破 80%"介入线 (R1908=87.3 / R1909=91.9 / R1910=90.2 全在中段).
2. **502=6 全 NVCF 上游侧** (zombie 首字节快回空 / ATE dsv4p_nv 出口侧整体不可达 / stream_first_byte_timeout dsv4p_nv 首字节 103s 空转), 非新可配置类.
3. **breaker OPEN 0 连续 14+ 轮**, 本轮 BREAKER-FAIL 1 被 CLOSED 吸收未 OPEN.
4. **dsv4p_nv 出口侧问题本轮回落而非续抬头** — R1907 首抬头 4 ATE → R1908 第 2 轮 4 ATE+9 500 → R1909 第 3 轮 1 ATE+9 500+1 zombie 新形态 → **R1910 第 4 轮: 1 ATE+1 zombie 新形态续, 但 9 个 500_nv_error 消失**.
   即"连续 3+ 轮关注线"虽达, 但本轮形态**降级** (500_nv_error 同源簇 0), 说明 dsv4p_nv function 74f02205 出口路由并非持续不可达, 而是**间歇性** —
   R1909 STATE 担心的"第 4 轮续抬头应升级核查"未成持续态势, 本轮不触发操作侧升级核查动作, 继续观测.

## 4. 验证 (NOP 无 restart)

- env 无漂移 (与 R1909 完全一致), /health ok, docker ps 全 Up, StartedAt 仍 21:26:29Z (0 restart).
- 无 .bak (0 改动).

## 5. 结论 + 给监督者方向

- 链路稳: SR 90.2% 中段常态, fallback 5 全 75s SKIP-CIRCUIT 0 真中断, breaker OPEN 0 连续 14+ 轮, bug8 0 触发连续 57 轮根除停巡.
- **本轮核心: dsv4p_nv 出口侧问题回落而非升级** — R1908/R1909 持续 9 个的 500_nv_error 同源簇 (dsv4p_nv function 74f02205 egress 空) 本轮消失, 仅留 1 ATE + 1 zombie 新形态 (egress 218.93.250.242 非空). 说明该出口路由是**间歇性不可达**而非持续, R1909 STATE 担心的"第 4 轮升级核查"触发条件未成.
- 给监督者: dsv4p_nv function 74f02205 出口侧三态 (ATE egress 空 / zombie egress 218.93.250.242 非空 / stream_first_byte_timeout egress 134.195.101.193) + glm5_2_nv 134.195.101.0/24 zombie 单点续连续 4 轮 — 仍属 NVCF 上游侧 + 出口 IP 段问题, 非 nv_gw 单参数可解. 本轮回落是好信号, 继续观测是否再抬头.
- 沿用铁律: 只改 HM2, 不碰 ms_gw(40007, 重启窗口热备), 不碰 HM1. 改 .py 必须 restart.
