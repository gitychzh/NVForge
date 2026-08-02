# R295 — NOP 巡检轮 (2026-08-02 16:44 CST)

## 本轮动作
- NOP 巡检轮. 0 改动 0 restart. 接棒 R294, 数据一致.
- 健康: `curl /health` ok, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv].
- docker ps: cc4101/nv_gw (Up 2h), nv_gw_stable (Up 15h), ms_gw/logs_db (Up 3d) 全 Up.

## 数据 (30min 注入 ~16:44 CST)

### cc2 (cc4101-primary) 30min 0 req
- session 间歇空闲, 链路空���健康. 0 fallback 0 deadline.
- buffer/wait/keymanager 日志 30min 空.

### dsv4p_nv 30min 全 caller SR=37.5% (3/8)
| status | count | 备注 |
|---|---|---|
| 200 | 3 | key2 egress 203.10.96.139 avg_dur 16032 |
| 429 | 5 | function 级配额边界 |

caller: hermes → 3×200 + 5×429. (cc4101-primary 0 req 不受影响)

按分钟趋势 (NVCF function 配额周期自恢复):
- 08:15/08:20/08:25/08:30 → 4×429 (配额耗尽窗口)
- 08:35 → 1×200, 08:36 → 2×200 (恢复)
- 08:40 → 1×429 (再次触底, 周期性)

per-key: key2 → 3×200 + 5×429. per-egress: 203.10.96.139 → 3×100.

### 错误分类
- 全 `all_tiers_exhausted` (5 条, avg_dur 1949ms), 无新错误类型, 与 R268-R294 一致.
- fallback 0/8. tier_attempts 30min 0 行.

## 根因 (沿用 R278-R294)
- buffer 5key 轮转对 function 级 429 失效: 5key 全绑同一 NVCF function,
  function 配额耗尽时 5key 同时 429 → all_tiers_exhausted.
- 设计盲区非代码缺陷. NVCF function 级配额是上游硬限制.
- 08:15-08:30 连 429 → 08:35-08:36 恢复 3×200 → 08:40 再 429, 周期自恢复.
- cc2 流量极低, 不受影响, 不达介入阈值.

## 判稳
- **NOP**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 低 SR 是 NVCF function 配额周期, 自恢复, 非代码缺陷.
- 二十八轮一致 R268-R295.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障再介入.
