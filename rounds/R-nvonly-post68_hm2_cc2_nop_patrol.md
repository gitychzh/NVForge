# R-nvonly-post68 — hm2 cc2 NOP 巡检轮 (2026-08-02 04:49 CST)

## 轮前数据 (注入, 04:49 CST)
- cc4101-primary (cc2) 30min: **0 req** (session 轮前无流量产生, 无数据可判 SR)
- hermes|dsv4p_nv: 200×10 + 429×5 → SR=66.7% (15req), 5×all_tiers_exhausted (avg_dur 1186s)
- 30min nv_gw buffer/wait/keymanager 日志: 0 行 (cc2 0 req 无触发)
- 容器 age: nv_gw/cc4101 均 3 hours ago

## 链路健康验证 (04:49 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | cc4101/nv_gw/nv_gw_stable/ms_gw/logs_db 全 Up (3h~2d) ✓ |
| 配置 (注入实测) | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 0 req (无流量) | — (无数据, 链路健康无故障) |
| 新错误类型 | 无 (0 cc2 tier error) | ✅ |
| transport 层 | 0 错误 (无 cc2 流量) | ✅ |
| buffer 触发 | 无 (cc2 0 req) | ✅ |
→ **NOP 巡检轮**, 0 改动, 0 重启.

## hermes dsv4p_nv 限流分析 (非 cc2 链路)
- SR=66.7% (10/15), top error: all_tiers_exhausted × 5 (5key 全挂)
- per-key: k2=10×200 (12921ms avg), 其余 5×429 (all_tiers_exhausted)
- per-IP: 203.10.96.139=10×100%, 其余 5×0% (egress IP 漂移, 单 IP 限流)
- 按分钟: 20:20~20:30 每 5min 1×429 稳定限流, 20:30~20:36 恢复 10×200 (NVCF 侧 dsv4p 周期性限流)
- finish_reason: tool_calls×9, stop×1 (无 zombie)
- **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv), 不处理.

## 本轮动作
- 拉主仓 git pull (已 up to date)
- 拉本仓 git pull origin master (已 up to date, HEAD=4d02854 post67)
- /health + docker ps 验证链路健康
- 0 改动, 0 重启

## 下一步
- 继续 NOP 巡检. 等 cc2 产生流量后再判 SR (本轮 0 req 是 session 轮前无流���, 非链路故障).
- 关注 dsv4p_nv (hermes) 限流是否缓解 (NVCF 侧问题, 非 cc2).
- 若 cc2 出现新错误或 SR<99% (排除 fallback 兜底), 再找根因小步改.
