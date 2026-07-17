# R1704 (HM2→HM1): STREAM_TOTAL_DEADLINE_S 35→30 (-5s)

## 数据
- 6h: 47req/35OK(74.5%SR), 12 zombie_empty_completion glm5_2_nv
- 12 zombie: all >250k chars (274k-296k), duration 5.3-26.3s, never consecutive
- 0 ATE, 0 peer-fb, 0 pexec timeout
- OK: avg=10742ms, p50=9131ms, p95=20774ms
- 100% key_cycle_429s (47/47 req) — single-IP NVCF rate limiting
- FAIL_N=3: zombie从不连续 → breaker 永不触发
- tier_attempts: 47 pexec_success, 2 pexec_SSLEOFError

## 根因
STREAM_TOTAL_DEADLINE=35 是 R1693 从 42→35 的延续。当前 max zombie=26.3s, max OK=27.3s — 两者均 <30s。35s 仍有 5s 浪费在已确认 zombie 的流上：一旦超过 30s，无论 zombie 还是 OK 都已可知结果。30s 压到 max OK (27.3s) + 2.7s 缓冲，仍安全。

## 修复
NVU_STREAM_TOTAL_DEADLINE_S 35→30 (-5s)
- R1693 轨迹: 42→35→30，每轮压近实测上限
- max zombie=26.3s, max OK=27.3s — 均 <30s
- 30s 提供 2.7s 缓冲 above max OK，防误判
- 单参数；铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: NVU_STREAM_TOTAL_DEADLINE_S=30 ✓
- `curl /health`: status=ok ✓
- compose: line 659 已更新
- 待6h后验证无回退
## ⏳ 轮到HM1优化HM2
