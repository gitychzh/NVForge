# R-nvonly-post19 — NOP 巡检轮 (hm2_cc2)

**日期**: 2026-08-02 02:10 CST
**主仓 HEAD**: a041817 (ff up to date)
**容器**: nv_gw Up 1m, cc4101 Up 1m, logs_db (healthy)

## 本轮判定: NOP 巡检轮 (0 改动, 0 重启)

### 依据
- cc2 (cc4101-primary) 30min: **2/2 = SR 100%** (glm5_2_nv, avg 3267ms)
- 0 错误, 0 fallback, 0 transport 错误, 0 buffer 触发
- tier 错误 0 行 (nv_tier_attempts 30min 无 error_type)
- 三阈值全绿: cc2 SR=100%, 无新错误类型, 无 transport 异常

### 非 cc2 流量 (hermes/openclaw caller 打 dsv4p_nv)
- dsv4p_nv SR=60% (12/20): 8×429 all_tiers_exhausted + 1×502
- per-key dsv4p: key3 6×200, key2 4×200, key0/key1 各 1×200, 但有 7×429 + 1×502 无 key 归属
- per-egress-IP: 134.195.101.194 (6, 100%), 203.10.96.139 (4, 100%), 其余 1+1
- **非 cc2 优化目标**: cc2 已切 glm5_2_nv (post15 回滚持续生效), hermes 打 dsv4p_nv 的 429 风暴是 NVCF 侧限流

### 配置验证 (实测 env)
- nv_gw: `NVU_DISABLE_MS_FALLBACK=0` (ms_gw fallback 已恢复, 与 prompt 指令一致)
  - `NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90`, `NVU_BUFFER_TOTAL_DEADLINE_S=450`, `NVU_BUFFER_MAX_RETRIES=5`
  - `UPSTREAM_TIMEOUT=90`, `NVU_TIER_BUDGET_GLM5_2_NV=120`, `TIER_COOLDOWN_S=180`
- cc4101: `PRIMARY_UPSTREAM_MODEL=glm5_2_nv` ✓ (post15 回滚持续)
  - `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions` (fallback 已恢复)
  - `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `PRIMARY_HEADER_TIMEOUT=400`, `UPSTREAM_TIMEOUT=130`
- /health: `nv_default_model: glm5_2_nv`, 5 keys ✓

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
| post16 | 0 req | 0 | NOP (回滚后无流量) |
| post17 | 1/1=100% | 0 | ✅ glm5_2_nv 满分 |
| post18 | 1/1=100% | 0 | ✅ 连续满分 |
| **post19** | **2/2=100%** | **0** | ✅ 连续满分 (流量+1) |

## 下一步
- 等下个有 cc2 流量的 30min 窗口: 期望 SR 持续 100%
- 若 cc2 SR<99% → 找根因, 小步改
- dsv4p_nv 429 风暴 (hermes caller): 持续监控, 非 cc2 优化目标
