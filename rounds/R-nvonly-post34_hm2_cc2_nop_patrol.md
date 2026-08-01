# R-nvonly-post34 — hm2_cc2 NOP 巡检轮 (2026-08-02 03:15 CST)

## 轮前链路分析 (注入, 30min 窗口)

### cc4101-primary (cc2) 30min — 0 req
本轮 session 轮前无 cc2 流量产生, 无数据可判 SR. 链路健康无故障.

### 其他 caller (非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 5 |
| openclaw | dsv4p_nv | 200 | 1 |

- dsv4p_nv SR=44.4% (4/9), top error: `all_tiers_exhausted` ×5 (5key 全挂, NVCF 侧 dsv4p 限流).
- **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
- 按分钟趋势: 18:40-19:00 持续 429 → 19:04-19:05 恢复 200 → NVCF 侧间歇限流后段自恢复.
- fallback 发生率: f=9 (全部 dsv4p_nv/hermes, 非 cc2).

### 健康验证
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5 ✓ |
| docker ps | cc4101/nv_gw/nv_gw_stable Up ~1h, ms_gw/logs_db Up 2d ✓ |
| 配置实测 (注入) | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (all_tiers_exhausted ×5 全是 dsv4p_nv/hermes, 非 cc2) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 改动
0 改动, 0 重启. 本轮纯巡检.

## cc2 SR 走势
- post17~post27: 连续满分 11 连庄 (post22-27 含 ms_gw fallback 兜底, 已恢复).
- post28~post33: 0 req 无流量, 链路健康不打断.
- **post34**: 0 req 无流量, 链路健康不打断.

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR (本轮 0 req 是 session 轮前无流量, 非链路故障).
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
