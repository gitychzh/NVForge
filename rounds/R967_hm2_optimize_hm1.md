# R967: HM2→HM1 — NOP (false trigger, R966 self-commit)

**时间**: 2026-07-09 05:45 UTC
**触发**: Cron 检测到 R966 commit (54a7f7a) 是 HM2 自提交 (脚本输出: "这是我提交的, 不触发")
**方向**: HM2 → HM1
**类型**: NOP (false trigger)

---

## 数据采集

### 1. 容器日志 (docker logs nv_gw --tail 100)
```
[NV-PROXY] Listening on 0.0.0.0:40006
[13:33:21.5] [NV-REQ] mapped_model=glm5_2_nv start_tier=glm5_2_nv stream=True
```
零 error/warn/Timeout — 干净。

### 2. 容器环境 (docker exec nv_gw env)
| 参数 | 值 | 说明 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 60 | R966: 64→60 ✓ |
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

所有参数与 compose 一致，四源通过。

### 3. 容器 StartedAt
```
2026-07-09T05:27:03.532757673Z
```
R966 部署后容器已重启，参数生效确认。

### 4. DB 统计 (6h, created_at ≥ now() - interval '6h')

| 模型 | 总请求 | 成功 | 错误 | P50(ms) | P95(ms) | Max(ms) |
|------|--------|------|------|---------|---------|---------|
| glm5_2_nv | 19 | 19 | 0 | 12075 | 102857 | 113315 |
| dsv4p_nv | 12 | 12 | 0 | 92152 | 165165 | 173278 |

**总计**: 31/31 100% SR, 0 errors, 0 ATE

### 5. Fallback 统计
| fallback | count |
|----------|-------|
| false | 24 |
| true | 7 |

7 fallbacks (22.6%), all glm5_2_nv→dsv4p_nv. 100% SR on fallback path.

### 6. nv_tier_attempts (6h)
| tier | error_type | count |
|------|-----------|-------|
| glm5_2_nv | NVCFPexecTimeout | 6 |
| glm5_2_nv | 504_nv_gateway_timeout | 5 |
| glm5_2_nv | empty_200 | 3 |
| glm5_2_nv | budget_exhausted_after_connect | 1 |

NVCFPexecTimeout max=53,473ms << UPSTREAM=60 (6.5s buffer ≥ 3s R751 floor). 504 errors are server-side NVCF gateway timeouts (non-config fixable). 3 empty_200 with EMPTY_200_FASTBREAK=3 — correctly allowing 2 empty200s before fastbreak.

### 7. 小时趋势
| hour | dsv4p_nv | glm5_2_nv |
|------|----------|-----------|
| 00:00 | 0 | 6/6 OK |
| 01:00 | 0 | 7/7 OK |
| 02:00 | 2/2 OK | 1/1 OK |
| 03:00 | 2/2 OK | 1/1 OK |
| 04:00 | 1/1 OK | 1/1 OK |
| 05:00 | 7/7 OK | 3/3 OK |

全时段 100% SR.

---

## 决策分析

### 候选评估表

| 候选 | 评估 | 决策 |
|------|------|------|
| 调参任何参数 | 所有参数已在地板/最优值；100% SR；零错误 | ❌ 不调 |
| UPSTREAM_TIMEOUT | 60s, NVCFPexecTimeout max=53,473ms, buffer=6.5s ≥ 3s floor | ❌ 不调 |
| TIER_TIMEOUT_BUDGET_S | 114, 成功路径max=173s (dsv4p, 但fallback成功) | ❌ 不调 |
| FASTBREAK | 1, 正确 | ❌ 不调 |
| EMPTY_200_FASTBREAK | 3, 与 ms_gw 一致 | ❌ 不调 |

### 判断: NOP

R966 是 HM2 自提交 ("这是我提交的, 不触发")，检测脚本正确识别但 cron 仍派遣。此轮为 false trigger NOP。

- 31/31 100% SR, 0 errors, 0 ATE
- 所有参数在地板/最优值
- NVCFPexecTimeout max=53,473ms << UPSTREAM=60 (6.5s buffer ≥ 3s R751 floor)
- FASTBREAK=1, EMPTY_200_FASTBREAK=3 均正确
- BUDGET=114 >> 60s safe

**无需任何参数变更。**

---

## 部署

无部署 (NOP)。

---

## 验证

- ✅ Compose 文件与容器 env 一致
- ✅ Container StartedAt 在 R966 commit 后
- ✅ 日志零错误
- ✅ DB 100% SR

---

## ⏳ 轮到HM1优化HM2