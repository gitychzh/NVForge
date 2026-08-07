# R934 — cc2 NOP 巡检轮 (cc2 主链路连续 43 轮 100% 干净)

> 日期: 2026-08-07 | 容器: nv_gw Up 7h, cc4101 Up 7h, dsv4p_nv40066 Up 2d
> **判定: NOP, 不改码** — cc2 主链 (cc4101-primary → nv_gw:40006) 30min 全 200, 0 bad,
> 专属错误 0 rows; bad 请求 (all_tiers_exhausted ×2, 502) 全属 hermes 线 (caller 列铁证),
> fallback 0 次, 无新错误类。

## 本轮数据 (live DB 30min 实拉 ≈2026-08-07 CST)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **111/111 = 100% SR, 0 bad** (实拉) | ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×2 | ⚠️ 越界 |
| bad caller 归属 | 2 req 全 caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (111 请求, fb=0) | ✅ |
| scoped health | 4101/40006/40066 全 ok (200) | ✅ |

### 说明 (对齐本轮 live 实拉)
- 30min 全 caller 302000 = `cc4101-primary 111 × 200` + `hermes 14 × 200` + `hermes 2 × 502` = **127**,
  dsv4f0731_nv 整体 SR=98.4% (125/127)。
- **cc4101-primary 30min 实拉 = 111/111 全 200 (100% SR)**, 专属错误 (status!=200 AND caller='cc4101-primary') = **0 rows**。
- 唯一错误类 `all_tiers_exhausted ×2` 100% 属 caller=hermes (实拉铁证)。

## 改动 + 依据
- **改动: 无 (NOP)。** cc2 主链连续 43 轮 100% 干净, 主专属错误 0 行。
- 依据: ①cc4101-primary SR 100% + 专属错误 0 rows; ②bad 全属 hermes 越 cc2 范围;
  ③fallback 0 次; ④无新错误类; ⑤多 tier round-robin + func_health 已达稳态。

## 验证
- curl 4101/40006/40066 → 全 ok (200)。
- 30min nv_requests cc4101-primary 实拉 = 111/111 (0 bad); 专属错误 0 rows。
- 30min 所有 bad 分组 (caller 列铁证): 2 条全 hermes, cc2 主链 0 bad。
- cc_requests fallback = 0 次。

## 下一步
- 继续 NOP 巡检; 下轮重拉 30min 窗口。
- 若 cc4101-primary 专属错误 > 0 或 SR < 99%, 先找根因再小步改 (铁律 1/2)。
- ⚠️ 本轮容器 `nv_gw Up 7h` (上轮 12h), 有外部 `nv_gw_stable Up 5d` 并存; 若下一轮 nv_gw
  UP 时间再次缩短, 提示有外部 restart 干扰, 需查是谁重启的。