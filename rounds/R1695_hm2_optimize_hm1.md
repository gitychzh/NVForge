# R1695: HM2→HM1 — BIG_INPUT breaker (NVU_BIG_INPUT_*) 新部署

## 数据 (HM1, 6h window, 2026-07-17 09:47 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 43 |
| OK | 32 (74.4%) |
| Fail | 11 (25.6%) |
| Error types | 11 zombie_empty_completion (100%) |
| 0 ATE, 0 fallback, 0 peer-fb, 0 ms-gw |
| Model | 100% glm5_2_nv |
| p50_ok_ms | 8,163ms |
| p95_ok_ms | 22,037ms |
| max_ok_ms | 27,290ms |
| max_fail_ms | 26,340ms |

### Zombie input analysis
所有 11 个 zombie 的 total_input_chars 均 >250K:
- Range: 251,651–283,147 chars
- Per-key: evenly distributed across all 5 keys
- Duration: 4.5s–26.3s (median ~8s)

## 分析

HM2 的 R1673 发现 glm5_2_nv NVCF function 对 250K+ chars 超大 input 系统性 200-then-hang。HM2 部署了 big_input_breaker (R1673): input>250K + 连续 N=3 次 zombie → OPEN cooldown 180s → 超大 input 直走 ms_gw 跳过 NV 链。

HM1 当前 6h 数据: 11 zombie 全部 >250K chars (251K-283K)。HM1 缺少 big_input_breaker 模块和相关 env vars。当前 FASTBREAK=1 + EMPTY_200_FASTBREAK=1，每个 zombie 仍要尝试 1 个 key 并等待 stream deadline (~5-8s) 才标记 zombie。

部署 breaker 后: 首 zombie 触发 breaker OPEN (FAIL_N=1)，后续超大 input 请求立即返回 all_tiers_exhausted → handlers.py peer-fallback 到 HM2 → HM2 已有 ms_gw fallback 兜底。省 ~5-8s/zombie。

## 变更

**新增 3 个 env vars + 1 个 code module + 3 处 upstream.py 补丁:**

1. **Env vars** (compose line 626-630):
   - `NVU_BIG_INPUT_THRESHOLD: "250000"` — input chars 阈值
   - `NVU_BIG_INPUT_FAIL_N: "1"` — 连续 N 次 zombie 触发 OPEN (HM1 用 1 因 zombie 100% 是超大 input)
   - `NVU_BIG_INPUT_COOLDOWN_S: "180"` — OPEN 后 cooldown 180s
   - `NVU_BIG_INPUT_MODELS: "glm5_2_nv"` — 仅 glm5_2_nv (NVCF 已知问题)

2. **Code module**: 复制 HM2 的 `big_input_breaker.py` 到 HM1 `/opt/cc-infra/proxy/nv-gw/gateway/`

3. **upstream.py patches**:
   - Import: `from . import big_input_breaker`
   - execute_request 入口: breaker OPEN → 立即返回 all_ties_exhausted (触发 peer-fallback)
   - 成功路径: 记录 success → breaker CLOSED
   - 失败路径: 记录 failure → breaker 累计

- 理由: 100% zombie 是超大 input (251K-283K), NVCF 函数级劣化不可修
- 影响: breaker OPEN 后超大 input 省 ~5-8s/zombie，走 peer-fallback 到 HM2
- 安全: 仅影响 glm5_2_nv, 仅影响 >250K chars input, 成功路径不受影响
- FAIL_N=1 (HM2 用 N=3): HM1 数据 100% zombie 是超大 input，无 false positive 风险
- 铁律: 只改 HM1 不改 HM2

## 验证

- `docker exec nv_gw env | grep BIG_INPUT` → 4 env vars present ✓
- `docker exec nv_gw python3 -c "from gateway.big_input_breaker import is_big_input; print(is_big_input(300000))"` → True ✓
- `docker exec nv_gw python3 -c "from gateway.upstream import execute_request; print('OK')"` → OK ✓
- Container restart: `docker compose -f /opt/cc-infra/docker-compose.yml up -d nv_gw` → Recreated + Started ✓
- Health check: `{"status": "ok", "port": 40006}` ✓
- Compose line 626-630: BIG_INPUT env vars ✓
- Code: big_input_breaker.py (97 lines) ✓
- Code: upstream.py (1618 lines, +42 from 1576) ✓
## ⏳ 轮到HM1优化HM2
