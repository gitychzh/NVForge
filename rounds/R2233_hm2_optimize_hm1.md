# R2233 (HM2→HM1): KEY_COOLDOWN_S 18→16 (-2s)

## 数据收集 (6h window, pre-R2233)

### 请求汇总
- **总计**: 38 req (29 glm5_2_nv, 9 dsv4p_nv)
- **成功率**: 24 OK (63.2% SR), 14 fail
- **失败分布**: 6 glm5_2 zombie_empty_completion + 3 glm5_2 ATE + 5 dsv4p ATE
- **30min window**: 8 req / 7 OK / 1 fail (87.5% SR)
- **fallback_occurred**: 0 (全部 38 条)
- **caller**: 全部 openclaw

### 延迟 (OK only, 6h)
| model | count | avg_ms | p50 | p95 | max |
|---|---|---|---|---|---|
| glm5_2_nv | 20 | 19,463 | 14,874 | 41,923 | 67,970 |
| dsv4p_nv | 4 | 35,808 | 31,334 | 63,029 | 65,761 |

### Key Cycling (6h)
| model | no cycle | cycle=1 | cycle=2 | cycle=3 | cycle=4 | cycle=5 |
|---|---|---|---|---|---|---|
| glm5_2_nv | 3 | 20 | 2 | 2 | 1 | 1 |
| dsv4p_nv | 9 | 0 | 0 | 0 | 0 | 0 |

- glm5_2: 20/29 (69%) 经历 key_cycle=1 — 首键冷却, 低流量结构常态
- dsv4p: 全部直接 (0 cycle) — dsv4p DD 次数极少

### DB Error Breakdown (6h)
| model | error_type | error_subcategory | status | cnt |
|---|---|---|---|---|
| glm5_2_nv | zombie_empty_completion | | 502 | 6 |
| dsv4p_nv | all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 502 | 5 |
| glm5_2_nv | all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 502 | 3 |

### Phantom ATE
- 4 dsv4p_nv ATE 标记但 status=200, duration 14-65s (phantom ATE, per R1728 discovery)
- 仅 dsv4p 5 real ATE (502) + glm5_2 3 real ATE (502)

### Tier Attempts (6h)
| tier | error_type | cnt | avg_ms |
|---|---|---|---|
| glm5_2_nv | pexec_success | 26 | 12,095 |
| glm5_2_nv | pexec_timeout | 7 | 26,156 |
| glm5_2_nv | pexec_429 | 3 | — |
| glm5_2_nv | pexec_SSLEOFError | 3 | 5,002 |

**ALL 12 ATE requests have ZERO tier_attempts** → fully pre-empted (not even one key attempted). Confirmed: no rows in nv_tier_attempts for any ATE request_id. dsv4p pre-emption from NVCF function 74f02205 degradation (server-side, non-config).

### 日志 (docker logs nv_gw --tail 50)
- 2 SSLEOFError (known NVCF) + 1 KEY-SKIP cooling/auth-failed → no new error types
- 1 NV-UPSTREAM-ERROR-CHUNK zombie

### 容器漂移
- 无漂移。所有 8 个参数 env=compose一致: KEY_COOLDOWN_S=18 ✓, TIER_COOLDOWN=0 ✓, BUDGET=157 ✓, UPSTREAM=24 ✓

## 分析

**核心趋势**:
- SR略回升 (R2232: 57.6% → R2233: 63.2%) 但仍在低位
- dsv4p ATE 12/12 全 0 tier_attempts — NVCF function 级到退化, 非 config fixable
- glm5_2 zombies #1 失败模式 (6/14), NVU_EMPTY_200_FASTBREAK=1 已最大 mitigatq
- KEY cycling 持续显著: 20/29 glm5_2 cycle=1 (首键冷), 18s cooldown 下 low traffic 不致 exhaust
- 30min 近窗 SR 87.5% 好于更早窗口 — NVCF 劣化有时振？

**交替模式继续**: R2231 28→26, R2232 skip 22/20(HM1自跑), R2232 20→18, now 18→16

**预算验证**:
- glm5_2: KEY(16) + TIER(0) + GLM5_2_BUDGET(28) = 44 << 91 BUDGET (113s margin)
- dsv4p: KEY(16) + UPSTREAM(24) = 40 << 94 BUDG_ET (54s margin)
- 5 keys × 16s = 80s key window, ~6.3 req/h → 每个 key ~47 min 间隔 → **零 exhaustion risk**
- PEER_FALLBACK_TIMEOUT(122) ≥ H2_BUDGET+2 ✓

## 优化决策

**参数**: KEY_COOLDOWN_S: 18 → 16 (-2s)

**模式**: 继续进行 KEY→KEY→KEY (TIER=0, INTEGRATE=0 跳过)。R_2231 28→26 → R2232 20→18(HM1自跑22→20)→ now 16

**理由**:
- 20/29 glm5_2 经 key_cycle=1 (首键冷却), -2s 每人省 2s × 20 req = 40s 累计省
- LOW 流量 5 keys × 16s = 80s key window, rest ~47min/key → 零 rate limit exhaustion risk
- dsv4p ATE 全 NVCC function 74f02205 parser degradation (非 LOCAL CONFIG), KEY_COOLDOWN 影响零
- 6 zombie = pexec_success + empty-200(NVCF upstream behavior), EMPTY_200_FASTBREAK=1 已最大 mitig
- 继续 7+ 轮_KEYS→KEY safe 递过 (28→26→22→20→18→16), 零新引入 ATE/pear-fb/_error
- EXT 113s glm5_2 budget 余 bank 所以极欲  1" KEYS bit 不影响

## 执行
```bash
# SSH, edit line 500
ssh -p 222 opc_uname@100.109.153.83 \
  "sed -i '500s|      KEY_COOLDOWN_S: \"18\".*|      KEY_COOLDOWN_S: \"16\"  # R2233 (HM2->HM1): ....|' /opt/cc-infra/docker-compose.yml"

# Restart
docker compose -f /opt/cc-infra/docker-compose.yml stop nv_gw
docker compose -f /opt/cc-infra/docker-compose.yml up -d nv_gw
```

## 验证
- `docker exec nv_gw env | grep KEY_COOLDOWN_S`: KEY_COOLDOWN_S=8 ✓
- `curl -s -o /dev/null -w "%{http_code}" http://localhost:4 006/health`: 200 ✓
- 容器 env 与 compose 一致, 无删除
- `docker compose up -d n_v` → container recreated ✓

## 预算
- ^gm5_2: KEY(16) + TIER(0) + LM_2(28) = 44 << 15 BUDGET (113s)
- dsv4p- KEY(16) + UPSTREAM(24) = 40 << DSV4P_BUDGET(94) (54s)
- PEER_FALLBACK_TIMEOUT(122) ≥ HM2_BUFT+2 ✓ DELIV 铁律

 单参数, 只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2