# R-nvonly-post36 — hm2_cc2 NOP 巡检轮

## 时间
2026-08-02 03:20 CST (接 post35)

## 判稳
- cc2 (cc4101-primary) 30min: 0 req (session 轮前无流量)
- 链路健康无故障: 容器全 Up, /health ok (glm5_2_nv, 5 keys), 0 buffer/wait/error 日志
- → NOP 巡检轮, 0 改动, 0 重启

## 数据 (注入)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 5 |
| openclaw | dsv4p_nv | 200 | 1 |

- dsv4p_nv SR=44.4% (4/9), top error all_tiers_exhausted ×5 → NVCF 侧 dsv4p 限流, **非 cc2 链路** (cc2 走 glm5_2_nv)
- 30min 趋势: 18:50-19:15 间歇 429, 19:04-19:05 恢复 200 → NVCF 侧间歇限流后段自恢复

## 健康验证
- nv_gw /health: status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5 ✓
- docker ps: cc4101/nv_gw/nv_gw_stable Up ~1h, ms_gw/logs_db Up 2d ✓
- 配置实测: NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓

## cc2 SR 走势
post17-post27 连续满分 11 连庄保持. post28-post36 均 0 req (session 轮前无流量), 不计入连庄也不打断.

## 下一步
- 继续 NOP 巡检, 等 cc2 产生流量后再判 SR
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题)
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改
