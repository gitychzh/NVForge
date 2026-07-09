# R968: HM2→HM1 — NOP (double-dispatch false trigger, R967 self-commit)

**时间**: 2026-07-09 05:55 UTC
**触发**: Cron 检测到 R967 commit (fa4c9cd) 是 HM2 自提交 (脚本输出: "这是我提交的, 不触发")
**方向**: HM2 → HM1
**类型**: NOP (double-dispatch false trigger — R967 already committed and pushed)

---

## 数据采集

### 1. 容器日志 (docker logs nv_gw --tail 100)
```
NO_ERRORS_FOUND
```
零 error/warn/Timeout — 干净。

### 2. 容器环境 (docker exec nv_gw env)
| 参数 | 值 | 说明 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 60 | R966 ✓ |
| TIER_TIMEOUT_BUDGET_S | 114 | R737 ✓ |
| MIN_OUTBOUND_INTERVAL_S | 0 | R638 ✓ |
| KEY_COOLDOWN_S | 25 | R162 ✓ |
| TIER_COOLDOWN_S | 25 | R492 ✓ |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | R961 ✓ |
| NVU_EMPTY_200_FASTBREAK | 3 | R829 ✓ |
| NVU_CONNECT_RESERVE_S | 0 | R657 ✓ |
| NVU_SSLEOF_RETRY_DELAY_S | 1.0 | R543 ✓ |
| NVU_FORCE_STREAM_UPGRADE | 0 | R692 ✓ |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 64 | R749 ✓ |
| NVU_PEER_FALLBACK_TIMEOUT | 45 | R697 ✓ |
| NVU_PEER_FALLBACK_ENABLED | 1 | ✓ |
| NVU_PEER_FB_SKIP_MODELS | glm5_2_nv,dsv4p_nv | ✓ |
| NV_INTEGRATE_KEY_COOLDOWN_S | 0 | R631 ✓ |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | R922 ✓ |

所有参数与 R967 一致。

### 3. DB 统计 (6h, ts ≥ now() - interval '6h')

| 指标 | 值 |
|------|-----|
| 总请求 | 31 |
| 成功 (200) | 31 |
| 失败 | 0 |
| 成功率 | 100% |
| ATE | 0 |
| Fallback | 7 (22.6%), all glm5_2_nv→dsv4p_nv, 100% SR |

### 4. 按路径分组
| upstream_type | cnt | ok | avg_ttfb | avg_dur | max_dur |
|---------------|-----|----|----------|---------|---------|
| nvcf_pexec | 31 | 31 | 49553 | 49555 | 173278 |

### 5. 错误分类
```
(0 rows)
```
零错误。

### 6. nv_tier_attempts (6h)
| tier | error_type | cnt | avg_ms | max_ms |
|------|-----------|-----|--------|--------|
| glm5_2_nv | NVCFPexecTimeout | 6 | 51823 | 53473 |
| glm5_2_nv | 504_nv_gateway_timeout | 5 | - | - |
| glm5_2_nv | empty_200 | 3 | - | - |
| glm5_2_nv | budget_exhausted_after_connect | 1 | 51838 | 51838 |

NVCFPexecTimeout max=53,473ms << UPSTREAM=60 (6.5s buffer ≥ 3s R751 floor). 504 是 NVCF 服务端网关超时。3 empty_200 配合 EMPTY_200_FASTBREAK=3 正确。

### 7. 与 R967 对比
| 指标 | R967 | R968 | 变化 |
|------|------|------|------|
| 6h 总请求 | 31 | 31 | 0 |
| 成功率 | 100% | 100% | - |
| 错误 | 0 | 0 | - |
| ATE | 0 | 0 | - |
| Fallback | 7 | 7 | - |
| UPSTREAM_TIMEOUT | 60 | 60 | - |
| NVCFPexecTimeout max | 53,473ms | 53,473ms | - |

**数据完全一致** — 无任何变化。

---

## 决策分析

### 候选评估表

| 候选 | 评估 | 决策 |
|------|------|------|
| 调参任何参数 | 所有参数已在地板/最优值；100% SR；零错误 | ❌ 不调 |
| UPSTREAM_TIMEOUT | 60s, NVCFPexecTimeout max=53,473ms, buffer=6.5s ≥ 3s floor | ❌ 不调 |
| TIER_TIMEOUT_BUDGET_S | 114, 成功路径max=173s (dsv4p单次, fallback成功) | ❌ 不调 |
| FASTBREAK | 1, 正确 | ❌ 不调 |
| EMPTY_200_FASTBREAK | 3, 与 ms_gw 一致 | ❌ 不调 |

### 判断: NOP

R967 是 HM2 自提交 ("这是我提交的, 不触发")，检测脚本正确识别但 cron 仍派遣。R967 已提交并推送，R968 是 double-dispatch。

- 31/31 100% SR, 0 errors, 0 ATE
- 所有参数在地板/最优值
- NVCFPexecTimeout max=53,473ms << UPSTREAM=60 (6.5s buffer ≥ 3s R751 floor)
- FASTBREAK=1, EMPTY_200_FASTBREAK=3 均正确
- BUDGET=114 >> 60s safe
- 数据与 R967 完全一致

**无需任何参数变更。**

---

## 部署

无部署 (NOP)。

---

## 验证

- ✅ Compose 文件与容器 env 一致
- ✅ 日志零错误
- ✅ DB 100% SR
- ✅ 数据与 R967 完全一致

---

## ⏳ 轮到HM1优化HM2