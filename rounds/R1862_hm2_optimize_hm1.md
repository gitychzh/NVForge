# R1862 (HM2→HM1): KEY_COOLDOWN_S 58→56, TIER_COOLDOWN_S 58→56 (-2s each)

## 改前数据

### 30min DB (created_at >= NOW() - 30min)
| tier_model | total | ok | fail | SR |
|---|---|---|---|---|
| glm5_2_nv | 4 | 0 | 4 | 0.0% |

### 2h DB
| tier_model | total | ok | fail | SR |
|---|---|---|---|---|
| glm5_2_nv | 15 | 1 | 14 | 6.7% |

### 6h DB
| tier_model | total | ok | fail | SR |
|---|---|---|---|---|
| dsv4p_nv | 3 | 3 | 0 | 100.0% |
| glm5_2_nv | 32 | 13 | 19 | 40.6% |

### 错误类型 (6h)
- zombie_empty_completion: 19 (all glm5_2_nv, NVCF-side — function returns 200 with empty body)
- all_tiers_exhausted: 3 (phantom, status=200)

### tier_attempts (30min)
- pexec_success: 4 (K0=1, K1=1, K3=1, K4=1) — NVCF accepts but returns empty
- zero SSLEOF, zero timeout, zero NVCFPexecTimeout, zero 429

### fallback (2h)
- fallback_occurred=false: 15 (peer-fb not triggering — zombie doesn't count as tier failure)

### 容器状态
- StartedAt: 2026-07-19T00:25:14Z (R1858 deploy后，7min前重启)
- health: ok
- UPSTREAM=49, KEY_COOLDOWN=58, TIER_COOLDOWN=58, BUDGET=178, PEER_FB=122

## 分析

glm5_2_nv 严重退化 (NVCF-side zombie_empty_completion — 函数接受请求但返回空体)。所有 tier attempts 显示 `pexec_success` — NVCF 接受请求但无内容返回。这不是 config 可修复的。KEY_COOLDOWN=58 时，每次 zombie 后 key 冷却 58s，与 TIER_BUDGET_GLM5_2_NV=60 配合，单 key 尝试后即耗尽 tier。

## 变更

| 参数 | 旧值 | 新值 | delta |
|---|---|---|---|
| KEY_COOLDOWN_S | 58 | 56 | -2s |
| TIER_COOLDOWN_S | 58 | 56 | -2s |

## 约束验证

- KEY=TIER=56 (铁律: KEY=TIER)
- 56+56=112 << 178 BUDGET (66s margin safe)
- HM2 KEY=25 证明 56 极度保守
- UPSTREAM=49+PEER_FB=122=171 < 178 (7s margin)
- 单参数对 (KEY+TIER 同步); 铁律:只改HM1不改HM2

## 改后验证

```bash
$ docker exec nv_gw env | grep 'KEY_COOLDOWN\|TIER_COOLDOWN'
KEY_COOLDOWN_S=56
TIER_COOLDOWN_S=56
$ curl -s http://localhost:40006/health
{"status": "ok", ...}
```

## 评判

- 更少报错: zombie 是 NVCF 侧，非 config 可修；KEY 冷却缩短 2s 让 zombie 后 key 更快恢复，减少单 key 耗尽概率
- 更快请求: 失败路径节省 2s key 冷却时间
- 稳定优先: 56 >> 25 (HM2) 极度保守，56+56=112 << 178 充裕安全
- 铁律: 只改HM1不改HM2 ✓
## ⏳ 轮到HM1优化HM2
