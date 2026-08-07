# R1089 cc2 NOP — primary 95/96=99.0% SR, 1 transient bad=502 buffer_exhausted (SSLEOF egress blip 延续 R1088, self-heal 复窗口100% clean); 60min 211/212=99.5%; fallback 0.0%

日期: 2026-08-07 21:24 CST

## 结论
**NOP 巡检轮, 不改码。** 主链 cc4101-primary (nv_gw:40006) 30min = **95/96 = 99.0% SR, 1 bad**。
单 bad (13:15:13 UTC req) 为 buffer_exhausted 40665ms, 与 R1088 (21:15 CST 同 req=9baaf179) 同一
多 US egress IP 瞬时 SSLEOFError transient blip 尾迹, 特征完全一致 (已归档 R1077/R1082/R1087/R1088 同签名)。
**blip 后复窗口 (13:15:13 → 21:23) 211×200, buffer 全部 attempt-1/2 直 flush 秒回, 零持续分布**, self-heal 机制健壮,
per-key 全 5 key pexec_success 无单 key 连续失败, fallback 0.0%。非配置漂移, 无参数可调。

## 依据 (轮前注入 21:22:33 + DB/日志复核 21:23-21:24 + /health 复核 2026-08-07)

- **30min cc4101-primary (主 nv_gw:40006) = 95/96 = 99.0% SR, 1 bad** (`SELECT status,count(*) FROM nv_requests
  WHERE created_at>now()-interval '30 min' AND caller='cc4101-primary'` → 95×200 + 1×502 buffer_exhausted 40665ms)。
- **60min 复核 (更稳窗口) = 211×200 + 1×502** (SR=99.5%), 唯一 bad=13:15:13 UTC buffer_exhausted (即 R1088 已根因的
  21:15 CST req=9baaf179, 124K thinking 流多 IP 瞬时 SSLEOFError 尾迹)。
- **self-heal 铁证**: 13:15:13 bad 后无任何 status=502 新增; buffer 日志 (docker logs nv_gw --since 60m) 显示
  `605053f1` 仅 attempt=2 (5s backoff) 后 success_tool_call 直 flush, 其余 `e42ac37c/a8fe3abb/f7c591cc...`
  全部 **attempt=1/5 直 flush 秒回 (5-10s)**, 无 3-attempt fail-fast 级联, 无冷却堆积, 无 WaitQueue。
- **per-key 健康**: nv_tier_attempts(`created_at`) 60min 全 5 key 均高 pexec_success (k0 42/k1 41/k2 42/k3 43/k4 42),
  仅 k3 2 次 transient NVCFPexecRemoteDisconnected (补回, 无单 key 连续失败)。
- **30min fallback 0/96 = 0.0%** (bad 本身已计为 NV 非成功; 复窗口全走主链)。
- **/health 实测**: 40006 nv_gw 200 (passthrough, 5 key), 4101 cc4101 200 (primary dsv4f0731_nv), 40066 dsv4p_nv40066 200。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **95/96 = 99.0% SR, 1 bad** (transient egress blip 尾迹) | ⚠️→self-heal 复窗口100% |
| 60min 复核 | 211×200 + 1×502 = 99.5% | ✅ 非持续分布 |
| 30min 错误分类 | 仅 1× buffer_exhausted (已根因, R1088 同 req) | ✅ |
| per-caller 归属 | 主链 1 bad=transient; hermes 0 bad | ✅ |
| per-key 健康 | 5 key 全 pexec_success (41-43/k); 仅 k3 2x transient RD | ✅ |
| 30min fallback | 0/96 = 0.0%, 复窗口全走主链 | ✅ |
| buffer | 复窗口全部 attempt-1/2 直flush 秒回, 零 fail-fast 级联 | ✅ self-heal 正常 |
| 容器 /health | 40006/4101/40066 全 200 | ✅ |

## 下一步
- 保持 NOP 观察。本轮 1 transient 502 为 R1088 同根因尾迹 (多 US egress IP 瞬时 SSLEOFError, 大 thinking 流放大窗口敏感度),
  AKE fail-fast + 复窗口 attempt-1/2 秒回证明 self-heal 机制健壮, 非配置漂移。
- 关注点: 若**同一 egress IP (7894/7896/7897/7899/7901) 在未来 1-2h 多轮**连续 SSLEOFError+缓冲重试
  (不再让 attempt-1 直flush) 才查该代理线路 / mihomo 端口, 当前无需动作。
- 持续 clean ≥ 数轮后评估是否需对 124K+ thinking 大流裁减 (buffer_exhausted 概率随 input 上升属模型/流特性, 非链路 bug)。