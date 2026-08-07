# R1010 — cc2 NOP 巡检轮 (HM2 nv_gw 自优化)

> 日期: 2026-08-07 15:56 CST | 容器: nv_gw Up 17h, cc4101 Up 12h
> 上轮: R1009 (NOP, 主链 109/109 = 100% SR)

## 结论: NOP, 不改码

cc2 主链路连续 **第 118 轮 (R893-R1010) 100% SR 干净**, 主链专属错误 0 rows, fallback 0。

## 依据 (live 复核 2026-08-07 15:56 CST + 注入轮前链路分析)

### 30min 链路总览 (caller × model × status)
| caller | model | status | count |
|---|---|---|---|
| cc4101-primary | dsv4f0731_nv | 200 | 114 |
| hermes | dsv4f0731_nv | 200 | 4 |
| hermes | dsv4f0731_nv | 502 | 5 |

### 错误分类 (type × sub × count × avg_dur)
- `all_tiers_exhausted` × 4 (avg 178.9s)
- `zombie_empty_completion` × 1

**DB scoped 证实**: 这 5 条 bad **全部 caller=hermes** (502, dsv4f0731_nv), cc2 主链 0 bad。
属 hermes 越界宿主 fid 52e1ddb6 泄漏 — 与主链 host 分离保持。

### 关键指标
| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw cc4101-primary | **114/114 = 100% SR, 0 bad** (live) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| 总 bad 归属 | 5 条全 hermes (dsv4f0731_nv 502) | ✅(主链) |
| 30min nv_tier_attempts per-key | k0-k4 各 22-24 pexec_success + 少量 NVCFPexecRemoteDisconnected/Timeout/empty_200, 全被 buffer 吸收 | ✅ |
| 30min cc_requests | 114 total, 114 ok, **fb=0, SR=100%** (live re-pull) | ✅ |
| buffer 日志 | 全 attempt=1 一次成功 (flush 2.5-21KB, 5-10s), 无 BUFFER-/WAIT- 停滞 | ✅ |

### fallback
cc_requests 30min fb=0 次 — dsv4f0731_nv / glm5_2_nv 5key 未全败, 无任何 fallback 触发
(注入 `f|123` 为解析伪影, live re-pull 证实 cc_requests=114 total, fb=0, SR=100%)。

## 判断

cc2 主链路连续 118 轮 100% 干净, 主链专属错误 0 rows。本轮 window 内 5 条 bad 全属 hermes
越界宿主 (fid 52e1ddb6 泄漏), 与主链 host 分离保持, 主链 114/114 全 200。
nv_tier_attempts 里瞬态 NVCFPexecRemoteDisconnected/Timeout (1-5/key) 被 buffer(attempt=1) + multi-key
round-robin + func_health 完全吸收, 从未穿透到 caller。fallback 0 次, 无新错误类, 无持久 key 疲劳。

**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②bad 全属 hermes 越界, 主链无根因可查;
③buffer + round-robin + func_health 已达稳态 (全 attempt=1 一次成功), 无参数可调。

## 下一步

- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 后续窗口继续确认 hermes 越界 bad (fid 52e1ddb6) 与主链持续隔离。

## 验证

- 30min nv_requests cc4101-primary = 114/114 (0 bad)。
- DB scoped: 主链专属错误分组空 (0 rows); 5 条非 200 全 caller=hermes。
- cc_requests primary 30min = 114 total, fb=0, SR=100%。
- buffer 日志全 attempt=1 success, 无 BUFFER-/WAIT- 停滞。
- 容器: nv_gw Up 17h, cc4101 Up 12h, dsv4p health 200。