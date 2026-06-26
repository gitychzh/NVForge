# R46: HM1 → HM2 — upstream.py duration_s 15→22 (+7s): reduce wasted glm5.1 429 cycling before deepseek fallback

## 📊 数据收集 (HM2)

**环境变量 (docker compose env):**
| 变量 | 当前值 | 状态 |
|---|---|---|
| `UPSTREAM_TIMEOUT` | 62 | ✅ active (config.py:28) |
| `TIER_TIMEOUT_BUDGET_S` | 111.0 | ✅ active (config.py:95, upstream.py:210+) |
| `MIN_OUTBOUND_INTERVAL_S` | 17.0 | ✅ active (config.py:149) |
| `KEY_COOLDOWN_S` | 26.0 | ✅ active (config.py:168-191) |
| `HM_CONNECT_RESERVE_S` | 6 | ✅ active (upstream.py:233) |
| `TIER_COOLDOWN_S` | 55 | ⚠️ DEAD — 不在 config.py 也不在 upstream.py |

**Docker 日志 (最近100行):**
- 109 HM-* 事件, 全部 fallback 到 deepseek_hm_nv
- glm5.1_hm_nv: 100% tier failure rate (全部5 key 429)
- deepseek_hm_nv: 所有成功请求在此 tier (avg ~32s)

**DB 数据 (30分钟窗口):**
| Tier | 请求 | 平均延迟 | p95 | 429错误 | 其他错误 |
|---|---|---|---|---|---|
| glm5.1_hm_nv | 198 | 19.6s | n/a | 100% tier failure | 少量 SSLEOF/ConnRST |
| deepseek_hm_nv | 948 | 32.0s | 72.0s | 0 | 955次 fallback 成功 |
| kimi_hm_nv | 7 | 160.2s | 215s | 0 | 最后兜底 |

**429 错误分布 (30分钟):** 2824 次 429 → ~94/min
**SSLEOF:** 327 | **ConnectionResetError:** 71

**DB 查询结果 (hm_requests):** 8条记录 (R45窗口后), 全部 status=200, 全部 fallback 到 deepseek_hm_nv

**HM2健康状态:** ✅ health OK

## 🔍 分析诊断

**根因:** NV API glm5.1 所有 key 持续 429 (rate limit), 每15s 循环恢复 → 立即再被 429 → 浪费 ~20-60s/tier 在无效 cycling 上。

**代码链路:**
1. `upstream.py:477` — `all_429` 时 `mark_key_cooling(tier_model, k, duration_s=15)` — 硬编码 15s
2. `config.py:184-191` — `mark_key_cooling()` 函数: `effective_duration = min(KEY_COOLDOWN_S * 2^(n-1), 30) if duration_s is None else duration_s`
3. 当 `duration_s` 被显式提供 (15) → 使用 15s, 忽略 `KEY_COOLDOWN_S=26.0` 的指数回退
4. 15s 太短 — keys 恢复后立即 429 → 再次 fallback → 再次 429 → 循环

**为什么 `TIER_COOLDOWN_S=55` 无效:** 该变量不在任何 Python 文件中被读取 (config.py 无定义, upstream.py 无引用)。完全 dead。

**为什么 `HM_CONNECT_RESERVE_S=6` 有效:** upstream.py:233 直接读取 `os.environ.get("HM_CONNECT_RESERVE_S", "5")`。

## 🎯 优化计划

**少改多轮原则:** 仅改 1 个文件 1 个参数

**执行:**
- **文件:** `/opt/cc-infra/proxy/hm-proxy/gateway/upstream.py` (源码 → Dockerfile `COPY gateway/ ./gateway/`)
- **位置:** line 493 `mark_key_cooling(tier_model, k, duration_s=15)`
- **变更:** `duration_s=15` → `duration_s=22` (+7s)
- **日志:** line 494 `Marking all cooling 15s` → `Marking all cooling 22s` (日志对齐实际值)

**理由:**
- 当前: glm5.1 全部 429 → 标记 15s cooldown → 15s 后 keys 恢复 → 立即 429 → 浪费 ~20-60s/tier
- 优化: 22s cooldown → keys 保持冷却 22s → NV API rate limit window 更充分 → 减少无效 cycling
- 只有 1 个参数变更 (少改多轮)
- 不改变 HM1 本地任何配置 (铁律)
- 不改变 mihomo 进程 (绝对禁止)

**预期效果:**
- 减少 glm5.1 tier 内无效 429 cycling 次数
- 更快到达 deepseek_hm_nv fallback (当前 avg 32s)
- 整体请求延迟可能略微降低 (减少 wasted cycling time)
- 稳定优先 — 不影响 deepseek_hm_nv 的成功路径

**部署:** `docker compose build hm40006 && docker compose up -d hm40006`
- ✅ 构建成功 (image hash: 4780d1df9e66)
- ✅ 容器重启成功 (hm40006 recreated + started)
- ✅ 健康检查通过: `{"status": "ok"}`
- ✅ 日志确认: `[HM-GLOBAL-COOLDOWN] tier=glm5.1_hm_nv all keys 429. Marking all cooling 22s`

## 📈 验证

```
[15:18:21.5] [HM-GLOBAL-COOLDOWN] tier=glm5.1_hm_nv all keys 429. Marking all cooling 22s
```

新代码已部署运行，确认 `duration_s=22` 生效。

## 🔧 待 HM2 后续优化

- `KEY_COOLDOWN_S` 可考虑从 26→30 (回到 cap), 但需 HM2 自己决策
- `TIER_COOLDOWN_S` 如欲激活 → 需在 `upstream.py` 或 `config.py` 中添加 `os.environ.get("TIER_COOLDOWN_S", …)`
- 当前 glm5.1_hm_nv 全 429 问题 → NV API 层面 rate limit, 非配置可解

## ⏳ 轮到 HM2 优化 HM1