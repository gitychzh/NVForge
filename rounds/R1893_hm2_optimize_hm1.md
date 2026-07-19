# R1893 (HM2→HM1): KEY_COOLDOWN_S + TIER_COOLDOWN_S 42→60 (+18s)

## 数据采集

### 6h DB (nv_requests)
- **SR: 45.10%** (23/51) — 严重劣化
- **28 zombie_empty_completion** (all status=502, all glm5_2_nv)
- **32 key_cycle_429s** (all glm5_2_nv: 29 req at 1 cycle, 3 req at 2 cycles)
- **15 phantom ATE** (status=200, all glm5_2_nv)
- **0 docker logs errors** (clean)

### 按模型分解
| Model | Total | Avg ms | Fail |
|---|---|---|---|
| glm5_2_nv | 42 | 5854 | 26 |
| dsv4p_nv | 9 | 11400 | 2 |

### docker logs nv_gw
- 最近100行无error/warn — 无异常

### 当前配置
- KEY_COOLDOWN_S: 42 (R1890: 44→42)
- TIER_COOLDOWN_S: 42 (R1890: 44→42)
- NV_INTEGRATE_KEY_COOLDOWN_S: 0
- TIER_TIMEOUT_BUDGET_S: 178

## 根因分析

R1890将KEY_COOLDOWN_S从44→42，低于NVCF的~60s rate limit窗口。键在429冷却到期前就重新尝试，导致:
1. 键进入429 → 2. 42s后冷却到期重新尝试 → 3. NVCF的~60s窗口仍处于rate limit → 4. 再次429 → 5. 循环直到所有键耗尽 → 6. zombie_empty_completion

KEY=42不足抵御NVCF的60s窗口，32次key_cycle_429s + 28 zombie证明此判断。

## 修改

**KEY_COOLDOWN_S: 42 → 60 (+18s)**
**TIER_COOLDOWN_S: 42 → 60 (+18s)**

KEY=TIER=60 per iron law。60 ≥ NVCF 60s rate limit窗口，键在冷却到期后重新尝试时NVCF已清除rate limit。
Budget: 60+60=120 << 178 (TIER_TIMEOUT_BUDGET_S) safe。

## 部署

```bash
sed -i 's|KEY_COOLDOWN_S: "60"  # R1893.*|KEY_COOLDOWN_S: "60"  # R1893 (HM2→HM1): 42→60 (+18s). 6h 45.1%SR(23/51)/28 zombie+32 key_cycle_429s all glm5_2 NVCF rate-limit. KEY=42 below NVCF ~60s window causing rapid 429 cascade. Restore KEY=60 aligned with NVCF rate limit window. KEY=TIER=60 per iron law. 60+60=120<<178 BUDGET safe. 单参数对; 铁律:只改HM1不改HM2.|' docker-compose.yml
sed -i 's|TIER_COOLDOWN_S: "60"  # R1893.*|TIER_COOLDOWN_S: "60"  # R1893 (HM2→HM1): 42→60 (+18s). KEY=TIER=60 per iron law. 单参数对; 铁律:只改HM1不改HM2.|' docker-compose.yml
docker compose up -d nv_gw
```

## 验证
- `docker exec nv_gw env`: KEY_COOLDOWN_S=60, TIER_COOLDOWN_S=60 ✓
- 容器重启成功: nv_gw Recreated → Started

## 单参数对; 铁律:只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
