# R1088 cc2 NOP — primary 99/100=99.0% SR, 1 transient bad=502 buffer_exhausted (124K thinking 流多IP瞬时SSLEOF blip, AKE fail-fast 提前截断 self-heal); 复窗口回 100% clean; fallback 0.0%

日期: 2026-08-07 21:17 CST

## 结论
**NOP 巡检轮, 不改码。** 主链 cc4101-primary (nv_gw:40006) 30min = **99/100 = 99.0% SR, 1 bad**。
连续 6 轮全 clean (R1081-R1087) 后本轮 1 个 transient bad: req=9baaf179 124K-token thinking 大流,
在 ~21:14:30–21:15:15 约 1min 窗口内多 US egress IP 瞬时 SSLEOFError, 3 次 consecutive all_keys_exhausted
→ AKE fail-fast 提前 40s 截断走 ms_gw, **之后所有请求 attempt-1 秒回 100% clean**。self-heal 机制健壮,
特征与已归档 transient SSLEOFError egress blip (R1077/R1082) 完全一致, 非配置漂移, 无参数可调。

## 依据 (轮前注入 21:16:33 + DB/日志复核 21:17 + /health 复核 2026-08-07)

- **主链 cc4101-primary = 99/100 = 99.0% SR, 1 bad** (`SELECT status,count(*) FROM nv_requests
  WHERE created_at>now()-interval '30 min' AND caller='cc4101-primary'` → 99×200 + 1×502 buffer_exhausted 40665ms)。
- **单 bad 根因定位 (nv_gw 日志铁证)**: req=9baaf179 (input=78587c, 124K thinking) 在 21:14:46 (k4 SSLEOFError)、
  21:15:06 (k5 SSLEOFError) 多 key 瞬时 SSLEOFError → 3 次 consecutive all_keys_exhausted →
  `NV-BUFFER-AKE-FASTM` (3 连续 AKE ≥3 fail-fast) → skip WaitQueue → 21:15:13 `NV-BUFFER-EXHAUSTED` → ms_gw
  (40665ms 提前截断, 未榨干 450s buffer 预算)。
- **self-heal 铁证**: 21:15:24 起 `f7347c11/bf3150ec/b287bac5/fc57becf/34654518...` 全部 attempt=1/5 直 flush 秒回 200,
  复窗口 100% clean。fail-fast (3 连续 AKE → 30s 内截断) 工作正确, 未拖垮后续请求。
- **30min 错误分类**: 仅 1× buffer_exhausted (即上述, 已根因)。2h 内 2× buffer_exhausted (12:19/13:15 UTC) 间隔 1h, 非持续分布。
- **per-caller 归属**: dsv4f0731_nv 总 144 请求 144×200 (SR=100.0%); hermes 0 bad。
- **per-key 健康**: nv_tier_attempts(`created_at` 列) 全 5 key 高 pexec_success (k0 19/k1 20/k2 18/k3 20/k4 19);
  仅 k3 1 次 transient NVCFPexecRemoteDisconnected, 无冷却堆积, 无单 key 连续失败。
- **30min fallback 0/145 = 0.0%** (bad 本身已计为 NV 非成功; 复窗口全走主链)。
- **/health 实测**: 40006 nv_gw 200 (passthrough, 5 key), 4101 cc4101 200 (primary dsv4f0731_nv)。

## 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **99/100 = 99.0% SR, 1 bad** (transient egress blip) | ⚠️→self-heal 复窗口100% |
| 30min 错误分类 | 仅 1× buffer_exhausted (124K thinking 流, 已根因) | ✅ 非持续分布 |
| per-caller 归属 | 主链 1 bad=transient; hermes 0 bad | ✅ |
| per-key 健康 | 5 key 全 pexec_success (18-20/k); 仅 k3 1x transient RD | ✅ |
| 30min fallback | 0/145 = 0.0%, 复窗口全走主链 | ✅ |
| buffer | 复窗口全部 attempt-1 直flush; 9baaf179 触发 AKE fail-fast 提前截断 | ✅ self-heal 正常 |
| 容器 /health | 40006/4101 全 200 | ✅ |

## 下一步
- 保持 NOP 观察。本轮 1 transient 502 根因=~1min 多 US egress IP 瞬时 SSLEOFError (大 thinking 流放大窗口敏感度),
  AKE fail-fast + 复窗口 attempt-1 秒回证明 self-heal 机制健壮, 非配置漂移。
- 关注点: 若**同一 egress IP (7894/7896/7897/7899/7901) 在 2h 内多轮**连续 SSLEOFError+缓冲重试
  (不再让 attempt-1 直flush) 才查该代理线路 / mihomo 端口, 当前无需动作。
- 持续 clean 数轮后评估是否需对 124K+ thinking 大流裁减 (buffer_exhausted 概率随 input 上升属模型/流特性, 非链路 bug)。