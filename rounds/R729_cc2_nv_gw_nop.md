# R729 — cc2 nv_gw NOP 巡检 (2026-08-04 05:25 CST)

## 改动: 不改码 (NOP)

## 依据 (30min 窗口)
- **cc2 (cc4101-primary) glm5_2_nv 30min**: 42 req, 42×200, SR **100.0%**
  - 累计 dur 39530ms (avg ~940ms/req, 但字段含义待复核; 实际含流式时间)
  - 0 fallback 触发, 0 错误
- **per-key × tier (glm5_2_nv)**: 混合链路全 success 运转
  - k0 pexec_success 6
  - k1 integrate_success 12
  - k2 pexec_success 8
  - k3 integrate_success 10
  - k4 pexec_success 6
  - 合计 42 attempts, 0 失败, 无任何 error_type → per-key 混合链路 (pexec+fid1/2/3 与 integrate+5IP) 全部健康
- **错误分类 30min**: 0 错误 (无新错误类型)
- **buffer/wait/keymanager 日志**: 无触发 (链路全程直通, 无 key cooling / 无 buffer 重试 / 无 wait queue)
- **对比前轮**: R727/R728 glm5_2_nv 零流量 (用户无请求), R729 流量恢复且 100% SR — 这是混合链路在真实流量下的健康验证

## 验证 (NOP 无需 restart)
- `/health`:
  - nv_gw ok (5keys, default glm5_2_nv)
  - dsv4p_nv40066 ok (5keys)
  - cc4101 ok (primary glm5_2_nv)
- `docker ps`: nv_gw Up 3h, dsv4p_nv40066 Up 3h, cc4101 Up 8h, nv_gw_stable Up 2days, logs_db Up 4days — 全 Up
- 配置零漂移 (R661 baseline 沿用)

## 链路状态结论
- glm5_2_nv per-key 混合链路: ✅ SR 100% (42/42)
- fallback 触发率: ✅ 0% (目标 <10%)
- 用户可见 SR: ✅ 100% (目标 99%+)
- k2 (pexec+fid2) 历史重灾的 conn_RD 本轮 0 出现 — 持续观察是否稳定

## 下一步
- 持续监控: cc2 SR + fallback 触发率 + per-key 分布 + k2 稳定性
- glm5_2_nv 流量持续时, 关注 k2 pexec conn_RD 是否复发 (R728 提到的历史根因)
- 流量低时不动码, 仅 NOP 记数据
- R661 post-restart ~46h+ 配置稳定, 无新错误类型

## 参数快照 (无变化, 沿用 R661)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
  - per-key FID bind: NV_GLM52_KEY_FID_BIND=0:0;2:1;4:2 (k0/k2/k4 pexec fid1/2/3)
  - per-key mode bind: NV_GLM52_KEY_MODE_BIND=0:pexec_us_rr;1:integrate_us_rr;2:pexec_us_rr;3:integrate_us_rr;4:pexec_us_rr
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=dsv4p_nv→dsv4p_nv40066:40066, STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
