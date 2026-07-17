# R1696: HM2→HM1 — handlers.py zombie→big_input breaker feed (补 R1695 遗漏)

## 数据 (HM1, 6h window, 2026-07-17 10:45 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 47 |
| OK | 36 (76.6%) |
| Fail | 11 (23.4%) |
| Error types | 11 zombie_empty_completion (100%) |
| 0 ATE, 0 fallback, 0 peer-fb, 0 ms-gw |
| Model | 100% glm5_2_nv |
| All requests | >250K chars (254K-284K) |
| p50 | 9,202ms |
| p95 | 21,552ms |
| max ok | 27,290ms |
| max fail | 26,340ms |
| key_cycle_429s | 45x1, 2x2 |

### Zombie timeline (all >250K chars)
```
10:33 284178c 6053ms
10:03 280008c 5346ms
09:34 280585c 5526ms
09:03 276406c 5705ms
08:34 275796c 8967ms
08:03 274590c 17103ms
07:33 274590c 26340ms
06:33 269889c 5067ms
06:03 257816c 8163ms
05:34 266731c 12032ms
05:03 254063c 6961ms
```

## 分析

R1695 部署了 big_input_breaker 模块 (big_input_breaker.py + upstream.py 3 处补丁)，但 **遗漏了 handlers.py 层的 zombie→breaker 对接**。对比 HM2 的 handlers.py (R1673) 发现 HM2 在 3 处 zombie 检测点都调用了 big_input_breaker：

1. **非流式 zombie** (openai `/v1/chat/completions`): 检测到 zombie → `record_big_input_failure("zombie_empty_completion")`
2. **流式 zombie** (openai passthrough): 检测到 zombie → `record_big_input_failure("zombie_empty_completion")`
3. **Anthropic 流式 zombie** (`/v1/messages`): 检测到 zombie → `record_big_input_failure("zombie_empty_completion")`

HM1 的 handlers.py **完全没有这些调用**。结果：
- upstream.py 的 breaker 入口逻辑正常（is_big_input_open() 检查），但 breaker 永远 CLOSED
- 因为没有任何 zombie 检测点调用 `record_big_input_failure()`，fail_count 永远为 0
- 超大 input 请求持续走 NV 链，每次 ~5-26s zombie，breaker 形同虚设

## 变更

**补丁 handlers.py 3 处 (不涉及 compose，纯代码补丁):**

1. **Import** (line 46): `from . import big_input_breaker`
2. **非流式 zombie** (line 457-462): 在 `metrics["error_type"] = "zombie_empty_completion"` 之后，添加 breaker feed
3. **流式 zombie** (line 907-912): 在 `zombie_detected = True` / `_log("NV-ZOMBIE-EMPTY"...)` 之后，添加 breaker feed

- 理由: R1695 部署了 breaker 但遗漏 handlers 层对接 → breaker 无法积累 fail_count 永远 CLOSED
- 影响: 补上后，首次 zombie → FAIL_N=1 触发 OPEN → 后续超大 input 请求立即返回 all_tiers_exhausted → peer-fallback 到 HM2 → 省 ~5-26s/zombie
- 安全: 与 HM2 R1673 逻辑一致，仅新增 zombie→breaker 记录，不修改现有 zombie 检测逻辑
- 铁律: 只改 HM1 不改 HM2

## 验证

- `docker exec nv_gw grep -n 'big_input_breaker' /app/gateway/handlers.py` → 7 matches (import + 2×3=6 breaker calls) ✓
- Python syntax check → OK ✓
- Container restart: `docker compose up -d --force-recreate nv_gw` → Recreated + Started ✓
- Health check: `{"status": "ok", "port": 40006}` ✓
## ⏳ 轮到HM1优化HM2
