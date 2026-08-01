# R-nvonly-post15 (hm2_cc2) — 应急回滚 dsv4p_nv→glm5_2_nv

**时间**: 2026-08-01 19:23 CST
**类型**: 应急修复轮 (1 改动 1 restart cc4101)
**基线**: R-nvonly-post12 (满分 40/40=100%, glm5_2_nv 时代) → 中断数轮 → post15

## 触发根因 (轮前数据注入)

cc2 30min SR 暴跌至 **10/29 ≈ 34%** (满分基线 → 严重故障). 根因链:

1. cc4101 `PRIMARY_UPSTREAM_MODEL=dsv4p_nv` → cc2 流量全打 dsv4p_nv
2. dsv4p_nv 在 NVCF 侧 429 风暴: 同 egress IP `203.10.96.139` (mihomo-7902) 反复 429,
   **响应无 retry-after 头** → keymanager 指数退避 120→180→480→600s 仍持续 429
3. 5 key 全 cooling → buffer 5 attempts (k0→k1→k2→k3→k4) 全 `execute_failed` (每次 ~5s 快速失败,
   `all_keys_exhausted=True`) → `buffer_exhausted` ×18, avg 165s
4. WaitQueue 等 120s 无恢复 → `NV-BUFFER-NO-MS` (ms fallback disabled) → 502 返 CC

### 6h 趋势佐证 (dsv4p_nv 持续恶化)
| 时段 | 200 | 429 | 502 | SR |
|------|-----|-----|-----|-----|
| 05:00 | 43 | 0 | 6 | 88% |
| 07:00 | 79 | 4 | 11 | 84% |
| 09:00 | 31 | 6 | 7 | 70% |
| 11:00 | 14 | 5 | 15 | **41%** |

→ NVCF 上游对 dsv4p_nv 限流, 非 nv_gw 侧可解.

## 决策与依据

**动作**: cc4101 `PRIMARY_UPSTREAM_MODEL: dsv4p_nv → glm5_2_nv`

依据:
1. **直接探测**: `curl /v1/messages model=glm5_2_nv` → 200 正常 (vs dsv4p_nv 429 风暴)
2. **历史先例**: post9-12 连续满分 (40/40=100%) 即 glm5_2_nv 时代
3. **config.py L224 注释**: R2143 时记录过完全相同的 dsv4p_nv NVCF 端点失效场景,
   当时的处置就是切 default→glm5_2_nv 让 cc2 流量重路由到健康 tier
4. **dsv4p_nv 是 NVCF 上游 429 风暴**, nv_gw 侧无法修复 (无 retry-after 头, 退避到 600s 仍 429)

铁律边界: 改的是 cc4101 (cc2 自己的入口代理, HM2 基础设施) 的 env, 非 nv_gw 源码.
不碰 ms_gw, `FALLBACK_UPSTREAM_URL=none` 保持, `NVU_DISABLE_MS_FALLBACK=1` 不变.

## 验证 (改后)

| 验证项 | 结果 |
|--------|------|
| compose 备份 | `docker-compose.yml.bak.R1923` ✓ |
| cc4101 recreate | `PRIMARY_UPSTREAM_MODEL=glm5_2_nv` 生效 ✓ |
| cc4101 /health | `{"primary":"glm5_2_nv"}` ✓ |
| docker ps | cc4101 Up, nv_gw Up, logs_db Up ✓ |
| 端到端探测 (cc4101→nv_gw→glm5_2_nv) | 200, `model:"glm5_2_nv"`, "Hi there!" ✓ |

→ 改动生效, cc2 流量已重路由到健康 tier. 等下个 30min 窗口确认 SR 恢复.

## 参数快照 (改后)

- cc4101: `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages`,
  `FALLBACK_UPSTREAM_URL=none`, `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `PRIMARY_HEADER_TIMEOUT=400`
- nv_gw: `NVU_DISABLE_MS_FALLBACK=1`, 5key(k0-k4)×5美国IP, `NVU_BUFFER_MAX_RETRIES=5`,
  `NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90`, `NVU_BUFFER_TOTAL_DEADLINE_S=450`,
  `NV_INTEGRATE_MODELS=glm5_2_nv` (dsv4p_nv 已从 integrate 移除, pexec-only)
- config.py: `DEFAULT_NV_MODEL=glm5_2_nv` (L224, 未改, 历史已是 glm5_2_nv)

## 下一步

- 下一轮巡检: 确认 cc2 30min SR 回到 ≥99% (glm5_2_nv 健康 tier)
- 关注 dsv4p_nv 是否恢复 (per-key 429 趋势) — 若 NVCF 侧恢复可考虑切回, 但需 6h 稳定数据
- 持续监控 `buffer_exhausted` 是否归零 (切回 glm5_2_nv 后应首发命中)
