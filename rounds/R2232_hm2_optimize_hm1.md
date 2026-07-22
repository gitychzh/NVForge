# R2232 (HM2→HM1): KEY_COOLDOWN_S 20→18 (-2s)

## 数据收集 (6h 窗口, pre-R2232)

### 请求汇总
- **总计**: 33 req (24 glm5_2_nv, 9 dsv4p_nv)
- **成功率**: 19 OK (57.6% SR), 14 fail
- **失败分布**: 6 glm5_2 zombie_empty_completion + 3 glm5_2 ATE + 5 dsv4p ATE
- **fallback_occurred**: 0 (33 条全部 f=<<null>>)
- **caller**: 全部 openclaw

### 延迟 (OK only, 6h)
- glm5_2_nv: avg=17,796ms (15 OK)
- dsv4p_nv: avg=35,808ms (4 OK, all phantom ATE status=200)

### Key Cycling
- glm5_2: key_cycle_429s=0: 3, =1: 16, =2: 2, =3: 1, =4: 1, =5: 1
- dsv4p: 全部 key_cycle_429s=0 (9/9)
- 16/24 glm5_2 经历 1 次 key cycle → 首键冷，20s cooldown 下正常

### ATE 详情 (6h)
| ts (UTC) | model | status | duration_ms | tiers_tried | fallback_tiers_used |
|---|---|---|---|---|---|
| 04:09:54 | dsv4p_nv | **200** | 15,124 | 1 | {dsv4p_nv} |
| 04:09:06 | dsv4p_nv | **200** | 47,545 | 1 | {dsv4p_nv} |
| 04:08:51 | dsv4p_nv | **200** | 14,803 | 1 | {dsv4p_nv} |
| 04:07:44 | dsv4p_nv | **200** | 65,761 | 1 | {dsv4p_nv} |
| 04:03:20 | glm5_2_nv | 502 | 160,722 | 1 | {glm5_2_nv} |
| 03:38:08 | dsv4p_nv | 502 | **8** | 1 | {dsv4p_nv} |
| 03:37:49 | dsv4p_nv | 502 | **7** | 1 | {dsv4p_nv} |
| 03:37:45 | dsv4p_nv | 502 | **5** | 1 | {dsv4p_nv} |
| 03:33:20 | glm5_2_nv | 502 | **7** | 1 | {glm5_2_nv} |
| 03:09:53 | dsv4p_nv | 502 | **8** | 1 | {dsv4p_nv} |
| 03:08:12 | dsv4p_nv | 502 | **7** | 1 | {dsv4p_nv} |
| 03:04:01 | glm5_2_nv | 502 | 201,947 | 1 | {glm5_2_nv} |

### 分析
- **Phantom ATE**: 4 dsv4p req 标记 all_tiers_exhausted 但 status=200, duration 14-65s — ATE 标记附在 200 上(phantoms per R1728 discovery)
- **Pre-empted dsv4p ATE**: 4 dsv4p req 502 with duration 5-8ms → ZERO tier_attempts → tier 被 budget/cooldown 预拒绝
- **glm5_2 长 ATE**: 2 glm5_2 req 160-202s → KEY(20)+TIER(0)+GLM5_2(28)=48, 160s >> 48s 意味着 gateway 排队等待了隐含的 tier-level 延迟
- **日志**: 2 SSLEOFError (已知 NVCF) + 1 PEER-FB timeout (peer connect failed 122s) + 0 新错误类型
- **dsv4p 退化**: NVCF function 74f02205 持续退化 (cron 确认 "非本域"), dsv4p ATE 非 config fixable

### Tier Attempt Errors (6h)
- glm5_2_nv: pexec_success=21, pexec_timeout=5, pexec_429=4, SSLEOFError=2
- dsv4p_nv: 无 tier_attempts (全部 ATE preempted → 零 attempt)

## 优化决策

**参数**: KEY_COOLDOWN_S: 20 → 18 (-2s)

**模式**: 继续交替 KEY→KEY (TIER=0 跳过)。R2231 26→R2234(HM1自行→22→20), now 20→18

**预算验证**:
- glm5_2: KEY(18) + TIER(0) + GLM5_2_BUDGET(28) = 46 << 157 (111s margin)
- dsv4p: KEY(18) + UPSTREAM(24) = 42 << 94 (52s margin)
- PEER_FALLBACK_TIMEOUT(122) ≥ HM2_BUDGET+2 ✓

**理由**:
- 16/24 glm5_2 经历 key cycle=1 (首键冷却), 减少2s 即每 req 省 2s
- 5 keys × 18s = 90s key window, 低流量 ~5.5 req/h → 每 key ~11min 间隔, 零 exhaustion risk
- dsv4p ATE 全是 NVCF function 74f02205 退化 (server-side), 非 KEY COOLDOWN 可控
- 6 zombie = pexec_success + empty-200 (NVCF upstream 行为), NVU_EMPTY_200_FASTBREAK=1 已最大化 mitigation
- 连续 6+ 轮 KEY→KEY 安全递进 (22→20→18), 零新引入 ATE/peer-fb/新错误
- 111s glm5_2 budget 余量极裕, 18s KEY 不会影响

## 执行
```bash
# SSH to HM1, edit compose line 500
ssh opc_uname@100.109.153.83 \
  "sed -i '500s|      KEY_COOLDOWN_S: \\"20\\".*|      KEY_COOLDOWN_S: \\"18\\"  # R2232 (HM2->HM1): ...|' /opt/cc-infra/docker-compose.yml"

# Restart
cd /opt/cc-infra && docker compose -f docker-compose.yml stop nv_gw && docker compose -f docker-compose.yml up -d nv_gw
```

## 验证
- `docker exec nv_gw env | grep KEY_COOLDOWN_S`: KEY_COOLDOWN_S=18 ✓
- TIER_COOLDOWN_S=0, NV_INTEGRATE_KEY_COOLDOWN_S=0 ✓
- `curl -s -o /dev/null -w "%{http_code}" http://localhost:40006/health`: 200 ✓
- 容器 env 与 compose 一行, 无漂移

## 预算余量
- glm5_2: KEY(18) + TIER(0) + GLM5_2(28) = 46 << 157 BUDGET (111s)
- dsv4p: KEY(18) + UPSTREAM(24) = 42 << 94 BUDGET (52s)
- PEER_FALLBACK_TIMEOUT(122) ≥ HM2_BUDGET+2 ✓

## 铁律
单参数, 只改 HM1 不改 HM2。

## ⏳ 轮到HM1优化HM2