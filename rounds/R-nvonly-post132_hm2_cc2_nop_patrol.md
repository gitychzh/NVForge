# R-nvonly-post132 — NOP 巡检轮 (hm2_cc2)

**时间**: 2026-08-02 07:55 CST
**上轮**: R-nvonly-post131 (已 push, HEAD ef63dc5)
**本轮**: NOP 巡检轮, 0 改动, 0 重启

## 判稳依据

### cc2 (cc4101-primary) 30min 窗口 — 0 req
session 轮前无流量产生, 无数据可判 cc2 SR.
链路健康无故障: 容器全 Up, env 配置正确, 0 cc2 tier error, 0 buffer/wait 日志,
0 stream_total_deadline (6h).

### 其他 caller (hermes, 非 cc2 链路)
| caller | model | status | count |
|--------|-------|--------|-------|
| hermes | dsv4p_nv | 200 | 1 |
| hermes | dsv4p_nv | 429 | 5 |

dsv4p_nv SR=16.7% (1/6): 5×429 (all_tiers_exhausted, 5key 全挂) + 1×200.
周期性 5min 一发 429 (23:30-23:55 UTC), NVCF 侧 dsv4p 限流模式.
**与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv).
30min fallback 发生率: f=6 (dsv4p 全挂 fallback ms, ms_gw fallback 正常工作).

### 与 post131 对比
- 窗口模式一致: cc2 0 req, dsv4p_nv 限流仍局限 hermes caller.
- post131: dsv4p SR=0.0% (0/6); post132: dsv4p SR=16.7% (1/6) — 略有恢复, 仍 NVCF 侧.
- glm5_2_nv 连续 post100-post132 (33 轮) 无 dsv4p 故障扩散, 无新错误.

## 健康验证 (07:55 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 6h, ms_gw/logs_db Up 2d ✓ |
| cc2 (cc4101-primary) 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min 错误分类 | all_tiers_exhausted × 5 (全 hermes+dsv4p, 非 cc2) ✓ |
| stream_total_deadline (6h) | 0 ✓ |
| buffer/wait 日志 | 无 (cc2 0 req) ✓ |

## 本轮改动
无. NOP 巡检轮.

## 下一步
- 继续巡检. 等 cc2 有流量时观察 glm5_2_nv SR.
- dsv4p_nv 限流持续, 但属 NVCF 侧 + hermes caller, 非本轮职责.
- glm5_2_nv 链路连续 33 轮稳定, 无需调整.
