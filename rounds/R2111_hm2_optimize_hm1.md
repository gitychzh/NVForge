# R2111 (HM2→HM1): KEY_COOLDOWN_S 75→77 (+2s)

## 数据分析 (6h window)

| Model | Requests | OK | Fail | SR |
|---|---|---|---|---|
| dsv4p_nv | 22 | 10 | 12 | 45.5% |
| glm5_2_nv | 25 | 17 | 8 | 68.0% |
| **Total** | **47** | **27** | **20** | **57.4%** |

### 错误分类

- dsv4p_nv: 12 ATE all_tiers_exhausted (NVCF pexec timeout, 5 key pool 2/5 working post-R2108)
- glm5_2_nv: 8 zombie_empty_completion (NVCF func-level degradation, 5 keys all return empty200)
- glm5_2_nv 429 rate: 77% (20/26), avg 2 key_cycle_429s

### 日志

nv_gw 启动日志干净，无运行时 error/warn。

## 优化

| Param | Old | New | Delta |
|---|---|---|---|
| KEY_COOLDOWN_S | 75 | 77 | +2s |

- **BUDGET**: KEY+TIER=77+70=147 < 153 BUDGET (6s margin safe)
- **Reasoning**: R2110 increased TIER_COOLDOWN 68→70 but 429 rate remains 77%. The 429→zombie cascade path: 429 exhausts key → immediate retry gets zombie. +2s key recovery gives NVCF rate-limit window more time to reset, reducing coupang 429→zombie conversion. 
- **dsv4p ATE**: Non-configurable NVCF pexec timeout — 3/5 keys already failed (k1,k2,k4). FASTBREAK=2 (R2108) already gives 2nd key chance. KEY_COOLDOWN doesn't affect pexec ATE.
- **Risk**: Minimal — 6s BUDGET margin, KEY_COOLDOWN only affects key re-use timing not timeout ceilings.

## 验证

```
$ docker exec nv_gw env | grep KEY_COOLDOWN_S
KEY_COOLDOWN_S=77

$ docker exec nv_gw env | grep TIER_COOLDOWN_S
TIER_COOLDOWN_S=70
```

KEY+TIER=77+70=147 < 153 ✓

## 单参数 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
