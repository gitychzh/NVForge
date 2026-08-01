# R-nvonly-post31 — hm2_cc2 NOP 巡检轮

**日期**: 2026-08-02 03:03 CST
**方向**: R-nvonly (ms_gw fallback 已恢复, 不主动禁用)
**改动**: 0  **重启**: 0  **代码变更**: 无

## 判稳依据

### 1. cc2 (cc4101-primary) 30min — 0 req
```
 status | count
--------+-------
(0 rows)
```
session 轮前无流量产生, 无数据可判 cc2 SR. 链路健康无故障.

### 2. 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 429 | 6 |

dsv4p_nv SR=0% (0/6), top error: all_tiers_exhausted ×6 (5key 全挂, NVCF 侧限流).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 3. 健康验证
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5 ✓ |
| docker ps | cc4101 Up 59m, nv_gw Up 59m, nv_gw_stable Up ~1h, ms_gw Up 2d, logs_db Up 2d ✓ |
| buffer/wait/error 日志 | 无 (cc2 0 req, 无 buffer 触发) ✓ |
| 配置实测 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK=ms_gw:40007 ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (all_tiers_exhausted ×6 全是 dsv4p_nv/hermes, 非 cc2) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## cc2 SR 走势
| 轮次 | cc2 SR | 趋势 |
|------|--------|------|
| post17-post27 | 100% (1~3 req/轮) | ✅ 11 连庄满分 |
| post28-post30 | 0 req | — (无流量, 链路健康, 不打断) |
| **post31** | **0 req** | — (无流量, 链路健康, 不打断) |

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR.
- 关注 dsv4p_nv (hermes) NVCF 侧限流是否缓解 (非 cc2 问题).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
