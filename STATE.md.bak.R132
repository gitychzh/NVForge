# STATE — cc2 自优化 nv_gw 链路 (R-nvonly 方向)

## 当前轮基线 (2026-08-02 02:22 CST, R-nvonly-post23 NOP 巡检轮)
- 主仓 git HEAD: 87d3169 (R-nvonly-post22 已 push)
- **本轮 R-nvonly-post23 (hm2_cc2)**: NOP 巡检轮. cc2 30min 2/2=SR100% (glm5_2_nv 1 + glm5_2_ms 1 fallback).
  post17~post23 连续满分 (7 连庄). 0 改动, 0 重启, 0 buffer 触发.
  1 次 fallback 到 ms_gw (glm5_2_ms, 符合"fallback 已恢复"指令, 非 nv_gw 故障).
  /health primary=glm5_2_nv ✓, 5 keys ✓, 容器全 Up ✓.
  ⚠️ 配置实测: `NVU_DISABLE_MS_FALLBACK=0`, `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/...` (ms_gw fallback 已恢复, 与 prompt 指令一致).
  hermes/openclaw caller 打 dsv4p_nv SR=73.5% (9×all_tiers_exhausted + 4×429 + 3×502) 是 NVCF 侧限流, 非 cc2 链路.
- round 文件: `rounds/R-nvonly-post23_hm2_cc2_nop_patrol.md`

## R-nvonly 核心铁律 (持续生效, 按 prompt 当前指令)
- 只改 HM2 nv_gw (40006), 不碰 HM1, 不碰 ms_gw 源码.
- ms_gw fallback 已恢复 (`NVU_DISABLE_MS_FALLBACK=0`, `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/...`), 不主动禁用.
- 改前有数据, 改后必验证, 写入仓库.

## 本轮关键数据

### 1. cc4101-primary (cc2) 30min 窗口 — 2 req, SR 100%
| status | count | avg_dur_ms |
|--------|-------|------------|
| 200    | 2     | 85680      |

cc2 本轮 30min 2 个请求, 全 200 成功. 1 个 glm5_2_nv 直接成功, 1 个 fallback 到 glm5_2_ms (ms_gw 兜底生效, 非 nv_gw 故障).
无 transport 错误, 无 buffer 触发 (cc2 流量直接成功).

### 2. 其他 caller (hermes/openclaw/other, 非 cc2 流量)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 14 |
| hermes | dsv4p_nv | 429 | 4 |
| hermes | dsv4p_nv | 502 | 3 |
| openclaw | dsv4p_nv | 200 | 7 |
| other | dsv4p_nv | 200 | 4 |
| other | dsv4p_nv | 502 | 2 |
| other | glm5_2_nv | 200 | 1 |

dsv4p_nv SR=73.5% (25/34), 9× all_tiers_exhausted (5key 全挂, avg 7326ms) + 4×429 + 3×502.
NVCF 侧 dsv4p_nv 限流持续, **与 cc2 无关** (cc2 已切 glm5_2_nv).

### 3. tier 错误明细
| key | error_type | count |
|-----|-----------|-------|
| 2 | 429_nv_rate_limit | 1 |

仅 1 次 dsv4p_nv 429 (key2), 无 transport 错误, 无 RemoteDisconnected/SSL EOF. R-nvonly 短惩罚分类持续生效.

### 4. fallback 发生率
| fallback | count |
|----------|-------|
| f (无) | 36 |
| t (有) | 1 |

1 次 fallback 到 ms_gw (glm5_2_ms), 符合"ms_gw fallback 已恢复"指令.

### 5. 健康验证
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | `nv_default_model: glm5_2_nv`, `nv_num_keys: 5`, 5 keys ✓ |
| nv_gw `NVU_DISABLE_MS_FALLBACK` | `0` (fallback 已恢复) ✓ |
| docker ps | cc4101 Up 19m, nv_gw Up 19m, nv_gw_stable Up 22m, ms_gw Up 2d, logs_db Up 2d ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 2/2 = 100% | ✅ glm5_2_nv 健康 tier |
| 新错误类型 | 无 (仅 1×429 dsv4p_nv, 非 cc2) | ✅ |
| transport 层 | 0 错误 | ✅ |
| buffer 触发 | 无 (2 req 直接成功/1 fallback) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## cc2 SR 走势
| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post17 | 1/1=100% | 0 | ✅ glm5_2_nv 健康, 满分 |
| post18 | 1/1=100% | 0 | ✅ 连续满分 |
| post19 | 2/2=100% | 0 | ✅ 连续满分 |
| post20 | 2/2=100% | 0 | ✅ 连续满分 |
| post21 | 2/2=100% | 0 | ✅ 5 连庄 |
| post22 | 3/3=100% | 0 | ✅ 6 连庄 (含 1 次 ms_gw fallback 兜底) |
| **post23** | **2/2=100%** | **0** | ✅ 7 连庄 (含 1 次 ms_gw fallback 兜底) |

## 参数快照 (实测 2026-08-02 02:22)
- nv_gw: `NVU_DISABLE_MS_FALLBACK=0`, `NVU_BUFFER_MAX_RETRIES=5`, `TIER_TIMEOUT_BUDGET_S=180`, `UPSTREAM_TIMEOUT=90`, `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`
- cc4101: `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions`, `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_HEADER_TIMEOUT=400`

## 下一步
- 继续 NOP 巡检, 维持 7 连庄.
- 关注 dsv4p_nv SR (hermes/openclaw caller, 非 cc2 链路), 若 NVCF 侧恢复则整体 SR 上升.
- 若 cc2 出现新错误或 SR<99%, 再找根因小步改.
