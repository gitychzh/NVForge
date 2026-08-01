# R-nvonly-post52 — hm2 cc2 NOP 巡检轮

**时间**: 2026-08-02 04:05 CST
**轮型**: NOP 巡检 (无流量, 链路健康无故障)
**改动**: 0  |  **重启**: 0

## 链路分析 (注入数据 2026-08-02 04:04 CST)

### cc2 (cc4101-primary) 30min — 0 req
本轮 session 轮前无 cc2 流量产生. 无数据可判 SR, 但链路健康无故障:
- nv_gw /health: status=ok, 5 keys, default=glm5_2_nv, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv]
- docker ps: cc4101/nv_gw/nv_gw_stable Up 2h, logs_db Up 2d
- 0 cc2 tier error, 0 buffer/wait 日志

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count | error |
|--------|-------|--------|-------|-------|
| hermes | dsv4p_nv | 429 | 6 | all_tiers_exhausted ×6 |

hermes 打 dsv4p_nv SR=0% (0/6), 6×all_tiers_exhausted (5key 全挂, NVCF 侧 dsv4p 限流).
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv). 按分钟 19:35~20:00 每 5min 1×429, 稳定限流.

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 SR | 0 req (无流量) | — (链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 | ✅ |
| buffer 触发 | 无 | ✅ |
→ **NOP 巡检轮**, 不改码, 不重启.

## 验证
- git pull origin main: Already up to date ✓
- nv_gw /health: ok ✓
- docker ps: 全 Up ✓
- nv_requests 30min (cc4101-primary): 0 rows ✓

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR.
- 关注 dsv4p_nv (hermes) 限流 (NVCF 侧, 非 cc2).
- 若 cc2 出现新错误或 SR<99%, 再找根因小步改.
