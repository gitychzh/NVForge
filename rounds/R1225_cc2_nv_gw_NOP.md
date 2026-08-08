# R1225 — cc2 nv_gw NOP 巡检轮 (SR 100%, 0 错误, fallback 0%)

- 时间: 2026-08-08 08:50 CST
- 类型: NOP (无改码)
- 上轮: R1224 (NOP, SR 100%)

## 30min 链路数据 (自查询)

- **cc2-primary (nv_requests)**: `200|96` → SR=100% (96/96), 0 4xx/5xx
- **错误分类 (status!=200)**: 0 rows → 无 buffer_exhausted / stream_total_deadline / 其他
- **tier 错误 (nv_tier_attempts, glm5_2_nv)**: 0 rows
- **buffer 日志**: 全 `NV-BUFFER-SUCCESS ... after 1 attempt(s)`, 无 attempt>1 / 无 WAIT- / 无 KEYMGR 惩罚 / 无 buffer_exhausted
- **fallback (cc_requests)**: 0/97 = 0%
- **容器健康**: nv_gw /health ok (5 keys + pexec_models 含 dsv4f0731_nv), cc4101 ok
- **容器 up**: nv_gw 29h, cc4101 29h, nv_gw_stable 6d

## 分析

- 主链 dsv4f0731_nv 单模式稳定, 全请求 attempt=1 直接 success。
- k3 SSLEOFError (R1205/R1206) 持续不复发 (连续 5+ 轮), self-heal 离散瞬时确认。
- 无真实新失败 (request_id 非上轮), mihomo 升级监控触发条件 (新失败 + SR<99%) 不满足。

## 决定

NOP,不改码。维持静稳观察。

## 下一步

维持观察。mihomo 升级监控触发条件: 后续轮次出现真实新失败 + SR<99% → 拉隧道线路排查。
k3 SSLEOFError 若连续复发 → 查 k3 mihomo 7896 线路。