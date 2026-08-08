# R1226 — cc2 nv_gw NOP 巡检轮 (SR 100%, 0 错误, fallback 0%)

- 时间: 2026-08-08 09:20 CST
- 类型: NOP (无改码)
- 上轮: R1225 (NOP, SR 100%)

## 30min 链路数据 (自查询)

- **cc2-primary (nv_requests)**: `200|100` → SR=100% (100/100), 0 4xx/5xx
- **错误分类 (caller=cc4101-primary status!=200)**: 0 rows → 无 buffer_exhausted / stream_total_deadline / 其他
- **tier 错误 (nv_tier_attempts)**: `NVCFPexecRemoteDisconnected|1` (仅 1 次, 见分析)
- **buffer 日志**: 全 `NV-BUFFER-SUCCESS ... after 1 attempt(s)`, elapsed 7-12s, 无 attempt>1 / 无 WAIT- / 无 buffer_exhausted
- **fallback (cc_requests)**: 0/f = 0%
- **容器健康**: nv_gw /health ok (5 keys + pexec_models 含 dsv4f0731_nv), cc4101 ok
- **容器 up**: nv_gw 29h, cc4101 29h, nv_gw_stable 6d

## 分析

- **主链 dsv4f0731_nv 单模式稳定**, cc2-primary 100/100 全 attempt=1 直接 success。
- **1 次 NVCFPexecRemoteDisconnected** (nv_key_idx=1, request 12c5d63d, 00:53:53 UTC):
  - **request caller = hermes** (非 cc2), 经 dsv4f0731 fid 281478d0。
  - **request 最终 status=200** self-heal 成功。
  - KeyManager 日志另有 2 次瞬时惩罚自愈 (`[08:20:03] k3 penalty=5s`, `[08:30:54] k5 penalty=5s`,
    transport_err 不累计 conn_count), 均被 5s 快速惩罚吸收。
  - **判归属 (request_id JOIN)**: hermes 线, 非 cc2 主链。瞬时 egress 抖动, 符合 R1077 self-heal 模式。
- **cc2 专属无任何异常**: 100/100 请求级 SR 100%, 0 错误。
- 无真实新失败 (非上轮 request_id), mihomo 升级监控触发条件 (真实新失败 + SR<99%) 不满足。
- k3 SSLEOFError (R1205/R1206) 持续不复发 (连续 6+ 轮), self-heal 离散瞬时确认。

## 决定

NOP,不改码。维持静稳观察。

## 下一步

维持观察。mihomo 升级监控触发条件: 后续轮次出现真实新失败 (非上轮 request_id) + SR<99% → 拉隧道线路排查。
k3 SSLEOFError 若连续复发 → 查 k3 mihomo 7896 线路。hermes 线瞬时 RemoteDisconnected 归属 hermes, 非 cc2 范围。