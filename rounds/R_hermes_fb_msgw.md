# R-hermes-fb-msgw: hermes adapter fallback 从 nv_gw(glm5_2_nv) 切到 ms_gw(glm5_2_ms)

## 时间
2026-08-03 23:10 (CST)

## 问题
HM2 hermes agent 报 "primary 和 fallback 均不可用, 请稍后重试"。

## 根因分析 (改前数据, 2h 窗口 14:00-15:00 CST)

hermes → hm4104(4104) → primary: dsv4p_nv40066(40066) → NVCF pexec (5 keys)
                      → fallback: nv_gw(40006) → glm5_2_nv → NVCF pexec/integrate (同 5 keys)

**核心: primary 和 fallback 共用同一组 5 个 NVCF API key, 无独立故障域。**

| 路径 | 总请求 | 成功 | 失败 | SR | 主要错误 |
|---|---|---|---|---|---|
| dsv4p_nv (primary) | 370 | 333 | 37 | 90% | zombie_empty_completion(18), all_tiers_exhausted(12), 429(1) |
| glm5_2_nv (fallback) | 276 | 169 | 107 | **61%** | **zombie_empty_completion(86)**, buffer_exhausted(14) |

三层叠加:
1. NVCF 429 风暴 (primary): 5 key 全 429 → all_tiers_exhausted, 冷却最高 600s
2. glm5_2_nv zombie 大流行 (fallback): NVCF 返回有 finish_reason 但内容为空, 2h 内 86 次
3. 无独立故障域: fallback 和 primary 用同一组 NVCF key, 一坏全坏
4. adapter 熔断器放大: primary 连续 8 次失败 → circuit OPEN → 100% 涌入本已不健康的 fallback

## 修改

### 1. hm4104 FALLBACK 从 nv_gw → ms_gw (独立故障域)
`/opt/cc-infra/docker-compose.yml` hm4104 section:
- `FALLBACK_URL`: `http://nv_gw:40006/v1` → `http://ms_gw:40007/v1`
- `FALLBACK_MODEL`: `glm5_2_nv` → `glm5_2_ms`
- `MS_GW_API_KEY`: `nv-gw-token` → `ms-gw-token`

ms_gw (ModelScope) 是完全独立的上游, 不走 NVCF API, 不受 NVCF 429/zombie 影响。
刚测 ms_gw 响应正常 (0.99s)。

### 2. dsv4p_nv40066 + nv_gw_stable: 429 最高冷却 600s → 300s
- `NVU_KEYMGR_429_MAX_COOLDOWN`: 600 → 300
- 避免 429 全 key 长时间死锁 (600s = 10min 全死)

## 验证 (改后)
- hm4104 health: `fallback_url: http://ms_gw:40007/v1, fallback_model: glm5_2_ms` ✓
- dsv4p_nv40066 health: ok ✓
- E2E primary (dsv4p_nv): 200, 28.5s ✓
- E2E fallback (ms_gw/glm5_2_ms): 200, 0.99s ✓
- hm4104 日志: primary zombie → 切 ms_gw fallback → 成功 (无 FALLBACK-FAIL-STREAM) ✓
- hermes service: 无 "均不可用" 或 "empty stream" 报错 ✓
- 改后 5min 内 hermes caller 全部 200 (1 个 IncompleteRead 非致命) ✓

## 回滚
```bash
# hm4104 fallback 改回 nv_gw
# docker-compose.yml hm4104 section:
#   FALLBACK_URL=http://nv_gw:40006/v1
#   FALLBACK_MODEL=glm5_2_nv
#   MS_GW_API_KEY=nv-gw-token
# dsv4p_nv40066:
#   NVU_KEYMGR_429_MAX_COOLDOWN=600
cd /opt/cc-infra && docker compose up -d hm4104 dsv4p_nv40066
```

## 备注
- NVCF zombie_empty_completion 是 NVCF 侧 glm5.2 模型故障, 非本地配置问题
- ms_gw 作为 fallback 是 hermes 的兜底, 不是日常路径; 日常仍走 dsv4p_nv primary
- cc4101 和 opclaw4103 不受此修改影响 (各自有独立的 fallback 配置)
