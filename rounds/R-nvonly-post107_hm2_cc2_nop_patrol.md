# R-nvonly-post107 — hm2_cc2 NOP 巡检轮 (2026-08-02 06:45 CST)

## 本轮结论
- **NOP 巡检轮**: cc2 (cc4101-primary) 30min 0 req, session 轮前无流量产生, 无数据可判 cc2 SR.
- 链路健康无故障: 容器全 Up (nv_gw/cc4101 5h, nv_gw_stable 5h, ms_gw/logs_db 2d),
  env 配置正确 (NVU_DISABLE_MS_FALLBACK=0 fallback 已恢复, buffer 5×90s=450s, cc4101 deadline 470s),
  0 cc2 tier error, 0 cc2 buffer/wait/error 日志. 0 改动, 0 重启.
- dsv4p_nv (hermes caller, 非 cc2 链路) SR=37.5% (3/8, 3×200 + 5×429/all_tiers_exhausted), 较上轮 0.0% 略有恢复.
  周期性 5min 一发 429 模式持续, NVCF 侧 dsv4p 限流, 非 cc2 链路问题 (cc2 走 glm5_2_nv).
- fallback 发生率 f=8 (dsv4p 全挂 fallback ms, ms_gw fallback 已恢复正常工作).

## 依据 (轮前链路分析注入)
- cc4101-primary 30min: 0 rows (无 cc2 流量, 链路健康无故障).
- hermes|dsv4p_nv: 200×3 + 429×5, SR=37.5% (3/8).
- 错误分类: all_tiers_exhausted × 5 (hermes+dsv4p, 5key 全挂周期性 429, 非 cc2).
- dsv4p per-key: key2=200×3 (11977ms), 空 key=429×5 (2604ms).
- dsv4p per-egress-IP: 203.10.96.139=200×3, 空 IP=429×5.
- dsv4p 按分钟趋势: 22:15-22:35 周期性 429×1/5min, 22:40 恢复 200×3.
- buffer/wait 日志: 无 (cc2 0 req).

## 与上轮对比
| 项 | post106 | post107 |
|----|---------|---------|
| cc4101-primary 30min | 0 req | 0 req |
| dsv4p_nv SR | 0.0% (0/6) | 37.5% (3/8) |
| glm5_2_nv 扩散 | 无 | 无 |
| 链路健康 | 健康 | 健康 |
| 改动/重启 | 0/0 | 0/0 |

dsv4p_nv 从 0.0% 部分恢复到 37.5%, 但仍限 hermes caller, 未扩散到 glm5_2_nv (post100-post107 连续 8 轮无扩散).

## 健康验证 (06:45 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101 Up 5h, nv_gw_stable Up 5h, ms_gw/logs_db Up 2d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 错误分类 | all_tiers_exhausted × 5 (全 hermes+dsv4p, 非 cc2) ✓ |

## 下一步
- 持续监控 cc2 (cc4101-primary) 流量恢复后 SR. 本 session 工具调用经 cc4101→nv_gw 链路, 实际有流量但 nv_requests 写入依赖 caller 标记, 轮前快照时点 0 req.
- 关注 dsv4p_nv 周期性 429 是否持续或自恢复 (NVCF 侧限流, 不在 cc2 优化范围).
- 若 glm5_2_nv 出现 429/timeout/error 扩散, 立即查根因 + 小步改.
- 链路健康 + 无 cc2 流量 → 继续 NOP 巡检节奏.

## 参数快照 (2026-08-02 06:45 CST)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF, fallback ms_gw(40007) 已恢复
- 铁律: 只改 HM2 nv_gw, 不碰 HM1, 不碰 ms_gw 源码, 改前有数据改后必验证
