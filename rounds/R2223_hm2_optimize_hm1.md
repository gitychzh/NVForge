# R2223 (HM2→HM1): KEY_COOLDOWN_S 44→42 (-2s)

## 数据依据 (改前必有数据)

**6h窗口** (至 2026-07-22 07:33 UTC):
- 总请求: 50 (全部 openclaw caller)
- 成功: 40 (80.0% SR) — 持平 R2222
- 失败: 10 = 7 glm5_2_nv zombie + 3 dsv4p_nv ATE (全部 >13h 陈旧, preempted)
- 平均OK延迟: glm5_2_nv 14936ms, dsv4p_nv 26922ms
- glm5_2_nv: 38/38 key_cycle_429s (100% cycling, max=5), 31/38 OK (81.6% SR)
- dsv4p_nv: 12 total, 9 OK, 3 ATE (全部 stale >13h, 0 tier_attempts, preempted)
- 0 fallback, 0 real ATE (3 ATE 全部陈旧 preempted >13h)
- 0 key_cycle_429s on dsv4p_nv, 100% on glm5_2_nv

**30min窗口**:
- 2 total, 1 OK, 1 fail (glm5_2 zombie)

**Docker logs**:
- glm5_2 zombie SSLEOFError on k3, auto-advance → k4/k5, sent finish_reason=content_filter SSE chunk
- 无其他异常

## 优化决策

**交替 KEY→KEY (skip TIER=0)**: 遵循 R2219→R2220→R2221→R2222 交替模式.

KEY_COOLDOWN_S: 44→42 (-2s).

**预算验算**: KEY(42)+TIER(0)+DSV4P_BUDGET(94)=136 << 157 TIER_TIMEOUT_BUDGET (21s margin).
dsv4p min per-key: 42+24=66 << 94 BUDGET_DSV4P (28s margin).

**风险评估**: SR 80.0% 持平 R2222, 零回退. 3 ATE 全部 >13h 陈旧 preempted (0 tier_attempts), 非本轮引入. 7 zombie 是 glm5_2 NVCF 服务端问题 (content_filter), 非本地配置可修. -2s 保守.

**铁律**: 只改HM1不改HM2. 单参数.

## 执行验证

- compose line 500: `KEY_COOLDOWN_S: "44"` → `"42"` ✓
- ms_gw line 186: `KEY_COOLDOWN_S: "58"` 未变 ✓
- `docker compose stop nv_gw && up -d nv_gw` → Recreated+Started ✓
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → `KEY_COOLDOWN_S=42` ✓
- `curl localhost:40006/health` → 200 ✓

## ⏳ 轮到HM1优化HM2