# R909 — cc2 NOP 巡检轮 (主链连续第 18 轮 100% 干净)

> 时间: 2026-08-07 ~09:20 CST (live DB now()≈2026-08-07 09:14)
> 类型: NOP (不改码)。cc2 主链路持续 100% 干净, 无新错误类。

## 结论
- **cc2 主链 (cc4101-primary/dsv4f0731_nv): 127/127 = 100% SR, 0 bad。**
- 30min 所有 bad 请求 (3 条) 100% 属 `caller=hermes` (2 × all_tiers_exhausted + 1 × stream_absolute_cap, 均为 502)。
  JOIN 铁证未进 cc2 主链候选池。
- buffer 全 attempt=1/5 成交 (7-11s success_tool_call), 0 重试 / 0 429 / 0 cooldown。
- fallback (cc2 线) 0 次。

## 数据 (实拉 30min window, 2026-08-07 09:14)

### 30min cc4101-primary (cc2 主链)
| status | count |
|---|---|
| 200 | 127 |
| !=200 | **0** |

### 30min 所有 bad (status!=200) — caller 归属
| caller | error_type | status | count |
|---|---|---|---|
| hermes | all_tiers_exhausted | 502 | 2 |
| hermes | stream_absolute_cap | 502 | 1 |

→ cc2 主链 0 bad。bad 100% hermes 越界。

### 30min nv_tier_attempts per-key 健康
- 5 key 全走健康 fid (dsv4f0731_nv), error_type=pexec_success 25-26×/key。
- 零星瞬时 RemoteDisconnected/empty_200/NVCFPexecTimeout 1-5× → 被 multi-tier round-robin + func_health 吸收, 未影响 SR。
- 无 52e1ddb6 泄漏。

### 30min buffer/wait/keymanager
```
NV-BUFFER-START  dsv4f0731_nv max_retries=5 stairs=[90×5] ping=30s total_deadline=450s
NV-BUFFER-ATTEMPT attempt=1/5  → NV-BUFFER-VERDICT success_tool_call 7-11s → NV-BUFFER-SUCCESS
```
全 attempt=1/5 成交, 0 重试 / 0 429 / 0 cooldown。

### fallback 发生率: 0 次 (cc2 线)

## 判断
cc2 主链路连续第 18 轮 (R892-R909) 100% SR 干净。bad 请求 100% 属 hermes, JOIN 铁证未进 cc2 主链。
**不改码**: ①主链 SR 100% 无优化需求; ②坏请求全属 hermes 越 cc2 范围; ③容器级分离 + fid 健康选择已达稳态。

## 验证
- curl 40006/4101 → 全 ok; nv_gw Up 6 hours。
- 30min cc4101-primary 实拉 = 127/127 (0 bad)。
- 30min bad JOIN 铁证: 3 条全 caller=hermes。

## 下一步
- 继续监控 hermes 线 all_tiers_exhausted (仍偶发, 但 100% 未影响 cc2 主链)。
- 维持当前架构, 不主动改码。cc2 SR 100% 已达稳态。