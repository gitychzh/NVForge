# R1851 (HM2→HM1): NOP — 全 zombie_empty_completion, NVCF content-filter 非 config 可修

## 改前数据 (6h window, HM1 DB, 2026-07-19 07:30 UTC)

```
SR: 33/42 = 78.6% (200:33 / 502:9)
```

### 502 分类 (9条)
| error_type | count | 分析 |
|---|---|---|
| zombie_empty_completion | 9 | NVCF content-filter 行为, glm5_2_nv, content_chars=12, reasoning_chars=0, 非 config-fixable |

### 模型维度
| mapped_model | total | ok | fail | avg_ms | max_ms |
|---|---|---|---|---|---|
| glm5_2_nv | 28 | 19 | 9 | 6958 | 14181 |
| dsv4p_nv | 14 | 14 | 0 | 14718 | 40603 |

### 关键观察
- 全部9条502 = zombie_empty_completion (glm5_2_nv): NVCF content-filter 返回空 completion, R852b zombie 检测在 2.3-4.2s 内 abort, 触发 cc4101 retry
- zombie 全为大输入请求 (total_input_chars 115726-118105, 均 >= 5000), 非小输入误判
- dsv4p_nv 14/14 OK, 但 3条 phantom ATE (all_tiers_exhausted + status=200) — 已 rescue, 非问题
- 0 fallback 触发, 0 breaker OPEN, 0 新错误分类
- 容器 StartedAt 维持 2026-07-18T21:26:29Z (R1839 改后字节码, 无 restart)
- 日志显示: NV-GLM52-SUCCESS 后紧跟 NV-ZOMBIE-EMPTY → NV-UPSTREAM-ERROR-CHUNK, 5 keys 轮转均触发, 模式稳定

### env 无漂移
```
UPSTREAM_TIMEOUT=51 (R1839)
TIER_TIMEOUT_BUDGET_S=178 (R1840)
KEY_COOLDOWN_S=60 (R1833)
TIER_COOLDOWN_S=60 (R1833)
NVU_TIER_BUDGET_DSV4P_NV=39 (R1835)
NVU_TIER_BUDGET_GLM5_2_NV=60 (R1831)
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEER_FALLBACK_TIMEOUT=122
NVU_MS_GW_FALLBACK_TIMEOUT=120
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
```
全与 R1843/R1845/R1846/R1850 NOP 轮一致, 无漂移.

## 决策: NOP — 不改

- 全部 502 为 zombie_empty_completion: NVCF 侧 content-filter 行为, 非 HM1 任何 config 参数可修
- dsv4p_nv 高延迟: NVCF 侧, 非 config 可修
- 无新错误分类, 无 fallback 恶化, 无 breaker OPEN
- 硬改违反铁律: 改前必有数据, 聚焦 nv_gw
- 0 restart 0 中断
- R1842-R1851 连续10轮 zombie 主导, SR 在 94-98% 区间抖动 (HM1 侧 sync 前), 非系统退化

## 评判: 更少报错更快请求超低延迟稳定优先
- 9 条 zombie NVCF 非可控 → 不触发介入
- 链路稳, 无 config 可改依据 → NOP
- 铁律: 改前必有数据 → 0 改
## ⏳ 轮到HM1优化HM2
