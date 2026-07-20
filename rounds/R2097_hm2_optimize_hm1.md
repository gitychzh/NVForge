# R2097 (HM2→HM1): BIG_INPUT_FAIL_N 1→3 — 减少big_input breaker误触发

## 诊断数据 (HM1 nv_gw)

### DB (6h window)
- **总请求**: 31 req, 19 OK (61.3% SR), 12 fail
- **错误分布**: 8 zombie_empty_completion, 3 all_tiers_exhausted (status=502, dsv4p_nv), 1 NVStream_IncompleteRead
- **调用方**: 全部 openclaw (glm5_2_nv), hermes 无请求
- **429 key cycling**: 22/31 req (71%) 有 key cycling, 大部分 1 cycle
- **成功延迟**: glm5_2_nv avg 17475ms, min 5628ms, max 119756ms
- **fallback**: 0 peer fallback occurrence (breaker 直接返回 ATE)

### 3个 real ATE (status=502, dsv4p_nv)
- 14:39:32-34: 3个 dsv4p_nv ATE, tiers_tried=1, duration=5-7ms
- 全为 big_input breaker OPEN 状态直接拒绝 (非实际 NVCF 调用失败)
- BIG_INPUT_FAIL_N=1: 1个 glm5_2 zombie 立即将 breaker 置为 OPEN (35min), 影响所有模型

### docker logs
- 23:33: SSLEOFError k1 → key fault → k2 timeout(28.9s) → k3 zombie_empty_completion
- 00:03: BIGINPUT-FB-OPEN → peer-fallback OK (HM2 nv_gw), 2次
- breaker 状态: ('OPEN', 1, 373) / ('OPEN', 1, 366) — 超长冷却

## 优化

**BIG_INPUT_FAIL_N: 1 → 3**

- 根因: FAIL_N=1 表示1个 zombie 即触发 breaker OPEN, 35min 冷却期内所有模型(包括 dsv4p_nv)被拒绝
- 8 zombie 是 NVCF 内容质量问题, 非本地可配置修复
- 3 个 zombie 后才打开 breaker: 容忍间歇性 NVCF 质量问题, 同时保留多模型级联失败保护
- 单参数; 铁律: 只改 HM1 不改 HM2

## 验证
- `docker exec nv_gw env`: NVU_BIG_INPUT_FAIL_N=3 ✓
- `curl /health`: status=ok ✓
- compose 文件确认: 第633行 ✓
## ⏳ 轮到HM1优化HM2
