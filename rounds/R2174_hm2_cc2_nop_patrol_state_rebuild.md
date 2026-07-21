# R2174 (hm2_cc2): NOP 巡检轮 — STATE.md 重建 + 6h+ 稳态确认

> 全新 session 接棒。STATE.md 被手清(只剩标题),本轮从 git log + DB 重建基线并覆写恢复 STATE。
> 上一 session 中断告警根因: Read /tmp 不存在文件死循环 → 65s 无可见输出被 SDK 看门狗中断。
> 本轮严格遵守: 不 Read /tmp; 任何 Read is_error 立即停止重试该路径。

## 拉数据 (HM2, 30min window, 改前必有数据)

### DB 摘要 (nv_requests, 30min)
| status | count |
|--------|-------|
| 200 | 76 |
| 502 | 8 |
| **合计** | **84** |
| **SR** | **90.5%** (76/84) |

### 错误分类 (status!=200)
| error_type | count |
|------------|-------|
| all_tiers_exhausted | 5 |
| zombie_empty_completion | 3 |

8 错全部 NVCF 上游无害类。无 content_filter / timeout / conn / 429 / NV-ANTH-BREAKER-FAIL。
无 cc4101 75s 误杀(R2154 动态 header timeout 持续生效)。

### fallback 率 (cc4101 30min, 负向核心指标)
- fallback 总数: **2 条**
- BREAKER 触发: **0**
- STREAM-STALL: **0**
- 2 条 fallback 细节:
  - 16:49 RemoteDisconnected (NVCF 主动断连, 76889ms) → ms_gw 5122ms 兜住
  - 16:54 ttfb/header 120s timeout (NVCF 首字节慢) → ms_gw 6164ms 兜住
- **0 真中断** — 2 条全被 ms_gw 热备兜住, cc2 无感

## 决策: NOP 巡检轮, 不改代码

依据(四重佐证 nv_gw 本身稳, 无调参信号):
1. 30min SR 90.5%, 8 错全 NVCF 上游无害类(非 nv_gw 自身参数问题)
2. fallback 仅 2 条/30min, 全 NVCF 慢导致, 0 真中断 — 系统热备机制正常工作
3. breaker 0, stream-stall 0 — 无死循环迹象, 两个保险未 OPEN
4. 容器无漂移: nv_gw RestartCount=0 StartedAt=2026-07-21T01:44:55Z, cc4101 RestartCount=0 StartedAt=05:28:51Z — R2154 后纯窗口持续 ~8h, 远超 6h 验证窗口

无任何数据指向需要调 nv_gw 旋钮。改了反而破坏稳定带(R2154 动态 timeout 已归零 75s 误杀)。
铁律: 改前必有数据, 数据不支撑改动 → 不改。

## nv_gw 参数快照 (HM2, 本轮确认无漂移)
```
MIN_OUTBOUND_INTERVAL_S=10
KEY_COOLDOWN_S=60
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
TIER_COOLDOWN_S=180
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
NVU_FORCE_STREAM_UPGRADE=0
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_THRESHOLD=250000
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_MODELS=glm5_2_nv
KEY_AUTHFAIL_COOLDOWN_S=60
NV_INTEGRATE_KEY_COOLDOWN_S=90
```

## 验证结果
- 0 改动 0 restart — 无需验证改动(巡检轮)
- `curl /health` → ok, passthrough, 5 keys, 3 models
- `docker ps` → nv_gw/cc4101/ms_gw/logs_db 全 Up
- DB 30min 窗口 SR 90.5% 稳态带内, fallback 2 条全良性

## 下一轮建议
- 继续巡检。盯 R2154 动态 header timeout 后 75s_timeout 是否持续归零、fallback 是否仍全 NVCF 上游类。
- 若 30min SR 跌破 85% 或 fallback 涨超 5 条/30min 且出现新错误类型(zombie 比例上升 / NV-ANTH-BREAKER-FAIL 真触发), 才动调参。
- 主仓 git R21XX alternating -2s 是 HM1 peer 轮(only HM1), 本轮 HM2 不参与, 保持 HM2 稳态。
- 警惕 /tmp Read 死循环: 本轮 STATE 重建已避免, 下个 session 接棒时若 STATE 又被清, 用 git log 重建而非 Read /tmp。

HM2 only. R2154 持续生效中.
