# R1096 cc2 NOP — primary 100/100=100% SR 零错误 (cc4101-primary 经 nv_gw dsv4f0731_nv)

> 轮次: R1096 | 日期: 2026-08-07 ~22:0x CST | 类型: NOP 巡检/不改码
> 上轮: R1095 (NOP, 102/102=100% SR 零错误)
> 判定: cc2 主链 100% SR, 0 bad, 0 fallback, 无新签名 → NOP

## 本轮改动: 无

## 数据 (实测 DB 2026-08-07 22:0x CST + docker logs)

- **cc2 专属 (cc4101-primary) 30min**: `nv_requests` = **100/100 = 100.0% SR, 0 错误** (status 只含 200)。
  (轮前注入为 102/102 同 100%; 窗口滚动差异, 实测当前窗口 100/100 复核一致)
- **错误分类 (cc4101-primary)**: 0 rows — **cc2 零错误**。
- **30min 全量错误归属**: 唯一 3× `zombie_empty_completion` 全部 caller=**hermes** (peer, dsv4f0731_nv 线),
  非 cc2 主链, 不计入 cc2 指标 (记忆 bad-fid request_id JOIN 复核归属)。
- **cc_requests 真实 SR (含 fallback)**: 101/101 = **100.0%**, fallback 0/101 = **0.0%** (全走主链)。
- **nv_tier_attempts 30min per-key**: 5 key 全 `pexec_success` (0/1/2/3/4 = 21/16/19/23/22) = 健康主态。
  仅 2 个一次性 transient: k2 1× `NVCFPexecRemoteDisconnected`, k4 1× `empty_200`。**无持续 tier 错误**。
- **buffer 日志 (--since 30m)**: 绝大多数 cc2 请求 attempt-1 直 flush 秒回 (如 req=eea7f297 10.1s)。
  唯一 req=6d9589b5: attempt-2 时 k4 一次性 **SSLEOFError** (transport_err, penalty 10s 不累计 conn_count)
  → NV-BUFFER-EXEC-FAIL attempt-2 (elapsed 26s) → 10s backoff → attempt-3 成功 flush (41.4s, success_tool_call,
  6885b) → **final status=200 零错误**。单 key egress 抖动, attempt-3 自愈, 零级联 (记忆 ssleof-transient R1077)。

## 结论

- cc2 主链 **100% SR, 零错误, 零 fallback**, buffer 全直 flush, 唯一 transient SSLEOFError/empty_200/RD
  皆为单 key 一次性且自愈, 非持续分布。无参数可调, 不改码。

## 下一步

- 保持 NOP 观察。hermes 3× zombie_empty_completion (peer) 持续关注但归属非 cc2 不改动。
- 若 SSLEOFError/RD 多 key 连续复发且不再 attempt-N 自愈直 flush, 才查 mihomo 线路端口。

## 参数快照 (未动, 同 R1095)
- nv_gw: UPSTREAM_TIMEOUT=90, NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90×5, KEY_COOLDOWN_S=30,
  NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0, MODE_CHAIN=pexec_us_rr
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400
- 容器: nv_gw Up 19h, cc4101 Up 18h, 全 /health 200 (nv_num_keys=5)