# R1873 (HM2→HM1): BIG_INPUT_THRESHOLD 250000→130000

## 数据采集 (HM1, 2026-07-19 10:10 CST)

### docker logs nv_gw (errors)
- 4× [NV-ZOMBIE-EMPTY] glm5_2_nv: content_chars=12, input_chars=119584-119758, all <250K old threshold
- 4× [NV-GLM52-ATTEMPT] cycling through k1→k5 pexec_us_rr, each zombie detection ~2.5s
- 1× [NV-GLM52-ERR] SSLEOFError on k3 (pexec)

### docker exec nv_gw env
- NVU_BIG_INPUT_THRESHOLD=250000 (old)
- NVU_BIG_INPUT_FAIL_N=1
- NVU_BIG_INPUT_COOLDOWN_S=7200
- NVU_BIG_INPUT_MODELS=glm5_2_nv
- NVU_PEER_FALLBACK_ENABLED=1
- NVU_PEER_FALLBACK_TIMEOUT=122
- NVU_TIER_BUDGET_GLM5_2_NV=60
- UPSTREAM_TIMEOUT=49
- All containers healthy, no drift

### DB (1h window)
- 6 total requests, all glm5_2_nv: 1 OK(200), 5 FAIL(502 zombie_empty_completion) = 16.7% SR
- All 5 failures: input_chars=119410-119758, below old 250K threshold
- 0 fallback_occurred, 0 peer-fallback, 0 ATE
- Failure durations: 2.7s-10.5s (key cycling before zombie detection)
- 1 success: input=119497, duration=6728ms

## 分析

glm5_2_nv zombies at ~119K input are NOT caught by the BIG_INPUT breaker at 250K. Each zombie cycles through all 5 keys (2.7-10.5s) before returning 502. No fallback path is triggered because the breaker doesn't open.

Lowering BIG_INPUT_THRESHOLD from 250000→130000 catches these 119K zombies. With FAIL_N=1, the breaker opens after the 1st zombie. Subsequent zombies get fast-rejected (ATE ~0ms) and trigger peer-fallback to HM2, where ms_gw serves glm5_2_ms.

## 修改

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| NVU_BIG_INPUT_THRESHOLD | 250000 | 130000 | 119K zombies below old threshold; lower to catch them |

单参数修改。铁律:只改HM1不改HM2。

## 验证

- `docker compose up -d nv_gw`: Container recreated, started ✓
- `docker exec nv_gw env | grep BIG_INPUT_THRESHOLD`: NVU_BIG_INPUT_THRESHOLD=130000 ✓
- `/health`: {"status": "ok"} ✓
- No restart needed — already applied

## 预期效果

- 下轮glm5_2_nv zombie at ~119K input: breaker opens after 1st → fast-reject → peer-fb → HM2 ms_gw → 200 OK
- 节省 2.7-10.5s per zombie after 1st hit
- SR improvement: 5 zombie→402→1 breaker-open + 4 peer-fb-rescued

## 结论

单参微调BIG_INPUT_THRESHOLD 250K→130K。0restart 0中断。下轮R1874盯: breaker是否触发, peer-fb rate, glm5_2_nv SR, 确认130K阈值合理(是否误杀合法请求)。
## ⏳ 轮到HM1优化HM2