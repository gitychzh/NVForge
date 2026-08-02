# R431 — NOP 巡检轮 (2026-08-03 01:25 CST)

## 摘要
- 0 改动 0 restart. NOP 巡检轮.
- cc2 (cc4101-primary) 30min 0 req (session 间歇空闲).
- dsv4p_nv 全 caller 30min SR=80.0% (12/15), 3×429 all_tiers_exhausted (avg 2191ms), 较 R430 的 63.6% 回升.

## 链路数据 (注入, 30min 窗口)
- caller×model×status: hermes|dsv4p_nv|200×11, hermes|dsv4p_nv|429×3, openclaw|dsv4p_nv|200×1
- 模型 SR: dsv4p_nv 80.0% (12/15)
- 错误分类: all_tiers_exhausted|all_tiers_failed_in_mapped_tier|3|2191ms
- per-key (dsv4p): k2×200×11, k3×200×1; 3×429 无 key 归属 (空 IP)
- per-egress-IP: 203.10.96.139 11/11=100%, 134.195.101.194 1/1=100%, 空 IP 3/3=0%
- 200 延迟: avg 10226ms, max 16649ms, min 3382ms, avg_ttfb 9694ms
- 200 finish_reason: tool_calls×8, stop×4
- 时间分布: 16:50/16:55/17:00 三连 429 → 17:05-17:16 连续 12×200 恢复
- buffer/wait/keymanager 日志: 无 (cc4101-primary 0 req 未触发)

## 判稳
- cc2 0 流量 → 无评估样本, 改前无数据 (铁律1 不满足), 不动码.
- 错误类型仅 all_tiers_exhausted, 无新增, 模式与 R268-R430 一致 (一百六十余轮一致).
- dsv4p_nv SR 63.6% → 80.0% 回升, 恢复迅速.
- 3×429=6/h 在阈值边缘, 但全在窗口前半段 (16:50-17:00), 后半段 (17:05-17:16) 全 200.

## 容器健康
- curl /health: status=ok, nv_num_keys=5, nv_default_model=glm5_2_nv.
- docker ps: nv_gw Up 11h, cc4101 Up 33min, nv_gw_stable Up 23h, ms_gw Up 3d, logs_db Up 3d.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv buffer 路径行为.
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.
- dsv4p_nv 小时级 SR 持续 <70% + cc2 缓冲流量恢复后再评估是否切换 PRIMARY_UPSTREAM_MODEL.
- all_tiers_exhausted 持续 >=5/h 且后半段不恢复 再评估 buffer/KeyManager 参数.
