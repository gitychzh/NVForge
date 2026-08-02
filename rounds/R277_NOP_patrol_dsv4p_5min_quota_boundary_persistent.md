# R277 — NOP 巡检轮 (2026-08-02 15:32 CST)

## 链路状态
- cc2 (cc4101-primary) 30min **0 req** — session 间歇空闲,链路空闲健康. 0 fallback 0 deadline.
- dsv4p_nv 30min SR=71.4% (10/14), 4 失败**全 hermes caller**, 全整 5min 边界点
  (07:10/07:15/07:20/07:25 UTC, 分钟%5==0).
- 失败 key 为空 (空 egress IP), duration 1890ms 快速失败 → pexec peek path 一击即败
  (hermes 不在 NVU_BUFFER_CALLERS, 不走 buffer 5key 轮转保护).
- 07:05/07:06/07:30 均恢复 200 → NVCF 5min 窗口边界配额耗尽后刷新恢复.

## 4h SR 趋势 (确认持续, 未恶化)
| UTC 小时 | ok | fail | SR |
|---|---|---|---|
| 03:00 | 6 | 4 | 60.0% (注入窗口残留) |
| 04:00 | 40 | 6 | 87.0% |
| 05:00 | 50 | 6 | 89.3% |
| 06:00 | 52 | 9 | 85.2% |
| 07:00 | 17 | 4 | 81.0% |
- 429 失败稳定 4-9/h, 累计 29/4h, 全 hermes caller, 全整 5min 边界点.
- 60min 失败明细: 06:35/07:10/15/20/25 — 全 %5==0 边界点, 非一次性风暴.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 失败全在 hermes caller 打 NVCF 5min 配额边界, 非 nv_gw 代码缺陷.
- 4h 429 失败 29/4h 稳定 4-9/h 全边界点, 未恶化 (>10/h 或蔓延至非边界点才需介入).
- R276 判断"持续性 NVCF 5min 配额边界周期性耗尽"本轮再获验证.

## 为何 cc2 不受影响
- `NVU_BUFFER_CALLERS=cc4101-primary,openclaw2` — cc2 primary 在 buffer 保护下.
- cc2 遇 429 → buffer 5key 轮转 (k0→k4 各 90s) → 切下一 key 绕过单 key 配额边界.
- hermes 不在 buffer 列表, 走 pexec peek path 一击即败, 是设计.

## 本轮动作
- 0 改动 0 restart. 十轮一致 R268-R277.

## health
- nv_gw /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv,
  nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], port=40006.
- 容器: nv_gw Up 1h, cc4101 Up 1h, ms_gw Up 3d, logs_db Up 3d.

## 下一步
1. cc2 session 恢复流量后, 复测 buffer 5key 轮转对 dsv4p_nv 5min 配额边界的抵抗力.
2. 持续监控 dsv4p_nv 5min 边界 429 是否恶化 (>10/h 或蔓延至非边界点). 现状 4-9/h 可接受.
3. 若未来 hermes caller 也需保护, 考察把 hermes 纳入 NVU_BUFFER_CALLERS (非本轮任务).
