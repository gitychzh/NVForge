# R1199: HM2→HM1 — NOP (67th chain of R1133, zombie-only, all params floor/optimal, NVCF content-filter not config-fixable)

## TL;DR
False trigger (cron script: "这是我提交的, 不触发"). 6h: 31req/19OK(61.3%)/12zombie. All glm5_2_nv integrate, NVCF content-filter stop+12chars, input_chars 173K avg. Gateway detection+error-chunk correct. dsv4p_nv 0 traffic 22h. ms_gw 0 traffic. 0 tier_attempts. Zero param. 铁律:只改HM1不改HM2.

---

## 一、触发分析

- **cron 脚本输出**: `"这是我提交的, 不触发"`
- **最新 commit author**: `opc2_uname` (HM2)
- **HM2 git HEAD**: `9be4a43 R1198: HM2→HM1 — NOP...`
- **HM1 git HEAD**: `fbf0e43 R821` (377 轮落后)
- **判定**: 误触发 — HM1 未提交任何新内容。cron 派送消息是模板残留（R1044 模式）。67th chain of R1133。

---

## 二、HM1 数据收集（改前必有数据）

### 2.1 Docker Logs（最近 100 行 ≈ 67min 窗口）
- **integrate 路径**: glm5_2_nv 全部，k1-k5 循环，首次尝试全部成功（1-7s）
- **zombie 检测**: 3× zombie_empty_completion（finish_reason=stop, content_chars=12, input_chars 175K-176K）
- **ERROR/WARN**: 无
- **429 / empty_200 / timeout**: 无
- **peer fallback / ms_gw fallback**: 无触发

### 2.2 DB — 6h 窗口（2026-07-11 11:40 → 17:40 UTC）

| 指标 | 数值 |
|------|------|
| 总请求 | 31 |
| 成功 (200) | 19 (61.3%) |
| 失败 | 12 (100% zombie_empty_completion) |
| 路径 | 100% nv_integrate |
| 模型 | 100% glm5_2_nv |
| OK 平均 ttfb | 7,188ms |
| OK 平均 duration | 7,744ms |
| OK 最大 duration | 38,540ms |
| zombie 平均 input_chars | 172,779 |
| ms_gw 流量 | 0 |
| dsv4p_nv 流量 | 0 |
| tier_attempts | 0 |
| fallback_occurred | 0 |

### 2.3 容器状态
- **compose md5**: `7975939c245761e451a8813852dcb9bf`（R1133 以来未变，48h+）
- **容器重启时间**: `2026-07-10T19:03:27Z`（稳定 22h+）

### 2.4 关键参数快照

| 参数 | 值 | 状态 |
|------|-----|------|
| `UPSTREAM_TIMEOUT` | 66 | floor |
| `TIER_TIMEOUT_BUDGET_S` | 198 | floor |
| `MIN_OUTBOUND_INTERVAL_S` | 0 | floor |
| `NVU_PEXEC_TIMEOUT_FASTBREAK` | 1 | optimal |
| `NVU_INTEGRATE_TIMEOUT_FASTBREAK` | 1 | optimal |
| `NVU_EMPTY_200_FASTBREAK` | 2 | optimal (R1031) |
| `TIER_COOLDOWN_S` | 15 | optimal (R1103) |
| `KEY_COOLDOWN_S` | 25 | floor |
| `KEY_AUTHFAIL_COOLDOWN_S` | 60 | optimal (R922) |
| `NVU_CONNECT_RESERVE_S` | 0 | floor |
| `NVU_TIER_BUDGET_DSV4P_NV` | 72 | optimal (R1116) |
| `NVU_TIER_BUDGET_GLM5_2_NV` | 96 | floor |
| `NVU_PEER_FB_SKIP_MODELS` | glm5_2_nv | optimal (R923) |
| `NVU_PEER_FALLBACK_TIMEOUT` | 66 | optimal |
| `NVU_SSLEOF_RETRY_DELAY_S` | 1.0 | floor |
| `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | floor |

---

## 三、决策分析

| 候选参数 | 当前值 | 分析 | 决策 |
|---------|-------|------|------|
| 任意 nv_gw 参数 | floor/optimal | 所有 12 个失败都是 zombie_empty_completion (NVCF content-filter stop+12chars) — code-level 问题，非 config-fixable。OK 请求全部首次尝试成功，延迟正常。0 tier_attempts，0 fallback，0 429，0 empty_200，0 timeout。系统处于稳定最优状态。 | ❌ 全部否决 |

**最终决策**: NOP — 零参数修改，零 compose 修改，零容器重启。所有失败均为 zombie_empty_completion（NVCF content-filter），非配置可修复。系统参数已处于 floor/optimal。

---

## 四、结论

R1199 NOP。67th chain of R1133 (zombie-only false trigger)。HM1 数据与 R1198 一致：31req/19OK(61.3%)/12zombie。glm5_2_nv integrate 全部请求，zombie 均为 NVCF content-filter stop+12chars（~173K input）。网关检测 + error-chunk 正确。dsv4p_nv 0 流量 22h+。ms_gw 0 流量。0 tier_attempts。compose md5 未变 48h+。所有参数 floor/optimal。无优化空间。

**单参数少改多轮。铁律：只改 HM1 不改 HM2。**

## ⏳ 轮到HM1优化HM2
