# R-nvonly-post28 — hm2_cc2 NOP 巡检轮

**时间**: 2026-08-02 02:50 CST
**上轮**: R-nvonly-post27 (11 连庄)
**本轮改动**: 0 改动, 0 重启 (NOP 巡检)

## 数据 (30min 窗口, 2026-08-02 02:48)

### cc4101-primary (cc2) — 0 req
```
 status | count
--------+-------
(0 rows)
```
本轮 30min 窗口 cc2 无请求产生 (session 轮前无流量). 无数据可判 cc2 SR.
docker logs nv_gw --since 30m 无 BUFFER-/WAIT-/MS-FB 日志, 佐证 cc2 本轮 0 流量.

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 5 |
| hermes | dsv4p_nv | 429 | 5 |
| hermes | dsv4p_nv | 502 | 1 |

dsv4p_nv SR=45.5% (5/11), top error: all_tiers_exhausted ×6 (5key 全挂, NVCF 侧限流).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).

### 健康验证
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5 ✓ |
| docker ps | cc4101 Up 45m, nv_gw Up 45m, nv_gw_stable Up 49m, ms_gw Up 2d, logs_db Up 2d ✓ |
| 配置 (注入实测) | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM_URL=http://ms_gw:40007/... ✓ |

## 判稳
- cc2 30min 0 req → 无法判 SR, 但链路健康无故障 (容器全 Up, /health ok, 无错误日志).
- 无新错误类型 (dsv4p_nv all_tiers_exhausted 是 hermes 非 cc2, 已知 NVCF 限流).
→ **NOP 巡检轮**, 不改码, 不重启.

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR.
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
