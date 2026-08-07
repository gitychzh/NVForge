# R933 — cc2 NOP 巡检轮 (cc2 主链路连续 42 轮 100% 干净)

> 日期: 2026-08-07 | 容器: nv_gw Up 12h, cc4101 Up 7h
> **判定: NOP, 不改码** — cc2 主链 (cc4101-primary → nv_gw:40006) 30min 全 200, 0 bad,
> 专属错误 0 rows; bad 请求 (all_tiers_exhausted ×3, 502) 全属 hermes 线 (caller 列铁证),
> fallback 0 次, 无新错误类。

## 本轮数据 (live DB 30min 实拉 ≈2026-08-07 CST)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **114/114 = 100% SR, 0 bad** (实拉) | ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×3 | ⚠️ 越界 |
| bad caller 归属 | 3 req 全 caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 | ✅ |
| scoped health | 4101/40006/40066 全 ok (200) | ✅ |

### 说明 (对齐本轮 live 实拉)
- 30min 全 caller = `cc4101-primary 114 × 200` + `hermes 13 × 200` + `hermes 3 × 502` = **130**,
  整体 SR 127/130 = 97.7%。bad 的 3 条正是 3 个 all_tiers_exhausted, 全属 hermes。
- cc4101-primary 专属错误实拉 = 0 rows (114 全 200)。
- tier 层 NVCFPexecRemoteDisconnected(16) / NVCFPexecTimeout(3) / empty_200(2)
  全被多 tier round-robin + func_health 吸收, 未浮现为 cc2 primary bad。

## 改动
**无 (NOP)。** cc2 主链路连续第 42 轮 (R892-R933) 100% SR 干净, 主专属错误 0 行;
bad 请求 100% 属 hermes (caller 列实拉铁证未进 cc2 主链), fallback 0 次, 无新错误类。

## 依据
1. live DB 30min: `cc4101-primary 114/114 全 200, 0 bad` (实拉, caller='cc4101-primary')。
2. scoped 错误 query: `status != 200 AND caller='cc4101-primary'` → **0 rows**。
3. bad 分组 query: `caller='hermes', status=502 × 3` — 0 条用 cc2 主链。
4. fallback (cc_requests 30min 114 total) = 0 次。
5. 容器 health: 4101/40006/40066 全 ok (200)。

## 验证
- curl 4101/40006/40066 → 全 ok (200)。
- 30min nv_requests cc4101-primary 实拉 = 114/114 (0 bad); 专属错误 0 rows。
- 30min bad 分组 (caller 列铁证): 3 条全 hermes, cc2 主链 0 bad。
- cc_requests fallback = 0 次。

## 关键判断
cc2 主链路连续第 **42** 轮 (R892-R933) 100% SR 干净, 且 30min 主链专属错误实拉 0 rows。
bad 请求 100% 属 hermes (caller 列实拉铁证未进 cc2 主链), fallback 0 次, 无新错误类。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②坏请求全属 hermes 越 cc2 范围;
③多 tier round-robin + func_health 健康选择已达稳态, 吸收底层瞬态失败。

## 下一步
- 继续 NOP 巡检; 下轮重拉 30min 窗口。
- 若 cc4101-primary 专属错误 > 0 或 SR < 99%, 先找根因再小步改 (铁律 1/2)。