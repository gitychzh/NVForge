# R-nvonly-post38 — hm2_cc2 NOP 巡检轮

**日期**: 2026-08-02 03:30 CST
**轮次**: R-nvonly-post38 (NOP 巡检)
**上轮**: R-nvonly-post37 (NOP)

## 判稳结论
**NOP 巡检轮** — 0 改动, 0 重启。cc2 (cc4101-primary) 30min 0 req 无流量, 链路健康无故障。

## 本轮关键数据

### 1. cc4101-primary (cc2) 30min — 0 req
本轮 session 轮前无流量产生, 无数据可判 cc2 SR。链路健康无故障。

### 2. 其他 caller (非 cc2 链路, 仅供观察)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 5 |
| openclaw | dsv4p_nv | 200 | 1 |

dsv4p_nv SR=44.4% (4/9), top error: all_tiers_exhausted ×5 (5key 全挂, NVCF 侧限流)。
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)。
趋势: 18:50-19:15 间歇 429, 19:04-19:05 恢复 200 → NVCF 侧间歇限流后段自恢复。

### 3. 健康验证
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | cc4101/nv_gw/nv_gw_stable Up ~1h, ms_gw/logs_db Up 2d ✓ |
| buffer/wait/error 日志 | 30min 无 (cc2 0 req, 无流量) ✓ |
| 配置 (注入实测) | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (all_tiers_exhausted ×5 全是 dsv4p_nv/hermes, 非 cc2) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启。

## cc2 SR 走势
| 轮次 | cc2 SR | 错误 | 趋势 |
|------|--------|------|------|
| post17-post27 | 100% (各轮 1-3 req) | 0 | ✅ 11 连庄满分保持 |
| post28-post37 | 0 req | 0 | — (无流量, 链路健康, 不打断) |
| **post38** | **0 req** | **0** | — (无流量, 链路健康, 不打断) |

## 改动
无 (NOP 巡检轮)。

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR (本轮 0 req 是 session 轮前无流量, 非链路故障)。
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2)。
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改。
