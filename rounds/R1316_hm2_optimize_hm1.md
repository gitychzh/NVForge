# HM2 Optimize HM1 — Round R1316

## 1. 触发判定

```
cron 脚本输出: "这是我提交的, 不触发"
最新 commit: 91fcf2c (R1315, author=opc2_uname)
判定: FALSE TRIGGER — 双派发 (30th consecutive post-R1286)
```

## 2. 数据收集 (改前必有数据)

### 6h 总体
| 指标 | 值 |
|------|-----|
| 总请求 | 59 |
| OK (200) | 52 |
| 失败 | 7 |
| SR | 88.1% |
| avg_ok_dur | 10874ms |
| avg_ok_ttfb | 9287ms |

### 错误分类
| model | error_type | cnt | avg_dur |
|-------|-----------|-----|---------|
| glm5_2_nv | zombie_empty_completion | 7 | 5027ms |

### 按小时
| hour (UTC) | total | ok | fail | SR |
|------------|-------|-----|------|-----|
| 2026-07-13 21:00 | 3 | 2 | 1 | 66.7% |
| 2026-07-13 22:00 | 7 | 5 | 2 | 71.4% |
| 2026-07-13 23:00 | 6 | 5 | 1 | 83.3% |
| 2026-07-14 00:00 | 6 | 5 | 1 | 83.3% |
| 2026-07-14 01:00 | 29 | 28 | 1 | 96.6% |
| 2026-07-14 02:00 | 5 | 5 | 0 | 100.0% |
| 2026-07-14 03:00 | 3 | 2 | 1 | 66.7% |

### 其他指标
- tier_attempts: 0
- fallback_occurred: 0 (f: 59)
- upstream_type: nv_integrate only (59 req)
- ms_gw: 13/13 100.0%
- ATE: 0, IncompleteRead: 0

### Docker logs (nv_gw, recent)
```
[09:33:26.0] [NV-ZOMBIE-EMPTY] (glm5_2_nv) zombie empty completion: finish_reason=stop but content_chars=12 < 50, input_chars=175336
[09:33:26.0] [NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk
[11:03:26.7] [NV-ZOMBIE-EMPTY] (glm5_2_nv) zombie empty completion: finish_reason=stop but content_chars=12 < 50, input_chars=175423
[11:03:26.7] [NV-ZOMBIE-ERROR-CHUNK] (glm5_2_nv) sent finish_reason=content_filter error SSE chunk
```

### HM1 nv_gw env (关键参数)
```
TIER_COOLDOWN_S=15, KEY_COOLDOWN_S=25, UPSTREAM_TIMEOUT=66
MIN_OUTBOUND_INTERVAL_S=0, NVU_CONNECT_RESERVE_S=0
NVU_PEER_FB_SKIP_MODELS= (empty)
NVU_TIER_BUDGET_DSV4P_NV=72, NVU_TIER_BUDGET_GLM5_2_NV=96
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_EMPTY_200_FASTBREAK=2, NVU_INTEGRATE_TIMEOUT_FASTBREAK=1, NVU_PEXEC_TIMEOUT_FASTBREAK=1
Compose md5: 6e1b58bc stable
```

## 3. 决策: NOP

**理由:**
- 所有失败均为 zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop, 12chars, 175K+ input) — 代码级 NOP 信号，不可通过配置修
- 0 ATE, 0 tier_attempts, 0 fallback, 0 IncompleteRead
- ms_gw 13/13 100%
- 所有参数在 floor/optimal
- Compose md5 6e1b58bc 稳定
- 30th consecutive double-dispatch post-R1286

**零参数修改，零 compose 修改，零容器重启**

## 4. 铁律
只改HM1不改HM2 ✅ (本轮无修改)

## ⏳ 轮到HM1优化HM2
