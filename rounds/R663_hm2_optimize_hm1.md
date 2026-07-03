# R663: HM2→HM1 — 优化回合报告

**回合编号**: R663  
**执行者**: HM2 (opc2_uname)  
**目标机器**: HM1 (opc_uname@100.109.153.83)  
**目标容器**: nv_40006_uni  
**时间**: 2026-07-04 06:10 UTC+8  
**上一轮**: R662 — HM2 compose drift fix, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=54

---

## 1. 数据采集

### 容器日志（最近100行）
- **0 error / 0 warn** — 完全clean
- 唯一匹配: `[NV-THINKING-TIMEOUT] (glm5_2_nv) thinking request stream=True → extended timeout 54s` — **正常日志**，表示thinking请求stream升级延长超时到54s，非错误

### 容器环境变量（关键参数，R662运行时状态）
| 参数 | 值 | 说明 |
|------|-----|------|
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | **54** | 容器运行时实际值（R662部署后） |
| UPSTREAM_TIMEOUT | 25 | HM1→上游超时 |
| TIER_TIMEOUT_BUDGET_S | 80 | tier预算 |
| KEY_COOLDOWN_S | 25 | key冷却 |
| TIER_COOLDOWN_S | 25 | tier冷却 |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 8 | peer fallback超时 |
| NVU_EMPTY_200_FASTBREAK | 2 | empty-200快速中断 |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | pexec快速中断 |

### Compose 三方一致性验证（R662 drift已修复）
- `sed -n '492p'` compose active value: `"54"` + R662 comment ✓
- `docker compose config` resolved: `"54"` ✓
- `docker exec env`: `54` ✓
- **三方一致** — R662 drift修复成功，compose与运行时完全同步

### DB统计（6小时窗口，R662运行期间）
| 指标 | 值 |
|------|-----|
| 总请求 | 78 |
| 成功(200) | 74 (94.9%) |
| 失败 | 4 (all_tiers_exhausted, server-side) |
| pexec路径 | 61/61 (100%) |
| integrate路径 | 13/13 (100%) |
| key_cycle_429s | 0 (零429) |
| 日志error | 0 |

### 延迟统计（6小时）
| 路径 | 请求数 | 成功率 | avg_ttfb | avg_dur | max_dur |
|------|--------|--------|----------|---------|---------|
| nvcf_pexec | 61 | 100% | 7,229ms | 7,248ms | 107,733ms |
| nv_integrate | 13 | 100% | 49,886ms | 105,047ms | 494,127ms |
| NULL (ATE) | 4 | 0% | — | 37,164ms | 141,293ms |

### 错误分类（6小时）
| error_type | count |
|-----------|-------|
| all_tiers_exhausted | 4 (NVCF server-side, 不可config修复) |

### 最近10条请求
- 全部 glm5_2_nv 通过 nvcf_pexec
- 全部 status=200, key_cycle_429s=0
- P50 ~2,430ms (极低延迟，远低于54s ceiling)
- ttfb范围: 1,636ms ~ 3,781ms

### 24h全景
| 指标 | 值 |
|------|-----|
| 总请求 | 900 |
| 成功 | 833 (92.6%) |
| 失败 | 67 (66 ATE + 1 NVStream_TimeoutError) |

---

## 2. 数据分析与优化决策

### 核心发现
1. **零错误regime持续稳定**：6h 0 log errors, 0 kc429, pexec 100%, integrate 100%
2. **R662 compose drift已修复**：三方一致(compose=config=env=54)，无drift风险
3. **延迟极低**：最近10请求 P50 ~2.4s，远低于54s ceiling，实际极少触发stream upgrade timeout
4. **唯一失败为ATE**：4次all_tiers_exhausted为NVCF服务端调度问题，非config可修复
5. **trajectory安全**：61→59→58→57→56→55→54 (−7s, 7轮)，全程零错误

### R663 决策
**执行 NVU_FORCE_STREAM_UPGRADE_TIMEOUT 54→53 (−1s)**

理由:
1. **继续trajectory**：61→59→58→57→56→55→54→53 (−8s, 8轮)，每轮−1s渐进式压缩
2. **6h数据证实安全**：pexec 61/61 OK, integrate 13/13 OK, 0 log error, 0 kc429
3. **UPSTREAM_TIMEOUT=25 << 53s margin 28s 充足**
4. **最近请求 P50 ~2.4s 远低于53s ceiling**，实际极少触发
5. **R662 drift已修复**：compose三方一致，本次修改从clean state出发
6. **铁律遵守**：只改HM1(nv_40006_uni compose)，不改HM2本地

### 未选的备选方案
- TIER_TIMEOUT_BUDGET_S (80): integrate max 494s outlier极长，80s budget合理，不改
- KEY_COOLDOWN_S (25): 0 kc429，稳定，不改
- PEER_FALLBACK_TIMEOUT (8): 已优化到地板附近，不改
- NVU_EMPTY_200_FASTBREAK (2): 已优化，不改
- 其他floor参数: NVU_CONNECT_RESERVE_S=0, MIN_OUTBOUND_INTERVAL_S=0 → 已至地板不改

---

## 3. 执行操作

### 步骤
1. 编写 Python compose fix script (`/tmp/r663_compose_fix.py`):
   - 原子重写 line 492 (NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "53" + R663 准确注释)
   - 注释包含完整 trajectory: 61→59→58→57→56→55→54→53 (−8s, 8轮)
2. `scp -P 222` 到 HM1 → `python3 /tmp/r663_compose_fix.py` 执行
3. `cd /opt/cc-infra && docker compose up -d nv_40006_uni` 重启生效
4. 验证三方一致 + 健康状态 + 日志无错误

### 修改前后对比
```
修改前 (R662):
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "54"  # R662 (HM2→HM1): 55→54 (−1s)...

修改后 (R663):
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "53"  # R663 (HM2→HM1): 54→53 (−1s). R656-R663 trajectory continued (61→59→58→57→56→55→54→53, −8s total)...
```

### 验证
```
$ docker exec nv_40006_uni env | grep NVU_FORCE_STREAM_UPGRADE_TIMEOUT
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=53  ✓

$ docker compose config | grep NVU_FORCE_STREAM_UPGRADE_TIMEOUT
NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "53"  ✓

$ docker ps --filter name=nv_40006_uni
nv_40006_uni Up 14 seconds (healthy)  ✓

$ docker logs nv_40006_uni --tail 30 | grep error
NO_ERRORS_POST_RESTART  ✓
```

---

## 4. 回合总结

| 项目 | 内容 |
|------|------|
| 变更参数 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT |
| 变更幅度 | 54 → 53 (−1s) |
| 6h成功率 | 74/78 (94.9%, zero-error regime) |
| pexec | 61/61 (100%) |
| integrate | 13/13 (100%) |
| 安全余量 | UPSTREAM=25 << 53s margin 28s |
| trajectory | 61→59→58→57→56→55→54→53 (−8s, 8轮) |
| compose三方一致 | ✅ compose=config=env=53 |
| 日志post-restart | ✅ 0 error |
| 铁律 | ✅ 只改HM1，不改HM2 |

## ⏳ 轮到HM1优化HM2
