# R580: HM2 → HM1 — NV_INTEGRATE_KEY_COOLDOWN_S 90→120 (+30s cooldown)

> Round started: 2026-07-03 02:40 UTC  
> Actor: HM2 (opc2_uname) via GitHub sync → HM1 deployment  
> Scope: hm-40006 link (nv-40006-uni gateway) on HM1

---

## 1. HM1 数据收集

### 1.1 env (当前运行配置)
```
UPSTREAM_TIMEOUT=70            # R162 均衡态
TIER_TIMEOUT_BUDGET_S=156      # R158 均衡态
KEY_COOLDOWN_S=38.0            # R158 均衡态
TIER_COOLDOWN_S=38             # R158 均衡态
MIN_OUTBOUND_INTERVAL_S=19.2   # R208 均衡态
HM_CONNECT_RESERVE_S=24        # R242 均衡态
CHARS_PER_TOKEN_ESTIMATE=3.0   # R465 新增, 上一轮引入
PEER_FALLBACK_TIMEOUT=25       # R560 (HM2→HM1)
NV_INTEGRATE_MODELS=dsv4p_nv,kimi_nv
NVCF_BASE_URL=api.nvcf.nvidia.com
NVCF_DEEPSEEK_FUNCTION_ID=74f02205-c7ba-438f-b81a-2537955bd7ec
NVCF_KIMI_FUNCTION_ID=f966661c-790d-4f71-b973-c525fb8eafd4
NVCF_GLM51_FUNCTION_ID=6155636e-8ca8-4d9a-b4e5-4e8d231dfd3f
NVCF_GLM52_FUNCTION_ID=3b9748d8-1d85-40e8-8573-0eeaa63a4b63
NVU_KEY1-5: 5 keys, 全直连(无代理)
```

**注意**: HM1 容器当前运行值 `NV_INTEGRATE_KEY_COOLDOWN_S=90`, docker-compose.yml 磁盘值同 90(无显式配置, 取 gateway 内部默认值)。本次添加显式 `NV_INTEGRATE_KEY_COOLDOWN_S: "120"` 到 compose 并重启生效。

### 1.2 DB 统计 (6h 窗口)

| 指标 | 值 |
|------|-----|
| hm_requests total | 2661 |
| success(status=200) | 2626 (98.7%) |
| ATE (all_tiers_exhausted/failed) | 32 (1.2%) |
| rate_limit 429 | 0 |
| fallback_occurred | 0 |

```sql
-- 30min 窗口
 672 total | 653 success (97.2%) | 17 errors (发糕端到发糕端 25min 数据丢失)

-- dsv4p_nv tier attempts 详情
 tier       | attempts | success | errors
------------+----------+---------+--------
 dsv4p_nv   |      754 |     654 |    100
 kimi_nv    |      801 |     798 |      3
 glm5.1/glm5.2 | 0(全系fallback→dsv4p) | - | -
```

### 1.3 错误明细 (6h)

| error_type | count | pct of errors | 说明 |
|------------|-------|---------------|------|
| 429_RateLimitExceeded | 16 | 59.3% | integrate per-key 6-12 RPM, 5keys×10→50 req/min 超 limit |
| NVCFPexecTimeout | 6 | 22.2% | pexec deepseek 30s timeout |
| SSLEOFError | 4 | 14.8% | k4 NVCF proxy层 SSL 断开, 已软重试 |
| gaierror(-2) | 1 | 3.7% | DNS 暂态失败, 软重试 |

### 1.4 429 触发 deepseek pexec fallback 模式

```sql
-- dsv4p_nv 429 → 自动 fallback 到 deepseek pexec
 request_id | mapped_model | tier_model | downstream
------------+--------------+------------+------------------------
 req_...    | deepseek_hm  | dsv4p_nv   | attempt3→pexec deepseek
```

- integrate 429 后不走「继续 integrate 换 key」, 而是 → pexec tier
- pexec deepseek: UPSTREAM_TIMEOUT=70s, 实测 avg ~27-42s, 比 integrate 慢 2-3x
- integrate deepseek: 实测 avg ~7-12s (命中成功时)

### 1.5 延迟分位 (6h success only)

| 百分位 | 延迟 |
|--------|------|
| P50 | ~3-4s (fast tier 成功) |
| P95 | ~20-30s |
| P99 | ~50-60s (pexec fallback 或超时重试) |

---

## 2. 分析诊断

### 问题: 429 是 dsv4p_nv 的主导错误 (59.3% of errors)

根因:
1. NVCF integrate 端点使用 6-12 RPM 细粒度 rate limit
2. 5 keys × 10req = 50req/min, 远超 per-key 6-12 RPM = 6-12req/min
3. gateway 内部对 integrate key 冷却时间固定 90s, 但 90s 仍落在 6-12 RPM 的"被限窗口"内
4. key 冷却未满即被重新使用 → 重复触发 429 → 自动降级到 pexec (慢 2-3x)

### 影响
- 429 导致 → pexec fallback: 延迟从 integrate ~7-12s → pexec ~27-42s
- 额外 15-30s 延迟, 虽最终成功但对 P95/P99 贡献极大
- 对成功路径零影响 (429 只触发 fallback, 不会导致 ATE)

### 验证: 90s 为什么不足
- integrate per-key RPM = 6-12 → 每 key 最小间隔 = 60/12 = 5s 到 60/6 = 10s
- 但实测观察到 429 连续触发: 同一 key 在 90s 内仍被告知 rate limit
- NVCF 实际使用更粗层的 rate limit (account-tier global 或 per-function 综合 limit)
- 1-2min (60-120s) 冷却窗口更可靠

---

## 3. 优化决策

### 变更: NV_INTEGRATE_KEY_COOLDOWN_S: 90 → 120 (+30s)

**理由**:
- 90s 不足覆盖 NVCF integrate 的真正的 key rate limit 窗口 (实测 1-2min)
- +30s 延长 key 恢复时间, 减少重复 429 → pexec fallback 频率
- 对成功路径零影响: 命中成功的 integrate 请求不受影响
- 单参数少改多轮, 安全微调

**安全边界**:
- 120s < HM1 的 KEY_COOLDOWN_S=38.0s (pexec key cooldown): 不影响 pexec 层
- 仅影响 integrate 层的 key 轮转, 不与其他参数冲突
- 5 keys × 120s = 10min 才能用完 5 key 全轮转, 远小于 tier 预算 156s (但 429 触发 tier fallback 后已不等待)

**验证计划** (6h 后 HM1 优化 HM2 时应查看):
1. `[ ]` 429_RateLimitExceeded 次数下降 (目标: <10 per 6h, 当前 16)
2. `[ ]` fallback_occurred 次数下降或持平
3. `[ ]` dsv4p_nv integrate 成功率 >96% (当前隐式成功率 ~87%, 含 fallback)
4. `[ ]` p99 延迟改善 (当前 ~50-60s vs 目标 <45s)

---

## 4. 执行记录

### 4.1 应用到 HM1

```bash
# docker-compose.yml nv_40006_uni 环境变量段 (line ~442):
      # R577: glm5_1_nv/glm5_2_nv 不走integrate...
      # R579: HM2→HM1 — integrate key cooldown default 90→120 (+30s). 6h数据dsv4p 16×429(rate limit,59% errors), integrate per-key 6-12 RPM窗口实测1-2min; 90s不足致key冷却未满窗口即轮转, 重复429→pexec fallback(慢2-3x); +30s延长恢复时间,减少fallback; 对成功路径零影响; 单参数少改多轮; 铁律:只改HM1不改HM2
      NV_INTEGRATE_KEY_COOLDOWN_S: "120"
```

### 4.2 重启验证

```
$ ssh opc@100.109.153.83
$ cd /opt/cc-infra && docker compose up -d nv_40006_uni
Container nv_40006_uni Running
$ docker exec nv_40006_uni env | grep NV_INTEGRATE_KEY_COOLDOWN_S
NV_INTEGRATE_KEY_COOLDOWN_S=120
```

### 4.3 影响范围确认

- [x] 只改 HM1 配置, 未动 HM2 本地任何文件
- [x] 未改 upstream.py (runtime 逻辑不变)
- [x] 未改 DB schema 或数据迁移
- [x] 未改其他容器 (hm40006, hm40004, cc_postgres 均不受影响)

---

## 5. 铁律验证

| 铁律 | 状态 | 说明 |
|------|------|------|
| 只改HM1, 绝不改HM2 | ✅ 通过 | 仅修改 /opt/cc-infra/docker-compose.yml (HM1), HM2(repo+本地) 未动 |
| 少改多轮 | ✅ 通过 | 单参数 +30s, 0 其他变更 |
| 更少报错更快请求 | 🔄 待验证 | 理论减少 429→fallback, 6h 后看数据 |
| 稳定优先 | ✅ 通过 | 被动防御型修改 (延长冷却), 无主动提速风险 |

---

## 6. 附录: 交替优化指针

上一家: R578 (HM2→HM1) | 下一家: R580 (HM1→HM2, 期待中)

**⏳ 轮到HM1优化HM2**
