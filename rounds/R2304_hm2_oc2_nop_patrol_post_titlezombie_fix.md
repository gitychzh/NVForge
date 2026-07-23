# R2304_hm2_oc2 巡检 — R2302 title-zombie 修复后首轮 + glm5_2_nv 30min 0 ATE 0 zombie

**轮号**: R2304_hm2_oc2  **日期**: 2026-07-24 (HM2)
**类型**: NOP 巡检轮 (nv_gw env/源码连续冻结, 0 改动 0 restart)
**背景**: R2302 (HM2 only) 修了 openclaw2 title-zombie 根治 (瘦身 resume.sh prompt 4k→1.6k + STATE 不预贴入).
本轮 = R2302 修复后首个 openclaw2 巡检轮 (R2161→R2302 之间因 title-zombie openclaw2 无法完成轮, 有空白). prompt 改主动 cat STATE/CLAUDE.md 接任务, 本轮验证行为正常.

## 改前数据 (改前必有数据, 0 改动故 = 巡检数据)

### 30min (本域 glm5_2_nv, 当前窗口)
- 72×200 + 8×502 = 91.0% SR (80 req 全 glm5_2_nv, 无 kimi/dsv4p 串入)
- 8 错 **全 stream_absolute_cap** (mid-stream 背景波, 首字节已收) — **0 ATE 0 zombie 0 IR**
- fallback: cc4101=1 (req=4c16780a PRIMARY-FAIL 60s header timeout, **SKIP-CIRCUIT** 不计熔断 < chain budget 120s, pre-empted nv_gw retry → FALLBACK-OK ms_gw 2.5s) + opclaw4103=2 → **0 真中断**

### 6h (含上游瞬态, 非稳态全窗)
- glm5_2_nv: 718×200 + 43×502 = **94.3%** (761) | kimi_nv: 218×200 + 50×502 = 81.3% (HM1 peer 域, 非本域)
- 6h 错分类: 34 ATE + 30 zombie + 27 cap + 1 IR = 92
- **ATE/zombie 非风暴簇**: 按小时散布 10:00-15:00 UTC (10:00=5ATE, 11:00=12ATE+5z, 12:00=16ATE+1z 峰,
  13:00=5ATE+12z, 14:00=6ATE+8z, 15:00=4z) — 12:00 峰后衰减, 30min 已归零. = 上游 NVCF key 瞬时压力 (tier: pexec_429=76, NVCFPexecRemoteDisconnected=25, SSLEOF=13), 非旋钮可治.
- 6h 499 (本域): **0** (R2149 锁定 model=glm5_2_nv 零退化保持; 502=93 全是 43 glm5_2_nv+50 kimi_nv)

### 60min/2h glm5_2_nv (恢复趋势)
- 60min: 147×200 + 16×502 = 90.2% | 2h: 278×200 + 28×502 = 90.8% — 与 30min 91.0% 一致 ~90% 平台 (vs R2161 98.4% golden 上沿, 略降但 30min 0 ATE 0 zombie 干净)

## nv_gw 参数快照 (无漂移, 与 R2139/R2161 STATE 逐行一致)

```
KEY_COOLDOWN_S=60  TIER_COOLDOWN_S=180  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_TIER_BUDGET_DSV4P_NV=180  NVU_TIER_BUDGET_GLM5_2_NV=120
UPSTREAM_TIMEOUT=90  TIER_TIMEOUT_BUDGET_S=180
NVU_FORCE_STREAM_UPGRADE=0  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
MIN_OUTBOUND_INTERVAL_S=10  NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_THRESHOLD=250000  NVU_BIG_INPUT_MODELS=glm5_2_nv
NVU_EMPTY_200_FASTBREAK=3  NVU_PEXEC_TIMEOUT_FASTBREAK=3
StartedAt=2026-07-22T15:10:34Z  RestartCount=0  (容器连续未重建)
```
health: nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv, port=40006, status=ok.

## 归因结论: 冻结继续, NOP 巡检

1. **30min 本域 0 ATE 0 zombie 0 IR** — 8 错全 stream_absolute_cap (mid-stream 背景波, 首字节已收未触发 fallback 真中断).
2. **6h ATE/zombie 非风暴**: 散布 10:00-15:00 衰减型, 12:00 峰后归零, = 上游 NVCF key 429 压力 (tier pexec_429=76), 链路层治不了, 旋钮无效.
3. **fallback 0 真中断**: cc4101 1 次 pre-empted SKIP-CIRCUIT (60s<120s 不计熔断) 救回 2.5s.
4. **499=0** 持续 (R2149 锁定 model=glm5_2_nv 零退化).
5. **env 无漂移** StartedAt 07-22T15:10:34Z RC=0 容器连续未重建.
6. **kimi_nv 6h 81.3%** = HM1 peer 域 (R2300-R2302 HM2->HM1 bridge 轮在调 kimi_nv budget, 非本域, 铁律只改 HM2 nv_gw).

三阈值全不满足 → 冻结. 0 改动 0 restart. HM2 only.

## 下一轮

1. git pull 看 HM1 peer (kimi_nv 连调下一轮) / cc2 / hermes2 新轮.
2. 拉 30min+6h: 看 6h ATE/zombie 瞬态是否彻底滑出 (12:00 峰滑出 6h 窗后 6h SR 应回升 golden); 30min 是否保 0 ATE 0 zombie; 499 是否保 0; fallback 是否 0 真中断.
3. 决策: 30min 0 ATE 0 zombie + 499=0 + 0 真中断 → 继续 NOP; 若 ATE/zombie 再簇成风暴 → 记录观测不动 (旋钮无效已证); 若 499 重现 → 查 openclaw2 settings/resume.sh.
4. 覆写 STATE (STATE 仍滞后, 本轮补对齐至 R2304).
