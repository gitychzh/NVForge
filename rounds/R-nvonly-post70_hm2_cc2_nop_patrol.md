# R-nvonly-post70 — hm2 cc2 NOP 巡检轮 (2026-08-02 04:55 CST)

## 基线
- 主仓 HEAD: 6347a8d (post69) → 本轮 post70
- 上轮: R-nvonly-post69 NOP, cc2 30min 0req
- 容器: nv_gw/cc4101 Up 3h, ms_gw/logs_db Up 2d, 全 Up

## 轮前链路分析 (注入, 30min 窗口 04:54)
| 项 | 实测 |
|----|------|
| cc2 (cc4101-primary) 30min | 0 req (session 轮前无流量) |
| hermes/dsv4p_nv | 200×10, 429×5 → SR=66.7% (NVCF 侧限流, 非 cc2) |
| top error | all_tiers_exhausted ×5 (dsv4p 5key 全挂, NVCF 侧) |
| cc2 tier error | 0 |
| cc2 buffer/wait 日志 | 0 行 |

dsv4p_nv per-IP: 203.10.96.139=10×100%, 其余 5×0% (egress 漂移单 IP 限流).
按分钟: 20:20~20:50 每 5min 1×429 周期性限流, 20:30~20:36 恢复 10×200.
→ dsv4p 限流是 NVCF 侧, cc2 走 glm5_2_nv 不受影响.

## 健康验证 (04:55)
- nv_gw /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓
- docker ps: cc4101/nv_gw/nv_gw_stable/ms_gw/logs_db 全 Up ✓
- 配置: NVU_DISABLE_MS_FALLBACK=0 (fallback 恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓

## 三阈值判稳
| 阈值 | 实测 | 判定 |
|------|------|------|
| cc2 SR | 0 req | — (无流量, 链路健康无故障) |
| 新错误类型 | 无 | ✅ |
| transport 层 | 0 错误 | ✅ |
| buffer 触发 | 无 | ✅ |
→ **NOP 巡检轮**, 0 改动, 0 重启.

## 行动
- 0 改码, 0 restart
- 0 commit 源码改动 (仅 round 文件 + STATE)

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR.
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧, 非 cc2).
- 若 cc2 出现新错误或 SR<99%, 再找根因小步改.
