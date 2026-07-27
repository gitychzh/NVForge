# R-keyretry-post1 (hm2_cc2): 巡检验证轮 — R-keyretry 同 key 重试部署后效果评估

> 2026-07-27 09:35 CST. 验证轮 (上一轮 R-keyretry 用户直接指令部署 NVCF key1 同 key 重试 3x
> 2s→4s→8s). 本轮拉部署后数据评估重试效果. **结论: NOP 记数据, 0 改动 0 restart.**

## 数据 (改前必有数据)

### R-keyretry 部署确认
- commit `24d435c` 时间 09:28:53 CST, 实际 restart 生效 ~09:26 CST (STATE.md 记录)
- env 实测生效: `NVU_CALLER_RETRY=3`, `NVU_CALLER_RETRY_INTERVALS=2,4,8` ✓
- /health OK: `nv_default_model=glm5_2_nv`, nv_num_keys=5 ✓
- fixed key 映射: `NVU_CALLER_KEY_MAP=cc4101-primary:1` → 日志显示 `fixed key=k2` (key1 索引→k2)
- cc4101: `PRIMARY_HEADER_TIMEOUT=60`, `CC4101_STREAM_TOTAL_DEADLINE_S=580`, `UPSTREAM_IDLE_TIMEOUT=150`

### 部署后短窗口 (~09:26-09:34, ~8min)
- cc2 (cc4101-primary) nv_gw 侧: 5×200 / 0 失败 → nv_gw 侧 SR 100% (但不含重试后 fallback 的)
- cc4101 真 fallback (部署后): 3 次 (1f3f0024, a5d9ed8c, d9eabb27) 全 ms_gw 成功

### 30min 窗口 (08:46-09:32, 含部署前)
- nv_gw 整体: 56×200 / 5×502 → SR 91.8%
- cc2 (cc4101-primary): 21×200 / 2×502 → SR 91.3% (2 失败: all_tiers_exhausted×1 + buffer_exhausted×1)
- nv_gw 整体错误: all_tiers_exhausted×3 + buffer_exhausted×1 + zombie_empty_completion×1 (zombie 非 cc2)
- cc4101 真 fallback (30min) = 1 (部署前 5a744824 timeout→fb ms_gw 成功)

### 6h 窗口 (绝大部分部署前, 不能评估 R-keyretry)
- cc2 nv_requests: 390×200 / 5×502 / 1×499 → SR 98.5% (390/396)
- cc2 错误分类: buffer_exhausted×4 + all_tiers_exhausted×1 + client_gone_during_flush×1
- cc_requests error_type: 538×空(成功) / 52×stream_total_deadline / 9×client_gone_mid_stream / 1×server_5xx

### R-keyretry 重试统计 (--since 1h, 含部署前测试 644bbd2b)
- 1 次就成功 (NV-GLM52-SUCCESS): 2 个
- 触发 RETRY-SLEEP 的请求数 (去重 req=): 5 个
- CHAIN-FAIL (3 次全败): 5 个
- **重试后成功 (有 RETRY-SLEEP 且后续同 req SUCCESS): 0 个** ← 关键: 0 救回

### hourly 分桶 (post7 修正后正确查法, 确认无 R-keyretry 副作用)
- stream_total_deadline: 02h=4 / 03h=9 / 04h=8 / 05h=8 / 06h=4 / 07h=8 / 08h=8 / 09h=3(进行中)
  → 范围 3-9/h 波动, 无骤升骤降, 9h 才 3 (未满). 52×/6h=8.7/h (post6 报 7.8/h, 范围一致)
- client_gone (BUG-A 家族): 02-04h 各1 / 06h=3 / 07-09h 各1 → 共 9×/6h, SDK 131s 墙波动正常

## 关键发现: R-keyretry 的两个致命局限 (本轮新认知, 下轮必读)

部署后 ~8min 观察到的 R-keyretry 失效分两类, 覆盖了当前 NVCF 故障的两种主要形态:

### 场景1: NVCF 快速错误 (429/502), 重试跑但全败
- 样本: 9ebebe23, 6a4f9a0c
- 链路: nv_gw CALLER_BIND fixed key=k2 → attempt1 KEY-FAULT → sleep 2s → attempt2 KEY-FAULT →
  sleep 4s → attempt3 KEY-FAULT → CHAIN-FALLBACK → all_keys_exhausted → `NV-MS-FB-ATTEMPT` (nv_gw 内部 fallback ms_gw)
- 9ebebe23 实测: 09:28:47 attempt1 → 09:29:07 CHAIN-FAIL = 20s (含 6s 间隔 + ~14s 3次NVCF调用)
- 日志铁证: `NV-GLM52-CHAIN-FAIL tier=glm5_2_nv all 5 keys + modes exhausted, last_mode=integrate_us_rr`
  → **NVCF 全面故障 (5 key 全挂), 同 key 重试 3 次也救不回** (符合 STATE.md 关键认知第5条预测)
- 副作用: 每个失败请求多花 ~20s 才 fallback ms_gw (但 in chain budget 120s 内, 可接受)

### 场景2: NVCF ttfb >60s, cc4101 pre-empt, 重试根本不跑
- 样本: 1f3f0024 (60.084s), a5d9ed8c (60.092s), d9eabb27 (60.051s)
- 链路: cc4101 → nv_gw → NVCF ttfb>60s → **cc4101 PRIMARY_HEADER_TIMEOUT=60s 先判 PRIMARY-FAIL** →
  `PRIMARY-FAIL-SKIP-CIRCUIT: primary timeout after 60084ms < chain budget 120s, likely cc4101
  pre-empted nv_gw retry, NOT counted toward circuit` → cc4101 自己 fallback ms_gw 成功
- **nv_gw 的同 key 重试 (2s→4s→8s) 根本来不及触发**, 因为 cc4101 在 60s 已经 pre-empt
- 这正是 CLAUDE.md BUG-A "cc4101 pre-empted nv_gw retry" 问题 — R-keyretry 对 ttfb 超时类故障完全无效

### 结论: R-keyretry 的有效场景极窄
R-keyretry 只在 **"NVCF 个别 key 间歇性快速错误 (429/502, 非 ttfb 超时) + ttfb<60s + 非全面故障"**
的窄场景下有效. 当前 NVCF 故障主要表现为:
1. ttfb 超时 (>60s 被 cc4101 pre-empt, 重试不跑) — 场景2, 部署后 3 个 fallback 全是这种
2. 全面 key 耗尽 (5 key exhausted, 同 key 重试也救不回) — 场景1, 部署后 2 个重试全败
→ **当前 NVCF 环境很少匹配 R-keyretry 有效场景, 故 0 救回**

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 91.3% (21/23, 2 失败全 NVCF 故障非 R-keyretry 退化) | ⚠ 低于 post6 100%, 根因 NVCF 故障非 R-keyretry |
| cc4101 真 fallback | 1 (30min) / 3 (部署后 8min) | ⚠ 部署后 fb 升, 根因 NVCF ttfb 超时场景2 |
| 无新错误类型 | all_tiers_exhausted + buffer_exhausted (已知) | ✓ |

→ SR/fb 未达 post6 基线, 但根因是 NVCF 故障 (场景1+2), 非 R-keyretry 引入的新问题.
R-keyretry 逻辑正确运行 (重试间隔/次数/KEY-FAULT 记录全对), 只是当前环境不匹配其有效场景.
**部署才 ~8min, 样本极小, 0 救回但都是 R-keyretry 的无效场景 → NOP 记数据, 不改码不调参.**

## 本轮改了什么
**0 改动 0 restart** (NOP 巡检验证轮). 只拉数据评估 R-keyretry 效果.

## 决策依据 (符合 STATE.md "下一轮该做什么" 第5条)
STATE.md 关键认知第5条: "若 SR 无变化 (NVCF 持续 429/超时, 重试也救不回) → 记数据, NOP, 不再调参"
本轮实测: 5 个触发重试请求 3 次全败, 0 救回 (场景1 全面故障 + 场景2 ttfb超时 pre-empt).
部署太短 (8min) 不能下"重试无效"最终结论, 但当前 NVCF 环境确实不匹配 R-keyretry 有效场景.

## 下轮建议
1. **等部署满 30min-1h 再拉数据**, 看是否有 R-keyretry 救回的案例 (需 NVCF 部分恢复, 个别 key 间歇故障)
2. **若持续 0 救回** → R-keyretry 在当前 NVCF 环境下无收益, 建议评估:
   - 回滚 env `NVU_CALLER_RETRY=0` (即刻生效, 不改码) 消除场景1 的 20s 无效延迟
   - 或保留 (用户直接指令部署, 回滚决策应由用户/更长数据驱动)
3. **盯 cc2 SR + cc4101 fb 三阈值**: 若 NVCF 恢复后 SR 回 100%/fb=0, 说明 R-keyretry 无害保留;
   若持续退化, 评估场景1 延迟是否值得.
4. **不碰 40007** (ms_gw 重启热备, 本轮 fallback 全靠它救回 3 个请求)
5. 铁律: 改前数据, 改后验证, 聚焦 40006, 只改 HM2, 写入仓库, 尽量多走 glm5_2_nv 少 fallback.

## 回滚锚点 (R-keyretry, 上一轮建立, 本轮未碰)
- env: `NVU_CALLER_RETRY=0` (回退 max_attempts=1, 即刻生效, 不改代码)
- 源码: `cp upstream.py.bak.R-keyretry upstream.py && docker compose restart nv_gw`
- compose: `cp docker-compose.yml.bak.R-keyretry docker-compose.yml && docker compose up -d nv_gw`

## 关联
- 上一轮: R-keyretry (commit 24d435c) — 同 key 重试 3x 部署
- 上上轮: R-buffer-post7 (commit 9596fe1) — 巡检 + 修正 cc_requests.ts 时序查询方法论
- CLAUDE.md BUG-A: cc4101 pre-empted nv_gw retry (场景2 根因, SDK 客户端墙/PRIMARY_HEADER_TIMEOUT)

HM2 only. Co-Authored-By: Claude <noreply@anthropic.com>
