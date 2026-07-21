# R2175 (hm2_cc2): NOP 巡检轮 — 稳态延续, 0 改动 0 restart

## 上下文
全新 session 接棒。STATE.md 完整(未被并发改/清), 上一轮 R2174 hm2_cc2 NOP 巡检
已重建基线 + 6h+ 稳态确认。本轮继续巡检, 盯 STATE "下一轮"定义的三触发改动阈值。
主仓 git 最新 `aa4d447 R2174 (HM2->HM1): TIER_COOLDOWN_S 20->18` 是 HM1 peer 轮
(only HM1), 非本域, HM2 不参与, 保持 HM2 稳态正确 (铁律: 只改 HM2, 不改 HM1)。

## 数据 (HM2, 30min window)
- nv_requests: 76 请求 / 68 OK(200) / 8 错(502) → **SR = 89.5%** (68/76)
- by model:
  - glm5_2_nv: 59 OK / 2 错 → **96.7%** SR (2 错: 1 all_tiers_exhausted + 1 zombie_empty_completion)
  - dsv4p_nv: 9 OK / 4 错 → 69% SR (4 错全 all_tiers_exhausted, NVCF function 74f02205 全挂非本域, 已知良性/R1719 起 dsv4p_nv 长期容忍)
- 6 错全 NVCF 上游无害类: 4 all_tiers_exhausted + 2 zombie_empty_completion
- 无 content_filter / timeout / conn / 429 / NV-ANTH-BREAKER-FAIL
- nv_gw BREAKER / big_input / nv_breaker: 30min **0 条触发**
- fallback: cc4101 报 4 次 (FALLBACK-OK), 全 NVCF 慢类 (cf5d1242 RemoteDisconnected + 790d6793 120s ttfb timeout) 被 ms_gw 兜住, **0 真中断**
- nv_requests.fallback_occurred=true 8 条 (含 cc4101 兜底 + nv_gw 内部 tier 切换)
- 75s_timeout: **0** (R2154 动态 header timeout 持续生效, cc4101 无误杀)
- STREAM-STALL-FAIL / CC4101-UPSTREAM-ERROR-SEEN: 0

## 容器 / 参数 (无漂移)
- nv_gw: RestartCount=0 StartedAt=2026-07-21T01:44:55Z (Up 8h, 与 R2174 一致)
- cc4101: RestartCount=0 StartedAt=2026-07-21T05:28:51Z (Up 4h, 与 R2174 一致)
- env 与 R2174 快照逐项一致: KEY_COOLDOWN_S=60 / UPSTREAM_TIMEOUT=90 /
  TIER_TIMEOUT_BUDGET_S=180 / TIER_COOLDOWN_S=180 / NVU_FORCE_STREAM_UPGRADE=0 /
  NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_BIG_INPUT_FAIL_N=1 等

## 决策: NOP 巡检, 0 改动 0 restart
STATE "下一轮"三触发改动阈值 vs 当前:
| 指标 | 当前 30min | 阈值 | 判定 |
|---|---|---|---|
| SR | 89.5% | 跌破 85% | 在阈值之上 ✅ |
| fallback | 4 条全 NVCF 慢 | >5 | 在阈值之下 ✅ |
| 新错误类型 | 0 (仍 ATE+zombie) | zombie上升/BREAKER真触发 | 无 ✅ |

三条件全不满足 → 数据不支撑调参 → 冻结, NOP 巡检不改代码。
glm5_2_nv SR 96.7% 稳态带内 (R2157 为 98.4%, 同带宽内正常波动)。
四重佐证 nv_gw 稳: 6 错全上游无害类 / 无参数误杀 / breaker 不触发 / 容器无漂移。
改了反而破坏 R2154 以来建立的稳定带。

## 验证
0 改动 0 restart 无需验证改动。curl /health ok (nv_num_keys=5, nvcf_pexec_models 正常).
docker ps 全 Up. DB 30min 窗口稳态带内. 参数 env 与基线逐项一致.

## commit
本轮 R2175 hm2_cc2 NOP 巡检, 仅 rounds/R2175_*.md 记录, 0 源码 0 env 改动。
