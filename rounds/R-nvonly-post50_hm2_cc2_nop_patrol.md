# R-nvonly-post50 — hm2_cc2 NOP 巡检轮

**日期**: 2026-08-02 04:05 CST
**方向**: R-nvonly (只改 HM2 nv_gw)
**类型**: NOP 巡检轮 (0 改动, 0 重启)

## 本轮改动
无. NOP 巡检轮.

## 依据 (轮前链路分析 + 实测 2026-08-02 03:58)
- cc2 (cc4101-primary) 30min 窗口: **0 req** (session 轮前无流量产生, 无数据可判 SR).
- 其他 caller: hermes 打 dsv4p_nv 6×429, 全 all_tiers_exhausted (5key 全挂, NVCF 侧 dsv4p 持续限流).
  - 按分钟趋势: 19:30~19:55 每 5min 1×429, 稳定限流 (NVCF 侧, 非 cc2 链路).
  - **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
- 配置实测 (注入): `NVU_DISABLE_MS_FALLBACK=0` (fallback 已恢复), `FALLBACK_UPSTREAM=ms_gw:40007` ✓.

## 健康验证
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | cc4101/nv_gw/nv_gw_stable Up 2h ✓ |
| nv_requests 30min (cc4101-primary) | 0 rows (cc2 无流量) ✓ |
| nv_requests 30min 错误分类 | 6×all_tiers_exhausted (全 hermes/dsv4p, 0 cc2) ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR (本轮 0 req 是 session 轮前无流量, 非链路故障).
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
