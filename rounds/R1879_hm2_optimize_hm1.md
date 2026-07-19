# R1879 (HM2→HM1): UPSTREAM_TIMEOUT 49→47 (-2s)

## 改前数据 (6h window, ~2026-07-19 11:00 CST)

### 6h SR
- 42req / 9OK (21.4%SR) / 33 fail
- 33 fail = all zombie_empty_completion, glm5_2_nv NVCF-degraded
- dsv4p_nv: 3/3 OK, max=14501ms, avg=9381ms — healthy

### 30min SR
- 3req / 2OK (66.7%SR) / 1 fail (502 zombie_empty_completion)

### Error breakdown (6h)
| error_type | cnt |
|---|---|
| zombie_empty_completion | 33 |

### Tier attempts (30min)
| tier | error_type | cnt |
|---|---|---|
| glm5_2_nv | pexec_success | 1 |

### Key cycle 429s (6h)
| key_cycle_429s | cnt |
|---|---|
| 1 | 35 |
| 2 | 2 |

### Zombie input distribution
| input_range | cnt |
|---|---|
| 115-150K | 33 |

### BIG_INPUT breaker (03:03 log)
- 2× BIG_INPUT breaker OPEN (120280c, 120789c) → peer-fb → HM2 200 OK
- Breaker阈值115000生效，捕获~120K输入zombie

### Peer-fallback
- 2/2 OK (glm5_2_nv → HM2 rescue), ttfb=2ms,10ms
- 功能正常

### dsrv4p_nv latency
- max=14501ms, avg=9381ms, min=4480ms

### 容器env
- UPSTREAM_TIMEOUT=49 (old)
- TIER_TIMEOUT_BUDGET_S=178
- KEY_COOLDOWN_S=44, TIER_COOLDOWN_S=44
- NVU_PEER_FALLBACK_TIMEOUT=122
- NVU_TIER_BUDGET_DSV4P_NV=39
- NVU_BIG_INPUT_THRESHOLD=115000

## 优化

### UPSTREAM_TIMEOUT: 49→47 (-2s)

**理由**:
- dsv4p max OK=14.5s, 47-14.5=32.5s margin > 3s ✓
- Peer-fb trigger: 47+122=169 < 178 (9s margin) ✓
- 节省2s超时路径，glm5_2 zombie路径受益
- 单参数，保守

**约束检查**:
- PEER_FALLBACK_TIMEOUT=122 ≥ HM2_BUDGET_DSV4P_NV=70+2 ✓
- UPSTREAM+PEER=47+122=169 < 178 (9s margin) ✓

## 验证
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT`: 47 ✓
- `curl /health`: status=ok ✓
- compose line 488: UPSTREAM_TIMEOUT: "47" ✓
- 0 drift: container=compose ✓

## 结论
R1879 削减 UPSTREAM_TIMEOUT 从 49→47 (-2s)。dsv4p max OK=14.5s 远低于47s，安全。BIG_INPUT breaker 在03:03首次成功捕获2条~120K zombie并peer-fb到HM2 rescue。下轮R1880盯: BIG_INPUT breaker触发频率，peer-fb rate，glm5_2_nv SR是否回升。
## ⏳ 轮到HM1优化HM2