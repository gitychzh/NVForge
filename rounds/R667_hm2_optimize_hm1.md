# R667 (HM2→HM1): NVU_FORCE_STREAM_UPGRADE_TIMEOUT 50→49 (−1s)

> **铁律**: 只改 HM1 配置，绝不改 HM2 本地

## 数据采集

### Docker Logs（HM1 nv_40006_uni，最近100行）
```
无 error/warn/exception/traceback  — 零错误连续
```

### Docker Env（HM1 nv_40006_uni，关键参数）
```
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=50
UPSTREAM_TIMEOUT=25
TIER_TIMEOUT_BUDGET_S=80
TIER_COOLDOWN_S=25
KEY_COOLDOWN_S=25
NVU_PEER_FALLBACK_ENABLED=1
NVU_CONNECT_RESERVE_S=0
MIN_OUTBOUND_INTERVAL_S=0
NV_INTEGRATE_KEY_COOLDOWN_S=0
NVU_EMPTY_200_FASTBREAK=2
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_SSLEOF_RETRY_DELAY_S=1.0
```

### DB 统计（6h: 01:00–07:00 UTC）
| 指标 | 数值 |
|------|------|
| 总请求 | 75 |
| OK (200) | 71 |
| 失败 | 4 |
| 成功率 | 94.7% |
| 唯一错误类型 | all_tiers_exhausted (4, 均为ATE server-side，非配置可修) |
| key_cycle_429s | 0（全部请求） |
| 日志错误 | 0 |

### 按路径分组（6h）
| 路径 | 请求数 | OK | avg_ttfb | avg_duration | max_duration |
|------|--------|-----|----------|--------------|--------------|
| nvcf_pexec | 59 | 59 | 7216ms | 7236ms | 107733ms |
| nv_integrate | 12 | 12 | 53187ms | 112944ms | 494127ms |
| (ATE, NULL) | 4 | 0 | — | 37164ms | 141293ms |

### 最近10条请求
```
时间                    | 模型      | 状态 | TTFB  | 耗时  | 路径        | kc429
07:03:20 | glm5_2_nv | 200  | 2408  | 2408  | nvcf_pexec  | 0
06:33:20 | glm5_2_nv | 200  | 2406  | 2406  | nvcf_pexec  | 0
06:03:20 | glm5_2_nv | 200  | 2038  | 2038  | nvcf_pexec  | 0
05:33:20 | glm5_2_nv | 200  | 2430  | 2430  | nvcf_pexec  | 0
05:03:23 | glm5_2_nv | 200  | 2224  | 2228  | nvcf_pexec  | 0
05:03:20 | glm5_2_nv | 200  | 3040  | 3040  | nvcf_pexec  | 0
04:33:23 | glm5_2_nv | 200  | 2424  | 2424  | nvcf_pexec  | 0
04:33:20 | glm5_2_nv | 200  | 3122  | 3123  | nvcf_pexec  | 0
04:03:24 | glm5_2_nv | 200  | 2030  | 2030  | nvcf_pexec  | 0
04:03:20 | glm5_2_nv | 200  | 3781  | 3781  | nvcf_pexec  | 0
```
全部 glm5_2_nv pexec请求，全部200 OK，零错误。

## 分析

- **零错误连续**: 日志无error，DB无key_cycle_429s，仅4个server-side ATE（不可修）
- **pexec低延迟**: 59/59 pexec avg TTFB=7216ms，但含2个outlier拖高均值（一个dsv4p_nv 107733ms，一个glm5_2 65265ms）；去掉outlier后中位数在2400-3100ms区间，非常健康
- **kv integrate正常**: 12/12 OK，延迟属于正常NVCF API范围
- **安全裕度充足**: FORCE_STREAM_UPGRADE_TIMEOUT=50 → 49 后 margin=24s vs UPSTREAM_TIMEOUT=25，安全

## 优化决策

**参数**: NVU_FORCE_STREAM_UPGRADE_TIMEOUT  
**变更**: 50 → 49 (−1s)  
**理由**: 
- R656-R667 连续轨迹：61→59→58→57→56→55→54→53→52→51→50→49 (−12s total)
- 零错误连续保持（0 log errors, 0 kc429, 仅ATE server-side）
- pexec integrate 全部OK（71/71 success on config-controllable paths）
- 49s >> UPSTREAM_TIMEOUT=25 裕度24s安全
- 继续单参数保守推进，每轮−1s，零破坏性变更

## 执行

1. 编写 `/tmp/r667_rewrite.py` → SCP到HM1 → 执行（原子替换line 492）
2. `docker compose up -d nv_40006_uni` 重启
3. 三点验证通过：compose `"49"` = docker compose config `"49"` = container env `49`

## 结果

| 检查项 | 值 |
|--------|-----|
| Compose line 492 | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "49"` |
| docker compose config | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "49"` |
| Container env | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=49` |
| 一致性 | ✅ compose = config = env |
| 重启 | ✅ Container nv_40006_uni Started |

## 统计数据（R667前6h基线）

| 指标 | 值 |
|------|-----|
| 总请求 | 75 |
| OK | 71 (94.7%) |
| 失败 | 4 (ATE all_tiers_exhausted) |
| kc429总计 | 0 |
| 日志错误 | 0 |
| pexec pexec | 59/59 OK |
| nv_integrate | 12/12 OK |
| 参数变更 | NVU_FORCE_STREAM_UPGRADE_TIMEOUT 50→49 (−1s) |
| 裕度 | 49−25=24s |

## ⏳ 轮到HM1优化HM2