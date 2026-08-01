# R-nvonly-post23 — HM2 cc2 NOP 巡检轮

**日期**: 2026-08-02 02:22 CST
**上轮**: R-nvonly-post22 (6 连庄满分)
**本轮**: NOP 巡检轮, 0 改动, 0 重启, 0 buffer 触发

## 本轮判定依据 (轮前链路分析, 30min 窗口)

### cc2 (cc4101-primary) 链路 — SR 100%
| caller | model | status | count |
|--------|-------|--------|-------|
| cc4101-primary | glm5_2_nv | 200 | 1 |
| cc4101-primary | glm5_2_ms | 200 | 1 |

cc2 本轮 30min 2 个请求, 全 200 成功. 1 个 glm5_2_nv 直接成功, 1 个 fallback 到 glm5_2_ms (ms_gw 兜底生效, 符合"fallback 已恢复"指令, 非 nv_gw 故障).
无 transport 错误, 无 buffer 触发, 无 tier 错误 (cc2 流量直接成功).

### 其他 caller (非 cc2 流量)
| model | SR | 详情 |
|-------|-----|------|
| dsv4p_nv | 73.5% (25/34) | 9× all_tiers_exhausted + 4×429 + 3×502 (hermes/openclaw/other) |
| glm5_2_nv | 100% (2/2) | 含 1 个 other caller |
| glm5_2_ms | 100% (1/1) | cc4101 fallback |

dsv4p_nv SR=73.5% 是 hermes/openclaw caller 打 NVCF 侧 dsv4p_nv 限流 (9× all_tiers_exhausted, 5key 全挂 avg 7326ms), **与 cc2 链路无关** (cc2 已切 glm5_2_nv 健康 tier).

### tier 错误明细
| key | error_type | count |
|-----|-----------|-------|
| 2 | 429_nv_rate_limit | 1 |

仅 1 次 dsv4p_nv 429 (key2), 无 transport 错误, 无 RemoteDisconnected/SSL EOF. R-nvonly 短惩罚分类持续生效.

### fallback 发生率
| fallback | count |
|----------|-------|
| f (无) | 36 |
| t (有) | 1 |

1 次 fallback 到 ms_gw (glm5_2_ms), 符合"ms_gw fallback 已恢复"指令.

## 健康验证
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | `nv_default_model: glm5_2_nv`, `nv_num_keys: 5`, 5 keys ✓ |
| nv_gw `NVU_DISABLE_MS_FALLBACK` | `0` (fallback 已恢复) ✓ |
| nv_gw `NVU_BUFFER_MAX_RETRIES` | `5` ✓ |
| docker ps | cc4101 Up 19m, nv_gw Up 19m, nv_gw_stable Up 22m, ms_gw Up 2d, logs_db Up 2d ✓ |
| 主仓 git HEAD | 87d3169 (R-nvonly-post22 已 push) ✓ |

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

## 参数快照 (实测)
- nv_gw: `NVU_DISABLE_MS_FALLBACK=0`, `NVU_BUFFER_MAX_RETRIES=5`, `TIER_TIMEOUT_BUDGET_S=180`, `UPSTREAM_TIMEOUT=90`
- cc4101: `CC4101_STREAM_TOTAL_DEADLINE_S=470`, `FALLBACK_UPSTREAM_URL=http://ms_gw:40007/...`, `PRIMARY_UPSTREAM_MODEL=glm5_2_nv`, `PRIMARY_HEADER_TIMEOUT=400`

## 下一步
- 继续 NOP 巡检, 维持 7 连庄.
- 关注 dsv4p_nv SR (hermes/openclaw caller, 非 cc2 链路), 若 NVCF 侧恢复则整体 SR 上升.
- 若 cc2 出现新错误或 SR<99%, 再找根因小步改.
