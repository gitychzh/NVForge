# R1012 — cc2 NOP 巡检轮 (HM2 nv_gw 自优化)

> 日期: 2026-08-07 16:03 CST | 容器: nv_gw Up 13h, cc4101 Up 12h
> 上轮: R1011 (NOP, 主链 119/119 = 100% SR)

## 结论: NOP, 不改码

cc2 主链路连续 **第 120 轮 (R893-R1012) 100% SR 干净**, 主链专属错误 0 rows, fallback 0。

## 依据 (live 复核 2026-08-07 16:03 CST + 注入轮前链路分析)

### 30min 链路总览 (caller × model × status)
| caller | model | status | count |
|---|---|---|---|
| cc4101-primary | dsv4f0731_nv | 200 | 122 |
| hermes | dsv4f0731_nv | 200 | 12 |
| hermes | dsv4f0731_nv | 502 | 3 |

### 错误分类 (type × sub × count × avg_dur)
- `all_tiers_exhausted` × 3 (avg 178.6s)

**DB scoped 证实**: 这 3 条 bad (dsv4f0731_nv 502) **全部 caller=hermes** (live `SELECT caller,status` → 唯一 bad 行 caller=hermes, status=502, fid=52e1ddb6), cc2 主链 0 bad。
属 hermes 越界宿主 fid 52e1ddb6 泄漏 — 与主链 host 分离保持。

### 关键指标
| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw cc4101-primary | **122/122 = 100% SR, 0 bad** (live) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| 总 bad 归属 | 3 条全 hermes (dsv4f0731_nv 502, fid 52e1ddb6) | ✅(主链) |
| 30min nv_tier_attempts per-key | k0-k4 各 23-25 pexec_success + 少量 NVCFPexecRemoteDisconnected(14)/Timeout(2)/empty_200(1), 全被 buffer 吸收 | ✅ |
| 30min cc_requests | 121 req 无 fallback 触发, SR=100% | ✅ |
| buffer 日志 | 全 attempt=1 一次成功 (flush 1.6-5.6KB, 6-13s), 无 BUFFER-/WAIT- 停滞 | ✅ |

### fallback
本轮 window 内 cc2 主链无任何 fallback 触发 — dsv4f0731_nv 5key 未全败。
(注入 `f|136` 为解析伪影, nv_tier_attempts 显示 5 key 各自独立 pexec 均正常, 未全挂。)

## 判断

cc2 主链路连续 120 轮 (R893-R1012) 100% 干净, 主链专属错误 0 rows。本轮 3 条 bad
(dsv4f0731_nv 502) 归属全属 hermes 越界宿主 (fid 52e1ddb6 泄漏), 与主链 host 分离保持,
主链 122/122 全 200。nv_tier_attempts 里瞬态 NVCFPexecRemoteDisconnected(14)/Timeout(2)/empty_200(1)
被 buffer(attempt=1) + multi-key round-robin + func_health 完全吸收, 从未穿透到 caller。
无新 cc2 主链错误类, 无持久 key 疲劳, 无 BUFFER-/WAIT- 停滞。

**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②bad 全属 hermes 越界, 主链无根因可查;
③buffer + round-robin + func_health 已达稳态 (全 attempt=1 一次成功), 无参数可调。

## 下一步

- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 后续窗口继续确认 hermes 越界 bad (fid 52e1ddb6) 与主链持续隔离。

## 验证

- 30min nv_requests cc4101-primary = 122/122 (0 bad)。
- DB scoped: 主链专属错误分组空 (0 rows); 3 条非 200 全 caller=hermes (live `SELECT caller,status` 证实, fid 52e1ddb6)。
- cc_requests primary 30min 无 fallback 触发 (121 req, SR=100%)。
- buffer 日志全 attempt=1 success (flush 1.6-5.6KB, 6-13s), 无 BUFFER-/WAIT- 停滞。
- 容器: nv_gw Up 13h, cc4101 Up 12h, /health 40006/4101/40066 全 200。