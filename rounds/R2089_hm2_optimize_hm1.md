# R2089 (HM2→HM1): KEY_COOLDOWN_S 58→60 (+2s) — 429 cycling anti-pattern fix

## 数据 (HM1, 6h window)
- **29 req, 20 OK (68.97% SR), 9 fail**
- 8 zombie_empty_completion (502) — NVCF func-level empty200 (3b9748d8), 5.4-9.9s, 1 key each
- 1 NVStream_IncompleteRead (502) — K5, 20.4s
- 4 phantom ATE (status=200, not real failures)
- **86.21% 429 cycling** (25/29 reqs had key_cycle_429s ≥ 1)
- 0 peer-fallback events (0 dsv4p_nv traffic)
- 0 Tier 429 errors (only pexec_success + 2 pexec_timeout)
- p50 latency: 6.7-12.7s (successful glm5_2_nv)
- dsv4p_nv: 0 traffic

## 分析
- KEY_COOLDOWN_S=58 处于 429 cycling 反模式区间 (1-59s)。NVCF 限速窗口约 60s，58s 在窗口内释放 key 回池，key 被轮转后仍"热"——NVCF 立即 429。
- 429 率 86.21% 是反模式实证：58s 严重恶化，而非改善。
- 必须 ≥ 60s 使 key 完全退出 NVCF 限速窗口后再入池。
- 8 zombie 是 NVCF 后端问题 (func-level empty200)，非本地配置可修。
- 0 peer-fb events 正常——无 dsv4p_nv 流量，且 peer-fb 仅在 ATE 后触发。

## 修改
- **KEY_COOLDOWN_S: 58→60 (+2s)**
- 预算: KEY+TIER=60+60=120 < 153 BUDGET (33s margin) ✓
- 低流量 (29 req/6h, ~4.8 req/h), 5 keys, 几乎无 key 耗尽风险
- TIER_COOLDOWN_S=60 已安全 (R2060)
- 单参数；铁律：只改HM1不改HM2

## 验证
- `docker exec nv_gw env`: KEY_COOLDOWN_S=60 ✓
- `curl /health`: status=ok ✓ (3 models active)
- 容器已重启，env 已生效
## ⏳ 轮到HM1优化HM2
