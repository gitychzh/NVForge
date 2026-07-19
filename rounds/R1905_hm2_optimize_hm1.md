# R1905 (HM2→HM1): NOP — false trigger, R1904 just deployed, insufficient post-deploy data

## 触发分析
- 检测脚本判定: "这是我提交的, 不触发" → HM2 自提交 R1904, 非 HM1 新 commit
- R1904 (UPSTREAM_TIMEOUT 32→30) 部署于 ~15:40 UTC, 当前 15:57 UTC, 仅 ~17min
- **改前必有数据 铁律触发**: 17min 无足够新数据验证 R1904 效果

## 6h 数据 (10:00-16:00 UTC, 含 R1904 前 ~5h43min)

| 指标 | 值 |
|------|------|
| 总请求 | 45 |
| 成功 | 28 (62.2% SR) |
| 失败 | 17 (100% zombie_empty_completion) |
| OK avg | 7996ms (glm5_2: 7643ms, dsv4p: 9057ms) |
| OK max | 19559ms (dsv4p_nv) |
| 0 fallback | ✓ |
| 0 peer-fb | ✓ |
| 0 ATE (non-zombie) | ✓ |

### 分模型

| 模型 | 总量 | OK | 失败 | OK avg | OK max |
|------|------|-----|------|--------|--------|
| glm5_2_nv | 36 | 21 | 15 zombie | 7643ms | 16462ms |
| dsv4p_nv | 9 | 7 | 2 zombie | 9057ms | 19559ms |

### 僵尸分析
- 17 zombie 全部 zombie_empty_completion (NVCF 返回空内容)
- 平均 input_chars: ~123K (>115K BIG_INPUT 阈值)
- 平均 zombie 持续时间: 3620ms (EMPTY_200_FASTBREAK=1 快速截断)
- BIG_INPUT 断路器: 阈值 115K, FAIL_N=1, COOLDOWN=21600s — 已覆盖
- 根因: NVCF 函数级 content-filter 返回 stop+空内容, 不可配置修复

### Tier 级错误 (6h)
- glm5_2_nv pexec_success: 26
- glm5_2_nv pexec_429: 2
- glm5_2_nv pexec_SSLEOFError: 2

## 24h 数据

| 指标 | 值 |
|------|------|
| 总请求 | 155 |
| 成功 | 109 (70.3% SR) |
| 失败 | 46 |
| 失败细分 | 39 zombie_empty_completion (glm5_2), 4 kimi ATE, 2 dsv4p zombie, 1 dsv4p ATE |

## 1h 数据 (R1904 后)

| 指标 | 值 |
|------|------|
| 总请求 | 5 |
| 成功 | 4 (80.0%) |
| 失败 | 1 zombie_empty_completion (glm5_2, 128966 chars, 3620ms) |

## 当前配置 (HM1 nv_gw)

| 参数 | 值 | 状态 |
|------|------|------|
| UPSTREAM_TIMEOUT | 30 | R1904 刚改, floor |
| TIER_TIMEOUT_BUDGET_S | 170 | R1903 刚改 |
| KEY_COOLDOWN_S | 60 | R1893 恢复, floor |
| TIER_COOLDOWN_S | 60 | R1893 恢复, floor |
| MIN_OUTBOUND_INTERVAL_S | 0 | floor |
| NVU_CONNECT_RESERVE_S | 0 | floor |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_EMPTY_200_FASTBREAK | 1 | floor |
| NVU_INTEGRATE_TIMEOUT_FASTBREAK | 1 | floor |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | R1744 |
| NVU_PEER_FB_SKIP_MODELS | kimi_nv | R1818 |
| NVU_TIER_BUDGET_DSV4P_NV | 39 | R1835 |
| NVU_TIER_BUDGET_GLM5_2_NV | 60 | R1831 |
| NVU_BIG_INPUT_THRESHOLD | 115000 | R1876 |
| NVU_BIG_INPUT_COOLDOWN_S | 21600 | R1881 |
| NVU_STREAM_FIRST_BYTE_DEADLINE_S | 15 | R1802 |
| NVU_STREAM_TOTAL_DEADLINE_S | 25 | R1742 |
| NVU_FORCE_STREAM_UPGRADE | 0 | R692 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 66 | R988 |

## 决策: NOP

**零参数修改, 零 compose 修改, 零容器重启。**

理由:
1. **False trigger** — HM2 自提交 R1904, 非 HM1 新 commit, 脚本正确识别 "不触发"
2. **改前必有数据** — R1904 仅部署 17min, 1h 仅 5 请求, 无法验证 UPSTREAM=30 效果
3. **全参数 floor/optimal** — 无进一步优化余量
4. **17 zombie 全部 NVCF empty200** — 不可配置修复, BIG_INPUT 断路器已覆盖但 function 级劣化仍穿透
5. **预算**: UPSTREAM=30 + PEER=122 = 152 < 170 (18s 余量) ✓

铁律: 只改 HM1 不改 HM2。
## ⏳ 轮到HM1优化HM2
