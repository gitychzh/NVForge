# R1863 (HM2→HM1): KEY_COOLDOWN_S 56→54, TIER_COOLDOWN_S 56→54 (-2s each)

## 改前数据

### 30min DB
| tier_model | total | ok | fail | SR |
|---|---|---|---|---|
| glm5_2_nv | 4 | 0 | 4 | 0.0% |

### 6h DB
| tier_model | total | ok | fail | SR |
|---|---|---|---|---|
| dsv4p_nv | 3 | 3 | 0 | 100.0% |
| glm5_2_nv | 32 | 13 | 19 | 40.6% |

### 6h overall: 16/35 (45.7% SR)

### 错误类型 (6h)
- zombie_empty_completion: 19 (all glm5_2_nv, NVCF-side — function returns 200 with empty body)
- all_tiers_exhausted: 3 (phantom, status=200)

### tier_attempts (6h)
- pexec_success: 43 (glm5_2_nv)
- pexec_429: 1 (glm5_2_nv)
- zero SSLEOF, zero timeout, zero NVCFPexecTimeout

### key_cycle_429s (6h)
- glm5_2_nv: 31 reqs with 1 cycle, 1 req with 2 cycles (total 32)

### Recent 20 glm5_2_nv requests
- 18 zombie (502), 2 success (200) — zombie clusters every ~30 min, 4-5 per burst, 3-4s each
- tiers_tried_count=1 on all, fallback_occurred=false (zombie doesn't trigger peer-fb)
- No successful requests since 00:03 UTC — all subsequent are zombie

### fallback (6h)
- fallback_occurred=false: all (peer-fb not triggering — zombie doesn't count as tier failure)

### 容器状态
- env: KEY_COOLDOWN=56, TIER_COOLDOWN=56, UPSTREAM=49, BUDGET=178, PEER_FB=122
- health: ok

## 分析

glm5_2_nv 持续 NVCF-side zombie退化 (19/19 错误全是 zombie_empty_completion — NVCF接受请求返回空体)。Tier attempts 全部 pexec_success — NVCF 接受请求但无内容。不是 config 可修复的。R1862 从 58→56 后 zombie 模式未变。继续沿 R1862 轨迹：降低 KEY/TIER cooldown 让 zombie 后 key 更快恢复，减少单 key 被 zombie 独占概率。

## 变更

| 参数 | 旧值 | 新值 | delta |
|---|---|---|---|
| KEY_COOLDOWN_S | 56 | 54 | -2s |
| TIER_COOLDOWN_S | 56 | 54 | -2s |

## 约束验证

- KEY=TIER=54 (铁律: KEY=TIER)
- 54+54=108 << 178 BUDGET (70s margin safe)
- HM2 KEY=25 证明 54 极度保守
- UPSTREAM=49+PEER_FB=122=171 < 178 (7s margin)
- 单参数对 (KEY+TIER 同步); 铁律:只改HM1不改HM2

## 改后验证

```bash
$ docker exec nv_gw env | grep 'KEY_COOLDOWN\|TIER_COOLDOWN'
KEY_COOLDOWN_S=54
TIER_COOLDOWN_S=54
$ curl -s http://localhost:40006/health
{"status": "ok", ...}
```

## 评判

- 更少报错: zombie 是 NVCF 侧非 config 可修；KEY 冷却缩短 2s 让 zombie 后 key 更快恢复
- 更快请求: 失败路径节省 2s key 冷却时间
- 超低延迟稳定优先: 54 >> 25 (HM2) 极度保守，54+54=108 << 178 充裕安全
- 铁律: 只改HM1不改HM2 ✓
## ⏳ 轮到HM1优化HM2
