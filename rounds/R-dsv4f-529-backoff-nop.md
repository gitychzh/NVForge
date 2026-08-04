# R-dsv4f-529-backoff-nop: 529 tier-DEGRADED backoff 尝试 — 依据既有数据回退 (NOP)

**Date:** 2026-08-05
**Container:** dsvf0731_nv40666 (port 40666, HM2)
**Status:** NOP (attempted change deployed then reverted to baseline `R-dsv4f-adaptive`)
**Fallback 状态:** hm4104 primary 故障/超时, 已 fallback 到 `dsv4f0731_ms`; 下一轮回 primary

## 背景 / 动机

`dsvf0731_nv40666` (deepseek-v4-flash 0731, FID 52e1ddb6) 在 3h 窗口内 **529 NVCF overloaded 860 次**, 113 次 `all keys exhausted` (ATE), 159 次成功 (41 首竿 + 118 重试后)。ATE 每次在 **9-45s (avg 18.6s)** 内耗尽全部 5 key, 远低于 180s budget, 且紧接着下一请求立即再次锤打同一 overload burst。

**根因确认**: 529 是账户级 NVCF 服务端过载, **keymgr 只对 429/conn/transport 冷却, 529 不触发任何 key 或 tier 冷却** → 529 burst 时 5 key 无冷却快速 cycle (~11s) 耗尽, fallback 到 ms。

## 尝试的修改 (后回退)

在 `gateway/upstream.py` dynamic all-exhausted handler 增加 `has_529` 检测 + `mark_tier_degraded` 15s backoff (`NVU_DSV4F_529_BACKOFF_S=15`):
- 529 主导耗尽时标记 tier DEGRADED 15s, 下一请求 short-circuit 直接 400 `nvcf_tier_degraded`, 避免 11-18s 空转 cycle。

## 回退依据 (既有数据, 铁律: 改前必有数据)

发现既有 round **`R-dsv4f-backoff-revert`** (2026-08-04) 已实验过 529 backoff 并**数据证实有害**:

| 策略 | SR | avg latency | 502 avg latency |
|------|-----|-------------|-----------------|
| Adaptive (no backoff, 现状) | 80-90% | 10s | 10-44s |
| Adaptive + 2s backoff | **60%** | **14s** | **18-46s** |

结论: *NVCF 529 是账户级持续过载, 在 tier budget (180s) 内不会恢复; 快速换 key (0ms) 反而能在 budget 内多试几次增加命中概率。* **backoff 有害无益。**

我的 tier-DEGRADED 15s 方案与 2s backoff 同属"过载时退避"思路, 存在同样的 SR 下降风险——15s 冷却窗口内即使 NVCF 已恢复也会被 short-circuit 到 ms, 即 SR 损失。既有数据不支持该方向, 故采纳 NOP 而非重蹈覆辙。

## 数据 (本轮, 3h 窗口)

- 529 (`529_nv_overloaded`): 860
- DYNAMIC-SUCCESS 首竿: 41; 重试后: 118 (合计 159)
- DYNAMIC-FAIL all keys exhausted: 113
- keymgr 429: 仅 20 (base=max=120s), 非主导
- DEGRADED-SKIP: 0 (当前无 tier short-circuit 触发)

## 操作步骤

1. Backup `upstream.py.bak.R529-backoff.*` (已删)
2. Edit `upstream.py` + `docker-compose.yml` 加 `NVU_DSV4F_529_BACKOFF_S=15`
3. `docker compose up -d dsvf0731_nv40666` (recreate, env 生效), `/health` OK, env 确认
4. 发现 `R-dsv4f-backoff-revert` 反证 → **回退**: 还原 upstream.py + 移除 env
5. 再次 `docker compose up -d` (recreate, env 清除), `/health` OK, env 确认 REMOVED
6. 删除 backup 文件

## 验证 (回退后)

- `docker exec dsvf0731_nv40666 env | grep DSV4F_529` → 无 (REMOVED, good)
- `curl http://localhost:40666/health` → `{"status":"ok", ...}`
- 容器 `Up` (recreated)
- upstream.py lint OK, 回退 diff 干净

## 下一步建议

- **529 是 NVCF 账户级过载, 非本容器可调**。当前 `R-dsv4f-adaptive` (pexec-first + 快速 cycle) 已被数据证明最优, 保持不动。
- 若 529 burst 持续影响 SR, 优先考虑**上游侧** (额外 NVCF key / 不同 egress IP / 换 FIFID), 而非本容器退避逻辑。
- 下一轮 hm4104 primary 恢复后回归主链验证。