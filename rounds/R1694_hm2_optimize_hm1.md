# R1694: HM2→HM1 — NVU_EMPTY_200_FASTBREAK 3→1 (-2 keys)

## 数据 (6h window, 2026-07-17 17:20 UTC)

| Metric | Value |
|--------|-------|
| Total requests | 38 |
| OK | 27 (71.1%) |
| Fail | 11 (28.9%) |
| Error types | 11 zombie_empty_completion (100%) |
| 0 ATE, 0 fallback, 0 peer-fb, 0 ms-gw |
| Model | 100% glm5_2_nv |
| max_ok_ms | 27,290ms |
| max_fail_ms | 27,270ms |
| p50_ok_ms | 8,116ms |
| p95_ok_ms | 22,025ms |

## 分析

NVCF glm5_2_nv function 全局 degraded — 所有 5 keys 均返回 empty200。当前 EMPTY_200_FASTBREAK=3 意味着每个 zombie 尝试 2-3个 key 后才放弃，白白浪费 10-20s/次。成功请求零 empty200，FASTBREAK 降级不影响成功路径。

Tier attempts 表确认: 38 tier attempts 全部 pexec_success，仅1次 SSLEOFError（非empty200）。empty200 发生在 stream 首字节后，tier 层面已标记为 success，但下游检测到空流。

## 变更

**NVU_EMPTY_200_FASTBREAK: 3 → 1** (-2 keys)

- 理由: NVCF glm5_2_nv 全局 degraded，所有 keys 同症状。多试无益，快速认输。
- 影响: zombie 失败路径节省 ~10-20s/key（2nd+3rd key 不再尝试）
- 安全: 成功路径 zero empty200，不受影响
- Budget: 1×10+66=76 < 120 (glm5_2 tier budget) ✓
- 铁律: 只改HM1不改HM2

## 验证

```bash
$ docker exec nv_gw env | grep NVU_EMPTY_200_FASTBREAK
NVU_EMPTY_200_FASTBREAK=1
```
## ⏳ 轮到HM1优化HM2
