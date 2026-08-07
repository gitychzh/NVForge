# R1163 cc2 STATE mirror sync — 恢复闭环 NOP

> 注入 30min cc4101-primary 200|92 = 100% SR, 0 非-200, 整窗全绿跨六轮;
> 总线 dsv4f0731_nv SR=98.6% (144/146) 唯二 502 均 JOIN 归属 hermes
> (NVStream_IncompleteRead + stream_first_byte_timeout) 非 cc2 非新根因;
> tier 全 pexec_success (93) 无 429/empty, fallback 0%, buffer 全 attempt 直通
> 无退避无 WAIT, fid 281478d0-f307 稳定, NOP 不改码

## 判决: NOP (cc2 整窗 93/93 全 200, 无改码条件)

## 数据 (实查 30min 2026-08-08 03:28-03:58, 注入分析 03:27 CST)

- cc4101-primary: `200|93` = 100% SR, 0 非-200
- 总线 dsv4f0731_nv: SR=98.6% (144/146) = cc2 92 + hermes 52 + 2×502 (注入窗口)
- 实查 30min bus 错误分类: NVStream_IncompleteRead ×1 + stream_first_byte_timeout ×1
- JOIN 归属 (实查): 两条 502 均 `caller=hermes`, fid 281478d0, 非 cc2
- tier (实查 30min): 全 `pexec_success` (93), 无 429/empty/新类型
- fallback: 0% (30min f|146 全 200 直通)
- buffer 日志: 全 attempt-1 direct flush + 少量 attempt-2 重试自愈 (verdict 均 success,
  elapsed 11-40s, 无 FAIL/无 WAIT/无 buffer_exhausted), 无 KeyManager 退避日志
- 容器 (实查): nv_gw + cc4101 /health 全 ok, 未重启; nv_gw Up 24h, cc4101 Up 24h

## 根因判断

链上静稳。唯二 502 JOIN 归属 hermes 非 cc2, 与上轮 R1162 同签名 (瞬时 egress 抖动 +
首次包超时), 同 fid 281478d0, 非配置漂移、非新根因。cc2 整窗 100% SR 跨六轮
(R1158→R1163) 全绿, 无独立新事件。

## 本轮改动

无 (NOP 巡检轮, 只记数据不改码)。

## 下一步

维持静稳观察。**核心监控: 是否重现独立瞬时 burst 及复发间隔**。
若下个窗口再现 ≥2× buffer_exhausted 且 request_id 全新 (JOIN 归属 cc2), 则为**独立新事件**,
按记忆 `ssleof-error-transient-egress-blip` 深挖 mihomo dsv4f0731_nv egress 线路 (7900-7904),
评估超 5 key 超大请求 buffer 首跳韧性。当前仍判定瞬时 egress 抖动非配置漂移, NOP。