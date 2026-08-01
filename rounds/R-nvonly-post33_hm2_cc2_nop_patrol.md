# R-nvonly-post33 — hm2_cc2 NOP 巡检轮 (2026-08-02 03:09 CST)

## 轮前链路分析注入数据

### cc2 (cc4101-primary) 30min — 0 req
- 本轮 30min 窗口 cc2 无流量产生 (session 轮前无请求).
- 无数据可判 cc2 SR; 链路健康无故障.

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 5 |
| openclaw | dsv4p_nv | 200 | 1 |

dsv4p_nv SR=44.4% (4/9), top error: all_tiers_exhausted ×5 (5key 全挂, NVCF 侧限流).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 30min 按分钟趋势 (dsv4p)
- 18:40-19:00: 持续 429 (每分钟 1 个)
- 19:04-19:05: 恢复 200 (4 个)
→ NVCF 侧 dsv4p_nv 间歇限流, 后段自恢复.

## 健康验证
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5 ✓ |
| docker ps | cc4101 Up, nv_gw Up, nv_gw_stable Up, ms_gw Up 2d, logs_db Up 2d ✓ |
| 配置 (注入实测) | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |
| cc2 30min nv_requests (DB 复查) | 0 rows (确认 0 req) ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (all_tiers_exhausted ×5 全是 dsv4p_nv/hermes, 非 cc2) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## cc2 SR 走势
| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post17-post27 | 满分 (各轮 1-3 req 全 200) | 0 | ✅ 连续满分 11 连庄 |
| post28-post32 | 0 req | 0 | — (无流量, 链路健康, 不打断) |
| **post33** | **0 req** | **0** | — (无流量, 链路健康, 不打断) |

## 改动
- 0 改动, 0 重启 (NOP 巡检).

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR (本轮 0 req 是 session 轮前无流量, 非链路故障).
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
