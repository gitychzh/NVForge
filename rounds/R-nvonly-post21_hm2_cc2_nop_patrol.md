# R-nvonly-post21 — NOP 巡检轮 (hm2_cc2)

**日期**: 2026-08-02 02:12 CST (链路数据时间戳)
**主仓 HEAD**: 7709820 (R-nvonly-post20 已 push)
**容器**: nv_gw Up 9m, cc4101 Up 9m, nv_gw_stable Up 13m, ms_gw Up 2d, logs_db (healthy 2d)

## 本轮判定: NOP 巡检轮 (0 改动, 0 重启)

### 依据
- cc2 (cc4101-primary) 30min: **2/2 = SR 100%** (glm5_2_nv, avg 3267ms)
- 0 错误, 0 fallback, 0 transport 错误, 0 buffer 触发
- tier 错误 (nv_tier_attempts 30min): 仅 1× `429_nv_rate_limit` 在 key2 (dsv4p_nv 流量, 非 cc2)
- 三阈值全绿: cc2 SR=100%, 无新错误类型, 无 transport 异常
- post17→post18→post19→post20→post21 连续满分 (glm5_2_nv 健康 tier, 5 连庄)

### 非 cc2 流量 (hermes/openclaw caller 打 dsv4p_nv)
- dsv4p_nv SR=61.5% (16/26): 10× `all_tiers_exhausted` (5key 全挂, avg 3692ms) + 6×429 + 4×502
- per-key dsv4p: key3 8×200(11502ms), key2 6×200(9988ms), key0/key1 各 1×200; 但 6×429 + 4×502 无 key 归属 (全挂后 all_tiers_exhausted)
- per-egress-IP: 134.195.101.194 (8/100%), 203.10.96.139 (6/100%), 134.195.101.180/188 各 1×100%
- dsv4p 200 finish_reason: 7×length, 7×tool_calls, 2×stop (7×length 异常偏高, 但非 cc2 链路)
- dsv4p 200 延迟: avg 9802ms, max 39434ms, ttfb 9574ms (慢, 但非 cc2 流量)
- **非 cc2 优化目标**: cc2 已切 glm5_2_nv (post15 回滚持续生效), hermes 打 dsv4p_nv 的 429 风暴是 NVCF 侧限流

### 配置验证 (实测 env, 与 post20 一致)
- nv_gw: `NVU_DISABLE_MS_FALLBACK=0` (ms_gw fallback 已恢复, 与 prompt 指令一致)
  - `MIN_OUTBOUND_INTERVAL_S=10`, `TIER_COOLDOWN_S=180`, `KEY_COOLDOWN_S=30`
  - `NV_INTEGRATE_KEY_COOLDOWN_S=90`, `TIER_TIMEOUT_BUDGET_S=180`
  - `NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4`
  - `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`
  - `UPSTREAM_TIMEOUT=90`, `NVU_FORCE_STREAM_UPGRADE=0`, `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150`
  - `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2`
- cc4101: `PRIMARY_UPSTREAM_MODEL=glm5_2_nv` ✓ (post15 回滚持续)
  - `PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages`
  - `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions`, `FALLBACK_UPSTREAM_MODEL=glm5_2_ms`
  - `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=130`
  - `CC4101_PRIMARY_FAIL_THRESHOLD=3`, `CC4101_PRIMARY_SKIP_S=30`, `UPSTREAM_IDLE_TIMEOUT=150`
- /health: `nv_default_model: glm5_2_nv`, `nv_num_keys: 5`, `nv_model_tiers: [kimi_nv, dsv4p_nv, glm5_2_nv]` ✓
- buffer/wait/keymanager 日志: 无 (2 req 直接成功, 未触发 buffer 路径)

### deadline 链对齐
- 90s/buffer-attempt × 5 = 450s buffer < 470s cc4101 total < 500s SDK idle ✓
- 本轮无 stream_total_deadline 触发

## cc2 SR 走势
| 轮次 | cc2 SR | 错误 | 备注 |
|------|--------|------|------|
| post9  | 40/40=100% | 0 | 满分 (glm5_2_nv) 🎉 |
| post11 | 36/36=100% | 0 | 满分 (glm5_2_nv) 🎉 |
| post12 | 40/40=100% | 0 | 连庄 (glm5_2_nv) 🎉🎉 |
| post15 | 10/29=34% | 19×502 | ❌ dsv4p_nv 429 风暴 → 切回 glm5_2_nv |
| post16 | 0 req | 0 | NOP (回滚后健康, 无流量) |
| post17 | 1/1=100% | 0 | ✅ glm5_2_nv 健康, 满分 |
| post18 | 1/1=100% | 0 | ✅ 连续满分 |
| post19 | 2/2=100% | 0 | ✅ 连续满分 (流量+1) |
| post20 | 2/2=100% | 0 | ✅ 连续满分 (稳态) |
| **post21** | **2/2=100%** | **0** | ✅ 连续满分 (5 连庄) |

## 下一步
- 等下个有 cc2 流量的 30min 窗口: 期望 SR 持续 100% (glm5_2_nv 健康 tier, 对标 post9-12 满分基线)
- 若 cc2 SR<99% → 找根因, 小步改
- dsv4p_nv 429 风暴 (hermes caller): 持续监控, 非 cc2 优化目标, NVCF 侧限流

## 参数快照 (未改)
- cc4101: `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages`,
  `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions`, `FALLBACK_UPSTREAM_MODEL=glm5_2_ms`,
  `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=130`,
  `CC4101_PRIMARY_FAIL_THRESHOLD=3`, `CC4101_PRIMARY_SKIP_S=30`, `UPSTREAM_IDLE_TIMEOUT=150`
- nv_gw: `NVU_DISABLE_MS_FALLBACK=0` (fallback 已恢复), 5key(k0-k4)×5美国IP(hysteria2),
  `NVU_BUFFER_MAX_RETRIES=5`, `NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90`, `NVU_BUFFER_TOTAL_DEADLINE_S=450`,
  `NVU_TIER_BUDGET_GLM5_2_NV=120`, `TIER_COOLDOWN_S=180`, `UPSTREAM_TIMEOUT=90`,
  `MIN_OUTBOUND_INTERVAL_S=10`, `KEY_COOLDOWN_S=30`, `NV_INTEGRATE_KEY_COOLDOWN_S=90`,
  `NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4`, `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`,
  `NVU_FORCE_STREAM_UPGRADE=0`, `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150`, `TIER_TIMEOUT_BUDGET_S=180`,
  `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2`
- config.py: `DEFAULT_NV_MODEL=glm5_2_nv` (未改)
