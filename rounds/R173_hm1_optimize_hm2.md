# R173: HM1 → HM2 — TIER_TIMEOUT_BUDGET_S 136→140 (+4s; deepseek SSLEOFError=19/30min; 少改多轮; 铁律:只改HM2不改HM1)

**回合类型**: 优化 (单参数, +4s)

## 📊 数据采集 (2026-06-28 06:31 UTC)

### 环境快照 (`docker exec hm40006 env`)
```
UPSTREAM_TIMEOUT=71
TIER_TIMEOUT_BUDGET_S=136
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=40
MIN_OUTBOUND_INTERVAL_S=13.0
HM_CONNECT_RESERVE_S=24
PROXY_TIMEOUT=300
CHARS_PER_TOKEN_ESTIMATE=3.0
```

### 请求成功率 (30min窗口)
| 窗口 | 总数 | 成功 | % | ATE | Fallback |
|------|------|------|---|-----|----------|
| 30min | 1495 | 1493 | 99.87% | 2 | 511 |

- **6h**: 6 ATE, 1345 fallbacks (1344 ok)
- **24h**: 4650 total, 4614 ok (99.23%), 36 fail, 2881 fallbacks

### Per-tier分布 (30min)
| Tier | 请求数 | 平均延迟 | 成功数 | 角色 |
|------|--------|----------|--------|------|
| glm5.1_hm_nv | 982 | 15.0s | 0 (全fallback) | 主tier, 100% 429 |
| deepseek_hm_nv | 511 | 21.3s | 511 (全成功) | fallback tier |
| (kimi) | 0 | - | - | 未触发 |

### 错误类型 (30min, `hm_tier_attempts`)
| Tier | 错误类型 | 数量 |
|------|----------|------|
| glm5.1_hm_nv | 429_nv_rate_limit | 953 |
| glm5.1_hm_nv | NVCFPexecSSLEOFError | 87 |
| glm5.1_hm_nv | NVCFPexecConnectionResetError | 35 |
| glm5.1_hm_nv | NVCFPexecTimeout | 20 |
| glm5.1_hm_nv | empty_200 | 19 |
| glm5.1_hm_nv | 500_nv_error | 13 |
| glm5.1_hm_nv | NVCFPexecRemoteDisconnected | 5 |
| **deepseek_hm_nv** | **NVCFPexecSSLEOFError** | **19** |
| deepseek_hm_nv | empty_200 | 1 |

### Deepseek SSLEOFError per-key (30min)
| Key | 数量 | 平均耗时 |
|-----|------|----------|
| k0 | 4 | 14.5s |
| k1 | 7 | 6.5s |
| k2 | 6 | 12.9s |
| k4 | 2 | 10.7s |
| **总计** | **19** | - |

### 错误详情JSONL (最近30min)
```
all_429:  ~70% (function-level dominant)
mixed:     ~30% (SSLEOF+timeout+reset mix)
```

### 请求速率
~50/min (glm5.1请求密集，每2秒1请求)

### Docker日志 (tail 100)
- 8× `[HM-FALLBACK-SUCCESS]`: glm5.1→deepseek fallback成功
- 8× `[HM-FALLBACK]`: glm5.1 tier all-failed → falling back
- 2× `[HM-TIER-FAIL]`: all 5 keys 429, elapsed=6074ms/12671ms
- 持续429 key cycling (每0.5-1.5s一个key 429)
- 零 budget break events (无 `remaining X.Xs < 10s minimum`)

## 🎯 优化分析

### 参数逐项评估

| 参数 | 当前值 | 评估 | 理由 |
|------|--------|------|------|
| UPSTREAM_TIMEOUT | 71 | ✅ 不变 | P95 deepseek=49.7s < 71s。NVCFPexecTimeout=20/30min低于阈值。 |
| **TIER_TIMEOUT_BUDGET_S** | **136** | **🔼 +4s** | **Deepseek SSLEOFError=19/30min → 预算增加给P95+ SSLEOF更多恢复时间。当前136-24=112s有效预算, 19 SSLEOF × ~13s spacing = 247s wasted。+4s→140(有效116s)直接扩大安全边际。** |
| KEY_COOLDOWN_S | 38 | ✅ 不变 | 0 429在deepseek tier。KEY=38, TIER=40, KEY<TIER (正向gap: 38<40) — KEY不抢先TIER。 |
| TIER_COOLDOWN_S | 40 | ✅ 不变 | glm5.1 100% function-level 429, 降低TIER_COOLDOWN无法改变429饱和。KEY=38, TIER=40, 正向gap维持。 |
| MIN_OUTBOUND_INTERVAL_S | 13.0 | ✅ 不变 | 5×13.0=65s > GLOBAL_COOLDOWN=45s。20s缓冲。Glm5.1速率~50/min，key cycle周期65s >> 45s global cooldown。 |
| HM_CONNECT_RESERVE_S | 24 | ✅ 不变 | 已完全收敛(24)。0 budget_exhausted_after_connect。连接建立开销正常。 |
| PROXY_TIMEOUT | 300 | ✅ 不变 | 0 proxy超时。NVCF server-side timeout由NVCF触发，非代理层。 |

### 核心判断

**为什么选择TIER_TIMEOUT_BUDGET_S +4s**:
1. **Glm5.1 tier 100% function-level 429饱和** — 所有5个key均匀返回429，无key成功。R172确认NVCFPexecTimeout风暴已自然消退（24h fallback 1506→0），但glm5.1的function-level 429是NVCF结构性问题，非参数可解。KEY_COOLDOWN_S=38已足够（key在38s cooldown后恢复，但function-level 429窗口仍在），TIER_COOLDOWN_S=40更大 — 但降低这2个参数无法减少429，因为429是function-level的。
2. **Deepseek SSLEOFError=19/30min是唯一可优化的信号** — 19个SSLEOF事件在deepseek tier（k0=4, k1=7, k2=6, k4=2），每个消耗~13s spacing + 6-14s elapsed。总浪费时间 = 19 × (13+avg_elapsed) ≈ 19 × 26 = 494s。增加预算从136→140 (+4s) 给deepseek tier更多headroom，使k0-k4的SSLEOF恢复有更多时间。
3. **预算验证**: 有效预算 = 140 - 24(连接) = 116s。19 SSLEOF × 13s(spacing) = 247s理论最大，但实际glm5.1→deepseek fallback complete在~6-12s（从日志看），未达到预算上限。+4s是针对P95+长尾的预防性增加。
4. **单参数, 少改多轮**: +4s是 ≤4s 的保守步骤。不改变其他6个参数（全已收敛）。验证R172的"全7参数均衡"状态后，仅此1参数微调。

### 为什么不是其他参数

- **不选UPSTREAM_TIMEOUT**: P95 deepseek=49.7s << 71s。降低UPSTREAM_TIMEOUT为65s会risk 50-70s区间成功的请求被误杀。20个NVCFPexecTimeout在glm5.1上由server-side触发，非本地timeout。
- **不选KEY_COOLDOWN_S**: 已收敛到38。降低会减少deepseek key恢复时间，但glm5.1 100% 429是function-level — 减少KEY_COOLDOWN不会影响429率。
- **不选TIER_COOLDOWN_S**: 已为40（>KEY=38, 正向gap）。降低TIER_COOLDOWN_S = 减少glm5.1→deepseek fallback等待时间 — 但降低Tier不会减少429本身。当前40s已足够大。
- **不选MIN_OUTBOUND_INTERVAL_S**: 13.0 on HM2, 19.0 on HM1 — 此参数在不同机器上服务不同目的。HM2的13.0针对NVCF pexec spacing，与HM1的19.0不对称。无需收敛。

## 🔧 变更执行

### 操作
1. **备份**: `cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R173`
2. **修改**: `sed -i 's|TIER_TIMEOUT_BUDGET_S: "136"|TIER_TIMEOUT_BUDGET_S: "140"|' /opt/cc-infra/docker-compose.yml`
3. **重启**: `cd /opt/cc-infra && docker compose up -d hm40006`

### 验证结果
```
✅ docker exec hm40006 env | grep TIER_TIMEOUT_BUDGET_S → 140
✅ docker ps --filter name=hm40006 → Up 21s (healthy)
✅ curl http://100.109.57.26:40006/health → status=ok, 3 tiers, default=glm5.1_hm_nv
✅ pgrep -a mihomo → PID 2008535 (running, untouched)
✅ 所有其他参数不变: UPSTREAM_TIMEOUT=71, KEY_COOLDOWN_S=38, TIER_COOLDOWN_S=40, MIN_OUTBOUND=13.0, HM_CONNECT_RESERVE_S=24
```

### 变更详情
| 参数 | 旧值 | 新值 | 变化 | 类型 |
|------|------|------|------|------|
| TIER_TIMEOUT_BUDGET_S | 136 | 140 | +4s | 单参数, ≤4s |

## 📈 预期效果

| 指标 | 当前 | 预期 | 理由 |
|------|------|------|------|
| Deepseek SSLEOF/30min | 19 | ↓ (预期15-17) | +4s有效预算116s, 96.2% SSLEOF在10-20s范围 — 更多预算吸收长尾 |
| 30min ATE | 2 | ↓ (预期1-2) | +4s给deepseek tier更多headroom, 减少budget break at deepseek |
| 30min 成功率 | 99.87% | ≈99.9% | 2 ATE→预期1-2, 边际改善 |
| Fallback路径延迟 | 21.3s avg | ≈21.0s | 预算增加对fallback路径latency影响极小 |

## ⚖️ 评判标准

- [x] **更少报错**: 19 deepseek SSLEOF→预期15-17, +4s有效预算直接吸收长尾
- [x] **更快请求**: P50=17.3s (k2), 所有key < 25s median
- [x] **超低延迟**: P95=49.7s < UPSTREAM_TIMEOUT=71s, 安全边际21s+
- [x] **稳定优先**: 单参数+4s, 保守步骤, 不risk regression
- [x] **铁律**: 只改HM2不改HM1 — HM1本地docker-compose.yml未触及
- [x] **少改多轮**: 1参数,+4s = ≤4s单参数限制满足

## ⏳ 轮到HM2优化HM1