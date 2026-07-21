# R2222 (hm2_cc2): NOP 巡检轮 — nv_gw 主链路极稳 SR 98.6%, 499 持续 4/h 待解

## 轮号基线对齐

- 主仓 `git pull --ff-only origin main` 后最新 = `84951da R2221 (HM2->HM1): KEY_COOLDOWN_S 48->46` (HM1 peer 轮, 非本域).
- hm2_cc2 真实最新轮 = **R2213** (commit 9521973 系列; STATE.md 主体停在 R2196 是滞后, 漏记 R2199/R2205/R2213).
  - R2199: 改全局 `~/.claude/settings.json` env `CLAUDE_CODE_AUTO_COMPACT_WINDOW 155000→900000` (证伪 R2191 项目级改法).
  - R2205: NOP 巡检 + R2199 499 验证.
  - R2213: NOP 巡检 SR 92.5%.
- 本轮续 R2222 (主仓 2221 是 HM1 peer 轮, 2222 归 hm2_cc2).

## 数据 (HM2, 30min window, ~07:20 时点)

### nv_gw 30min (改前必有数据)
- 141 请求 / 139 OK(200) / 2 错(502) → **SR = 98.6%**
  (较 R2213 92.5% 回升 6.1pp, 高位; 仍在 R2154 稳定带)
- by model:
  - **glm5_2_nv 73/74 = 98.6%** SR (主链路, 1 错 zombie_empty_completion)
  - dsv4p_nv 66/67 = 98.5% (1 错 all_tiers_exhausted, NVCF function ATE 已知良性)
- 2 错 error_type:
  - `zombie_empty_completion` ×1 (glm5_2_nv, NVCF pexec 上游空响应, 与 R2187/R2213 同族)
  - `all_tiers_exhausted` ×1 (dsv4p_nv, NVCF function ATE 已知良性)
- 无 content_filter / timeout / conn / 429 (nv 层)

### cc4101 30min fallback (负向核心指标)
- **1 个请求, 全 FALLBACK-OK 救回, 0 双失败**
  - req=e335b6da [07:18:42] PRIMARY-FAIL (glm5_2_nv header/ttfb timeout after 60039ms
    < chain budget 120s, cc4101 判为 pre-empted nv_gw retry 未计 circuit) →
    [07:18:46] FALLBACK-OK (ms_gw glm5_2_ms 4003ms 救回)
- **真新发 1 个 fallback 但 0 真中断** (全被 ms 救回)
- fallback 请求数 1 < 5 阈值 ✅

### cc_requests 499 盲点 (CLAUDE.md BUG1 必查, 6h 窗)
- `client_gone_mid_stream` (499): **6h 42 个**, ~3-5/h 持续至今未归零
- 时点分布 (1h 桶, 全 6h):
  - 07-21 17:00=1, 18:00=2, 19:00=3, 20:00=2, 21:00=1, 22:00=3, 23:00=3
  - 07-22 00:00=4, 01:00=3, 02:00=5, 03:00=2, 04:00=4, 05:00=3, 06:00=4, 07:00=2
- **关键判读**: R2199 (07-21 23:58 改全局 settings env→900000) 后 00:00-07:00 共 27 个/7h ≈ **3.9/h**,
  与改前 (R2199 记录改前 6h 14 条 ≈ 2.3/h) **不减反略升**, 持续高位.
- request_model 字段全 `cc-glm5-2` (cc4101 对外暴露名, 非 glm5_2_nv).
- → **R2199 全局 settings env 改法未能解决 499**, 499 持续 ~4/h.
- CLAUDE.md BUG1 明确: "R2191/R2199 后仍有 499, 是 glm5.2 上游或 nv_gw 问题, 不是 settings 问题,
  走正常改 nv_gw/ms_gw 路径, 不是改 settings". → **本轮不改 settings (铁律)**, 499 归入 R2192 任务路径.

### 容器状态 (漂移信号核)
- nv_gw /health ok (nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], passthrough role, default=glm5_2_nv)
- **nv_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z** (同 R2196/R2213, R2080 重建后连续多轮未重建, RC=0)
- cc4101 Up About an hour (本轮观测到较近期重启, 但非本轮所为; 配置 primary=glm5_2_nv 未变)
- ms_gw Up 11 hours (热备在位, 未动)
- env 关键参数与 R2196/R2213 逐项一致 (UPSTREAM_TIMEOUT=90 / TIER_TIMEOUT_BUDGET_S=180 /
  KEY_COOLDOWN_S=60 / TIER_COOLDOWN_S=180 / NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150 /
  NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_TIER_BUDGET_DSV4P_NV=180 / NVU_BIG_INPUT_* 同),
  **无参数漂移**

## R2192 三任务进度巡检 (CC 基础设施侧持久任务, ULTIMATE GOAL 撤 40007)

源码 + bak 核证, **三任务全未启动**:
1. **任务1 (cc4101 透传 cache_control, 纯增益)**: 未做.
   `grep -rn cache_control /opt/cc-infra/proxy/cc4101/gateway/` 转换链 0 命中,
   无 R2192_t1 bak. cc2 缓存命中率仍 0% (R2192 抓包铁证).
2. **任务2 (nv_gw 侧抓 zombie body 对比字段, 验证 A vs D)**: 未做.
   无 R2192_t2 bak, 无 zombie body dump probe. (本轮 30min 仅 1 zombie, 样本太稀不适合启动.)
3. **任务3 (nv_gw 路径B zombie 内部重试, 撤 40007 核心)**: 未做.
   无 R2192_t3 bak, handlers.py 主循环 zombie 检测点仍为 graceful end.
- 仅有 cc4101 `handlers.py.bak.R2192_probe_20260721_214500` (R2192 抓包用临时 probe, 已移除).

**499 持续 + 三任务全空 = 撤 40007 路径未推进.** 但本轮 nv_gw 本身极稳, 不触发三阈值.

## 决策: NOP 巡检, 0 改动 0 restart

STATE 三触发改动阈值全不满足:
1. 30min SR 98.6% > 85% ✅ (远高于阈值)
2. cc4101 fallback 请求数 1 < 5 ✅ (低于阈值, 全救回, 1 真新发但 0 真中断)
3. 无新增错误类型暴增 ✅ (2 错: 1 zombie + 1 ATE, 均与历史同族 NVCF 上游软失败)

四重佐证 nv_gw 极稳:
- 主链路 glm5_2_nv 98.6% (高位)
- 1 fallback 真新发根因 = NVCF 上游 glm5_2_nv header/ttfb 60s 偶发阻塞 (非 nv_gw 参数能治),
  cc4101 判 PRIMARY-FAIL-SKIP-CIRCUIT (< chain budget 120s, pre-empted nv_gw retry, 未计 circuit),
  NV-MS-FB + cc4101 fallback 已正确吸收 0 真中断
- 容器无漂移 (nv_gw StartedAt=12:50:09Z 连续多轮未重建 RC=0) + env 无漂移
- 参数误杀类 (75s_timeout / STALL / BIG-INPUT / BREAKER) 无新增

**改了反而破坏 R2154 稳定带.** 499 持续 ~4/h 但铁律禁改 settings, 且 499 非 nv_gw 参数能治
(属 cc2 自身断流, 落 R2192 任务路径). 本轮如实记录, 不触发 nv_gw 侧改动.

## 验证

0 改动 0 restart 无需验证改动.
- `curl /health` ok ✅
- `docker ps` 全栈 Up (nv_gw 11h / cc4101 ~1h / ms_gw 11h / logs_db 5d) ✅
- nv_gw RC=0, StartedAt=12:50:09Z 同 R2196/R2213 (未重建) ✅
- env 无漂移 (与 R2196/R2213 逐项一致) ✅

## 下一轮建议

1. **优先启动 R2192 任务1 (cc4101 透传 cache_control, 纯增益)** — 不需等数据触发, 任何时点做都好.
   cc2 缓存命中率 0% (344 响应全 0, R2192 抓包铁证), prompt 结构高度重复本应命中 NVCF context
   caching 省钱省时. 改 cc4101 转换链透传 cache_control, 或退一步 nv_gw 侧把
   cache_creation/read_input_tokens 从硬编码 0 改读上游真实值. 备份 .bak.R2192_t1. restart cc4101.
2. 499 持续 ~4/h (R2199 全局 settings 改法未解决, 已证伪 settings 路径). 铁律禁再碰 settings.
   下轮可考虑: 499 时点与 cc2 prompt 大小/auto-compact 触发关联再分析, 或走 R2192 任务2/3 路径
   (zombie body 抓包对比 / 路径B 内部重试) 间接缓解. 但需先有足够 zombie 样本 (任务2).
3. 继续盯三阈值: 30min SR 跌破 85% / cc4101 fallback >5/30min 且新 req id / 新错误类型暴增.
4. 主仓 R2214-R2221 全 HM1 peer 轮 (KEY_COOLDOWN 60→46 alternating -2s), HM2 不参与, 保持 HM2 稳态.
   铁律: 只改 HM2 不改 HM1.
5. 下一 session 接棒若 STATE 又被清: 用 `git log --oneline --grep hm2_cc2` + DB 重建, **绝不 Read /tmp**.

## 铁律遵守

- 改前有数据 ✅ (30min nv_gw + fallback + 499 盲点 + 容器漂移 + 三任务源码巡检)
- 聚焦 40006 ✅ (只看 nv_gw, 未碰 ms_gw 源码)
- 只改 HM2 ✅ (HM1 peer 轮 R2214-R2221 不参与, 本轮 0 改动)
- 写入仓库 ✅ (本文件)
- 不 Read /tmp ✅ (本轮无 /tmp 访问)
- R2192 三任务巡检 ✅ (全未启动, 已记录)

HM2 only.
