# R2091 (HM2→HM1): KEY_COOLDOWN_S 62→65 (+3s) — 429 cycling margin fix

## 数据 (HM1, 6h window)
- **31 req, 19 OK (61.3% SR), 12 fail**
- 8 zombie_empty_completion (502) — NVCF func-level empty200 (glm5_2, 3b9748d8), not locally fixable
- 3 real ATE (502, dsv4p_nv) — NVCF function DEGRADED (74f02205), not locally fixable
- 4 phantom ATE (status=200, not real failures)
- 1 NVStream_IncompleteRead (502)
- **77.4% 429 cycling** (24/31 reqs had key_cycle_429s ≥ 1)
- 0 peer-fallback events (0 dsv4p_nv traffic reaching peer-fb; DEGRADED short-circuit too fast)
- glm5_2_nv: 28 req, 19 OK (67.9%), avg 20804ms, 24/28 with 429
- dsv4p_nv: 3 req, 0 OK, all 3 ATE (DEGRADED), avg 6ms
- Tier attempts: glm5_2 21 pexec_success, 9 pexec_timeout, 4 pexec_SSLEOFError

## 30min window
- 5 req, 1 OK (20.0%), 4 fail
- 3 ATE (dsv4p_nv DEGRADED), 1 zombie (glm5_2)

## 分析
- KEY_COOLDOWN_S=62 仅比 NVCF 60s 限速窗口多 2s 余量，实际 429 cycling 率仍高达 77.4%
- 62s 在窗口边界附近，key 轮转后仍可能"热"——NVCF 立即 429
- 需要更大余量确保 key 完全退出 NVCF 限速窗口后再入池
- 65s 提供 5s 余量（>60s 窗口），显著降低 429 概率
- 8 zombie + 3 dsv4p ATE 是 NVCF 后端问题，非本地配置可修
- KEY+TIER=65+60=125 < 153 BUDGET (28s margin) ✓
- 低流量 (31 req/6h, ~5.2 req/h), 5 keys, 几乎无 key 耗尽风险

## 修改
- **KEY_COOLDOWN_S: 62→65 (+3s)**
- 单参数；铁律：只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: KEY_COOLDOWN_S=65 ✓
- `curl /health`: status=ok ✓ (3 models active)
- 容器已重启，env 已生效
## ⏳ 轮到HM1优化HM2