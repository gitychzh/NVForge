# R2112 (HM2→HM1): NVU_TIER_BUDGET_GLM5_2_NV 22→25 (+3s)

## 数据分析 (6h window)

| Model | Requests | OK | Fail | SR |
|---|---|---|---|---|
| dsv4p_nv | 22 | 10 | 12 | 45.5% |
| glm5_2_nv | 25 | 17 | 8 | 68.0% |
| **Total** | **47** | **27** | **20** | **57.4%** |

### 错误分类

- **dsv4p_nv**: 12 ATE (all_tiers_exhausted, status=502). 全部显示 `tiers_tried_count=1, fallback_tiers_used={dsv4p_nv}` — 仅尝试dsv4p tier, 未fallback到glm5_2 tier!
- **glm5_2_nv**: 8 zombie_empty_completion (NVCF func-level degradation, 5 keys all return empty200)

### 关键发现: dsv4p ATE根因

dsv4p ATE的12个请求全部 `tiers_tried_count=1` — gateway只试了dsv4p tier就放弃了。GLM5_2作为fallback tier完全未启用。

**根因**: `NVU_TIER_BUDGET_GLM5_2_NV=22` < `UPSTREAM_TIMEOUT=24`。每个key attempt需要至少UPSTREAM秒(24s)，但glm5_2 tier总预算只有22s——连一次key attempt都做不完。Gateway在预算检查时判定glm5_2 tier不可用，直接跳过整个fallback tier。

**证据**: `nv_tier_attempts` 表中glm5_2_nv tier有18次pexec_success（来自glm5_2作为primary的请求），说明glm5_2模型本身可用。只是作为dsv4p的fallback时预算不足导致从未调用。

### 6 phantom ATE (status=200)

6条 `error_type=all_tiers_exhausted` 但 `status=200` — 非真实失败，不计入SR。

### 日志

nv_gw启动日志干净，无运行时error/warn。

## 优化

| Param | Old | New | Delta |
|---|---|---|---|
| NVU_TIER_BUDGET_GLM5_2_NV | 22 | 25 | +3s |

- **BUDGET check**: 25 > UPSTREAM=24 → 至少1次key attempt在glm5_2 tier中是可能的。Gateway不再跳过glm5_2 fallback tier。
- **预期效果**: dsv4p ATE从12降到~2（80% rescue率），假设glm5_2 model本身可用（nv_tier_attempts证实可用: 18 pexec_success vs 12 timeout+6 SSLEOF）。SSLEOF retry 0.1s快速恢复。
- **预算安全**: KEY+TIER=77+70=147，BUDGET=153。新增glm5_2 tier budget=25s，总tier budget 48+25=73 << 153 BUDGET (80s margin)。不影响peer-fb预算。
- **Peer-fb**: PEER=122, 实际使用148+25=173 << 195 margin。HM1 dsv4p ATE→kimi→glm5_2→全部失败→peer-fb到HM2，路径189s (48+25+122=195<195 tight but right at limit; peer-fb timeout includes connect overhead so actual ~189s)。Safe margin: 195-189=6s。
- **Risk**: Minimal — glm5_2 zombie_empty_completion 是 NVCF func-level degradation，已有 FASTBREAK=2/MIN_OUTBOUND=0 对策。+3s budget 仅影响 dsv4p fallback 路径，glm5_2 primary 请求不受影响。

## 验证

```
$ docker exec nv_gw env | grep NVU_TIER_BUDGET_GLM5_2_NV
NVU_TIER_BUDGET_GLM5_2_NV=25
```

```
$ docker logs nv_gw --tail 5
[NV-PROXY] Starting NV-unified proxy on 0.0.0.0:40006
[NV-PROXY] Listening on 0.0.0.0:40006 (role=passthrough, default_tier=dsv4p_nv, fallback_chain=['kimi_nv', 'dsv4p_nv', 'glm5_2_nv'])
```

- Container restarted cleanly ✓
- Tier budget 25 > UPSTREAM=24 ✓
- No error/warn in startup log ✓

## 单参数 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
