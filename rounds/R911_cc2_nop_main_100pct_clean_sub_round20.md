# R911 — cc2 NOP 巡检轮 (主链连续第 20 轮 100% 干净)

> 时间: 2026-08-07 ~09:23 CST (live DB now()≈2026-08-07 09:23)
> 类型: NOP (不改码)。cc2 主链路持续 100% 干净, 无新错误类。

## 结论
- **cc2 主链 (cc4101-primary/dsv4f0731_nv): 119/119 = 100% SR, 0 bad。**
- 30min 所有 bad (3 条, 均 502) 100% 属 `caller=hermes` (2 × stream_absolute_cap + 1 × all_tiers_exhausted, 全坏 fid 52e1ddb6)。
  JOIN 铁证未进 cc2 主链候选池。
- buffer 全 attempt=1/5 成交 (9-10s success_tool_call), 0 重试 / 0 429 / 0 cooldown。
- fallback (cc2 线) 0 次 (0/123)。
- 容器: 4101/40006/40066 全 ok (200), nv_gw Up 6 hours, cc4101 Up 5 hours。

## 数据 (实拉 30min window, 2026-08-07 09:23)

### 30min cc4101-primary (cc2 主链)
| status | count |
|---|---|
| 200 | 119 |
| !=200 | **0** |

### 30min 所有 bad (status!=200) — caller 归属
| caller | id+fid | status | count |
|---|---|---|---|
| hermes | (stream_absolute_cap ×2 + all_tiers_exhausted ×1) | 502 | 3 |

→ cc2 主链 0 bad。bad 100% hermes 越界, 全系坏 fid 52e1ddb6 (hermes 线宿主)。

### 30min fid 级健康 (nv_tier_attempts)
- 健康 fid **281478d0**: `pexec_success ×121`, 0 错误 → cc2 主链用的 fid。
- 坏 fid **52e1ddb6**: NVCFPexecRemoteDisconnected ×22 + 529_nv_overloaded ×3 + NVCFPexecTimeout ×1 + empty_200 ×2, 0 success。
  JOIN 铁证: `52e1ddb6 | hermes | 28` 全属 hermes caller → 0 泄漏进 cc2 主链。
- func_health 健康选择持续**未选中** 52e1ddb6, 主链 100% 走 281478d0。

### 30min buffer (cc4101-primary)
```
NV-BUFFER-START   dsv4f0731_nv caller=cc4101-primary
NV-BUFFER-ATTEMPT attempt=1/5 timeout=90s
NV-BUFFER-VERDICT attempt=1 success_tool_call 9-10s → FLUSH → SUCCESS flushed after 1 attempt(s)
```
全 attempt=1/5 成交, 0 重试 / 0 429 / 0 cooldown。

### fallback 发生率: 0 次 (0/123, cc2 线)

## 判断
cc2 主链路连续第 **20** 轮 (R892-R911) 100% SR 干净。bad 请求 100% 属 hermes (坏 fid 52e1ddb6 宿主线), JOIN 铁证未进 cc2 主链候选池。
**不改码**: ①主链 SR 100% 无优化需求; ②坏请求全属 hermes 越 cc2 范围; ③fid 健康选择 (281478d0 vs 52e1ddb6) 已达稳态, 隔离持续奏效。

## 验证
- curl 40006/4101/40066 → 全 ok; nv_gw Up 6h, cc4101 Up 5h。
- 30min cc4101-primary 实拉 = 119/119 (0 bad)。
- 30min bad JOIN 铁证: 3 条全 caller=hermes, 全坏 fid 52e1ddb6。
- 52e1ddb6 全部 28 次 attempts JOIN 归属 hermes, 0 进 cc2。
- fallback 0, cc_requests SR 100% (123/123)。

## 下一步
- 继续监控 hermes 线 all_tiers_exhausted / stream_absolute_cap (仍偶发, 但 100% 未影响 cc2 主链)。
- 维持当前架构, 不主动改码。cc2 SR 100% 已达稳态。