# R1881 (HM2→HM1): NVU_BIG_INPUT_COOLDOWN_S 7200→21600

## 改前数据 (6h window, ~05:34–11:34 UTC)

### 请求统计
| model | total | ok | fail | SR |
|-------|-------|----|------|----|
| glm5_2_nv | 45 | 11 | 34 | 24.4% |
| dsv4p_nv | 3 | 3 | 0 | 100% |

### 失败分类
- zombie_empty_completion: 34 (100%)
- all_tiers_exhausted: 0 (5 phantom ATE with status=200)

### 输入大小分布
| input_type | total | ok | fail |
|------------|-------|----|------|
| big_input (>=115K) | 44 | 10 | 34 |
| normal | 1 | 1 | 0 |

### Tier 层
- pexec_success: 52, pexec_429: 1, pexec_SSLEOFError: 1
- NVCF tier 层健康，问题在 completion 内容层

### BIG_INPUT breaker
- 03:03 捕获 2 条 ~120K zombie → peer-fb 200 OK (verified working)
- 但 breaker 仅持续 7200s (2h)，6h 窗口内重置 3 次，每次重置后 zombie 漏入

## 根因
NVCF glm5_2 对 >115K 大输入稳定产出 zombie empty completion（finish_reason=stop 但 content 几乎为空）。NVCF tier 层本身健康（52 success, 1 429, 1 SSLEOF），问题在 completion 内容质量而非 connectivity。

## 修改
- `NVU_BIG_INPUT_COOLDOWN_S`: 7200 → 21600 (+14400s, 3x)
- 原理：7200s=2h 在 6h 窗口内重置 3 次，每次 breaker 冷却后新 zombie 漏入。21600s=6h 使 breaker 在首次触发后覆盖整个窗口，所有后续 big_input 走 peer-fb（已验证 200 OK）
- 边际：peer-fb 延迟 ~120s（NVU_PEER_FALLBACK_TIMEOUT=122），vs zombie 直接失败节省 3-16s 但无产出。peer-fb 虽慢但可交付结果

## 验证
- docker exec nv_gw env | grep BIG_INPUT → 21600 ✓
- /health → ok ✓
- docker compose up -d → nv_gw Recreated/Started ✓

## 铁律
只改HM1不改HM2 ✓
## ⏳ 轮到HM1优化HM2
