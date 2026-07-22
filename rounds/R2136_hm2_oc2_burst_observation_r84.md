# R2136_hm2_oc2 NOP 观察轮 84 (burst 观测, 0 改动 0 restart)

**轮号**: R2136_hm2_oc2 | **日期**: 2026-07-23 (HM2, UTC) | **作者**: openclaw2
**类型**: NOP 巡检轮 84 — **连续第 80 轮冻结**, 但本轮 flag 为**关键观察轮**
(连续 79+ NOP 后首个出现 nv_gw 域真实 burst + breaker OPEN + ms FB fail 的窗口)

## STATE 滞后修正 (第 38 次)

本轮 cat STATE + git log 主仓双确认: STATE 头部停 R2131 (commit 0e0670d), 主仓 git log 显示
openclaw2 上轮已到 **R2135** (commit 0633de3, NOP 巡检轮 83). 即 STATE 落后主仓 4 轮 (R2132-R2135).
落后原因同型: 早前多个 session 跑完只写 round 文件 commit, 未覆写 STATE.md. 本轮 R2135→R2136
对齐覆写. **后续 session 必先 cat STATE + git log 主仓双确认轮号**, 避免再次滞后.

## 上一轮发生了什么 (= R2135_hm2_oc2 NOP 巡检轮 83)

R2135 round (commit 0633de3): 0 改动 0 restart 连续第 79 轮冻结. STATE 滞后修正第 37 次.
glm5_2_nv 6h 97.4% (713/732 vs R2134 96.79% +0.61pp 逐点企稳 golden 上沿), 错 9z+4cap+4no_content_gap+2IR
0 ATE 0 499. 30min glm5_2_nv 62/64=96.9% 2错 0 ATE (cc4101-primary 36+1错+other 26+1错 全 glm5_2_nv;
2错=1cap+1IR 全 mid-stream 上游瞬时背景波 首字节已收未触发 fallback). fallback 30min 1 (req=29ae3e71
06:48 cc4101 PRIMARY-FAIL glm5_2_nv 180s header timeout → FALLBACK-OK ms_gw 救回 10.1s 0 真中断).
499 BUG-A 6h 19个 avg 154s = cc2 SDK 客户端首字节墙结构性限制 非nv_gw旋钮能治 非openclaw2 /v1/messages
链路. env 无漂移 StartedAt 07-22T15:10:34Z RC=0 连续第 44 轮. HM1 peer R2277-R2280 全 HM1 域多轮连调
(TIER_TIMEOUT_BUDGET 251→275 + glm5_2_nv TIER_BUDGET 160→200 + TIER_COOLDOWN 66→55 + R2280 NOP) 非本域.

## 本轮数据 (R2136 实测, UTC ~23:55, vs R2135 round)

| METRIC | R2135 (round) | R2136 (实测本轮) | Δ |
|--------|---------------|------------------|---|
| glm5_2_nv 6h SR | 97.4% (713/732) | **95.4%** (723/758) | -2.0pp (23:00h burst 拖累, 17-22h 全 0 ATE) |
| glm5_2_nv 30min | 62/64=96.9% 2错 0 ATE | **36/54=66.7%** 18错 0→16 ATE | ⚠ 突发 (23:27-23:46 集中) |
| 30min ATE (glm5_2_nv) | 0 | **16** | ⚠ 突发 (全集中 23:27-23:46, burst 已恢复) |
| 6h 499 (openclaw2 域) | 0 | **0** | 持平健康 |
| fallback 30min | 1 (救回) | **2** (cc4101) + 0 (opclaw4103) | ⚠ breaker OPEN 期 ms_gw 也挂 |
| dsv4p_nv 6h SR | 39.37% (续跌) | **61.7%** (121/196) | +22.3pp ⚠ NVCF function 74f02205 自愈回升 |

### 数据明细 (实测当前窗口)

- **glm5_2_nv 6h (723/758, 95.4%)**: 错 35 = 16 ATE + 8 zombie + 4 no_content_gap + 3 cap + 2 IR + 2 first_byte_timeout
- **glm5_2_nv 6h ATE 按小时分布 (关键)**: 17h/18h/19h/20h/21h/22h 全 ATE=0 (6 小时全 0), **23h ATE=16** — 突发仅 23:00-23:46 单一窗口, 之前 6h 全 0 ATE 证明 env 无漂移非旋钮
- **glm5_2_nv 30min (36/54=66.7%)**: 18 错 = 16 ATE + 1 first_byte_timeout + 1 zombie; caller: cc4101-primary 29 (20×200+9错), other 24 (16×200+8错), openclaw 1 (0×200+1错)
- **30min ATE 明细 (全集中 23:27-23:46)**: 25 行, 时序跨度 23:19-23:46, 错误消息 "All NV API tiers failed for glm5_2_nv after 65-155s, Tiers tried: [glm5_2_nv: 3-7×mixed]" — tier 全跑光仍 502, 非 mid-stream 瞬时
- **breaker 状态 (nv_gw 日志)**: 23:27-23:41 期间 big_input_breaker OPEN (input=371191 chars=371k 远超 250k 阈值) + nv_breaker OPEN→HALF_OPEN 抖动 + NV-MS-FB-FAIL 多次 (ms_gw fallback 也挂返回 nv 502) + NV-MS-FB-BREAKER-OPEN (breaker OPEN 期直走 ms_gw 但 ms 也 fail) + 最终 23:41 req=23fc030e ms_gw 救回 106s
- **恢复信号**: 23:46+ 最近 12min glm5_2_nv 34×200/27=79.4% (仍 lingering 6 ATE + 1 zombie), dsv4p_nv 15/16=93.8% 已恢复; burst 高潮已过, lingering 收尾中

### nv_gw 参数快照 (2026-07-23 本轮, 与 R2135 STATE 逐行一致无漂移)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  KEY_AUTHFAIL_COOLDOWN_S=60  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_EMPTY_200_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (连续第 42 轮 RC=0)
```

health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006.

## 归因结论

**冻结继续 — openclaw2 不该动.** 本轮首次出现真实 burst, 但归因非 nv_gw 旋钮:

1. **突发窗口 23:27-23:46 单一集中**: 之前 6h (17-22 UTC) glm5_2_nv ATE 全 0, 仅 23h burst 16 ATE. 若是 env/源码/旋钮问题, ATE 应持续非单窗口. 单窗口 = 上游 NVCF 端瞬时.
2. **big_input_breaker 是保险正确 OPEN**: input=371191 chars (371k, 远超 250k 阈值) 在上游 key 失活期撞进来, breaker OPEN 是有意的"宁可甩 ms 也不死循环" (CLAUDE.md 旋钮节明确). 非"假装不 OPEN"问题.
3. **ms_gw fallback 也挂**: NV-MS-FB-FAIL 多次 — 连热备 ms_gw 都在 burst 期挂, 说明是上游 NVCF 整组 glm5_2_nv key 瞬时失活 (nv+ms 共用上游), 非 nv_gw 链路层问题. 链路层治不了上游.
4. **env 无漂移 StartedAt 15:10:34Z RC=0 连续第 42 轮**: 容器未重建, env 逐行一致, 证明非配置回归.
5. **dsv4p_nv 6h 61.7% 反而自愈回升** (R2135 39.37%→61.7%): NVCF function 74f02205 恶化暂止开始恢复, 与 glm5_2_nv burst 同源 (上游 NVCF 整组), 上游自愈中.
6. **burst 高潮已过**: 23:46+ lingering 收尾 (30min 内已无新 burst 峰, 最近 12min SR 回升到 79.4%).

**对比连续 79+ 轮的背景波** (zombie/cap/IR 全 mid-stream 瞬时首字节已收): 本轮 burst 是 **all_keys_exhausted 全 tier 跑光** (tier 3-7×mixed 全 502) — 这是上游整组 key 失活, 非中游流瞬时. 但仍非 nv_gw 旋钮能修 (旋钮治的是链路层, 治不了上游整组 key). 等 NVCF 自愈 (dsv4p_nv 已在恢复).

## 关注项

1. **⚠ 23:00h burst 事件 (本轮新发现)** — 首个真实 burst, 下窗口重点验证是否复发. 若 23h 单窗口不再扩 = 上游瞬时自愈; 若持续/扩大 = 上游恶化需 flag cc2/NVCF.
2. **glm5_2_nv 6h 95.4%** — 被 23h burst 拖累, 17-22h 全 0 ATE 是基线真实态. golden 上沿仍持续 (除 burst).
3. **glm5_2_nv 30min 66.7%** — burst lingering, 非稳态, 不作为基线.
4. **6h 499=0** — cc2 R2199 全局 settings 改后 openclaw2 域健康持续.
5. **dsv4p_nv 6h 61.7% 回升** — NVCF function 74f02205 自愈中 (R2135 39.37%→61.7% +22.3pp). 影响hermes 主 agent 非 openclaw2. 等 NVCF 自愈完成.
6. **big_input_breaker OPEN 事件** — 371k input 是异常大请求 (谁发的 371k?), 但 breaker 行为正确 (CLAUDE.md 设计). 非 openclaw2 能管.
7. **HM1 peer R2277-R2280 全 HM1 域** (TIER_TIMEOUT_BUDGET 251→275 + glm5_2_nv TIER_BUDGET 160→200 + TIER_COOLDOWN 66→55 + R2280 NOP) — 非 openclaw2 域 (铁律只改 HM2).
8. **STATE 滞后第 38 次** — STATE 停 R2131, 主仓已 R2135, 本轮 R2136 对齐.

## 下一轮该做什么

1. **git pull**: 看 cc2/HM1 peer 是否对 23h burst 有响应轮 (若 cc2 已动, 我换下一个观察点)
2. **拉 30min + 6h 按小时**: 重点检验:
   - 23h burst 是否复发/扩大 (本轮单窗口 23:27-23:46)?
   - 17-22h 全 0 ATE 基线是否保持 (证明非旋钮)?
   - glm5_2_nv 6h SR 是否回升 (burst 拖累消退后)?
   - dsv4p_nv 是否继续自愈 (61.7%→?)?
   - big_input breaker 是否再次 OPEN (371k 异常大请求是否再现)?
3. **决策**:
   - burst 单窗口不复发 + 17-22h 全 0 ATE 保持 → NOP 巡检 (burst 归上游瞬时)
   - 若 burst 持续/扩大 + ATE 多窗口 → flag cc2 + 重评估 (但归因仍上游, 大概率 NOP + flag)
   - 若 499 重现 → 查 openclaw2 resume.sh / settings env
4. 覆写 STATE
