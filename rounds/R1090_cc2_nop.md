# R1090 cc2 NOP — primary 93/94=98.9% SR, 1 bad=502 buffer_exhausted (R1088 同 req=9baaf179, 历轮已知容器尾迹, self-heal 复窗口全 200); per-key 全 pexec_success 零 tier 错误; fallback 0.0%

日期: 2026-08-07 21:32 CST

## 结论
**NOP 巡检轮, 不改码。** 主链 cc4101-primary (nv_gw:40006) 30min = **93/94 = 98.9% SR, 1 bad**。
单 bad = req=**9baaf179** (13:15:13 UTC) buffer_exhausted 40665ms — 与 R1088/R1089 文档化的同一 req ID、同一
124K thinking 流多 US egress IP 瞬时 SSLEOFError transient blip 尾迹 (已归档 R1077/R1082/R1087/R1088 同签名), **非新错误**,
非配置漂移。复窗口 buffer 全部 attempt-1/5 直 flush success_tool_call 秒回 (4-16s), 零 fail-fast 级联, 零冷却, 零 WaitQueue。
per-key 全 5 key 均 pexec_success (**本轮零 tier 错误**, 上轮 k3 2x transient RD 也未再出现)。fallback 0.0%。容器 /health 全 200。

## 依据 (轮前注入 21:29:33 + DB/日志复核 21:30-21:32 + /health 复核 2026-08-07)

- **30min cc4101-primary (主 nv_gw:40006) = 93/94 = 98.9% SR, 1 bad** (`SELECT status,count(*) FROM nv_requests
  WHERE created_at>now()-interval '30 min' AND caller='cc4101-primary'` → 93×200 + 1×502)。
- **唯一 bad 定位**: `SELECT request_id,status,error_type,duration_ms,created_at FROM nv_requests WHERE status!=200
  AND caller='cc4101-primary' AND created_at>now()-interval '60 min'` → **req=9baaf179, 502 buffer_exhausted, 40665ms,
  13:15:13 UTC**。该 request_id 与 R1088/R1089 已根因的 req 完全一致 (R1088 21:15 CST 124K thinking 流瞬时 SSLEOFError
  egress blip 尾迹), **同一条已知 historical bad**, 无任何新签名的 502。
- **self-heal 铁证**: 9baaf179 后无任何 status=502 新增; buffer 日志 (docker logs nv_gw --since 30m) 显示复窗口
  `ae00e936/1a5810cf/c9314851/26c49091/3f5c5ca5...` 全部 **attempt=1/5 verdict=success_tool_call 直 flush 秒回 (4-16s)**,
  无 3-attempt fail-fast 级联, 无冷却堆积, 无 WaitQueue。
- **per-key 健康**: nv_tier_attempts(`created_at`) 30min 全 5 key 均 pexec_success (k0 16/k1 17/k2 18/k3 21/k4 20),
  **零 tier 错误** (无 RemoteDisconnected, 无 429, 无冷却堆积)。较 R1089 (k3 2x transient RD) 更干净。
- **30min fallback 0/95 = 0.0%** (bad 本身已计为 NV 非成功; 复窗口全走主链)。
- **/health 实测**: 40006 nv_gw 200 (passthrough, 5 key), 40066 dsv4p_nv40066 200。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **93/94 = 98.9% SR, 1 bad** (R1088 同 req=9baaf179, 已根因) | ⚠️→self-heal 复窗口全200 |
| 30min 错误分类 | 仅 1× buffer_exhausted (历轮已知容器尾迹) | ✅ 非新错误 |
| per-caller 归属 | 主链 1 bad=known transient; hermes 0 bad (44×200) | ✅ |
| per-key 健康 | 5 key 全 pexec_success (16-21/k), **零 tier 错误** | ✅ |
| 30min fallback | 0/95 = 0.0%, 复窗口全走主链 | ✅ |
| buffer | 复窗口全部 attempt-1 直flush success_tool_call 秒回(4-16s) | ✅ self-heal 正常 |
| 容器 /health | 40006/4101/40066 全 200 | ✅ |

## 下一步
- 保持 NOP 观察。本轮 1 transient 502 与 R1088/R1089 完全同一 req=9baaf179 (124K thinking 流瞬时 SSLEOF egress blip
  尾迹), AKE fail-fast + 复窗口 attempt-1 秒回证明 self-heal 机制健壮, 非配置漂移, 无参数可调。
- 关注点: 若**同一 egress IP (7894/7896/7897/7899/7901) 在未来 1-2h 多轮**连续 SSLEOFError+缓冲重试
  (不再让 attempt-1 直flush) 才查该代理线路 / mihomo 端口, 当前无需动作。
- 持续 clean ≥ 数轮后评估是否需对 124K+ thinking 大流裁减 (buffer_exhausted 概率随 input 上升属模型/流特性, 非链路 bug)。