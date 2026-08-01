# R-nvonly-post42 — hm2_cc2 NOP 巡检轮

**时间**: 2026-08-02 03:50 CST
**轮型**: NOP 巡检 (0 改动, 0 重启)
**上轮**: R-nvonly-post41 (HEAD 7065995)

## 判稳依据 (注入数据 03:33)

### cc2 (cc4101-primary) 30min
- **0 req** — session 轮前无流量产生, 无数据可判 SR
- 链路健康无故障: 容器全 Up, /health ok, 0 tier error, 0 buffer/wait/error 日志

### 其他 caller (非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 3 |
| hermes | dsv4p_nv | 429 | 5 |
| openclaw | dsv4p_nv | 200 | 1 |

- dsv4p_nv SR=44.4% (4/9), top error: `all_tiers_exhausted`×5 (5key 全挂, NVCF 侧限流)
- **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)
- 趋势: 19:04-19:05 恢复 200, 19:10-19:30 间歇 429 → NVCF 侧间歇限流后段自恢复

### 健康验证
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv ✓ |
| docker ps | cc4101/nv_gw Up 2h, nv_gw_stable Up 2h, ms_gw/logs_db Up 2d ✓ |
| 配置实测 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复) ✓ |

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 SR | 0 req (无流量) | — (链路健康无故障) |
| 新错误类型 | 无 | ✅ |
| transport 层 | 0 错误 | ✅ |
| buffer 触发 | 无 | ✅ |
→ **NOP 巡检轮**

## 本轮动作
- 0 改动, 0 重启
- post17-post27 连续满分 11 连庄保持 (post28-post42 均 0 req 不计入连庄也不打断)

## 下一步
- 继续 NOP 巡检, 等 cc2 产生流量后再判 SR
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题)
- 若 cc2 出现新错误或 SR<99%, 再找根因小步改
