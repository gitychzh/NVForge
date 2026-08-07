# R935 — cc2 NOP 巡检轮 (cc2 主链路连续 44 轮 100% 干净)

> 日期: 2026-08-07 | 容器: nv_gw Up 7h, cc4101 Up 7h, dsv4p_nv40066 Up 2d
> **判定: NOP, 不改码** — cc2 主链 (cc4101-primary → nv_gw:40006) 30min 全 200, 0 bad,
> 专属错误 0 rows; bad 请求 (all_tiers_exhausted ×3, 502) 全属 hermes 线 (caller 列铁证),
> fallback 0 次, 无新错误类。

## 本轮数据 (live DB 30min 实拉 ≈2026-08-07 CST 11:0x)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **106/106 = 100% SR, 0 bad** (实拉) | ✅ |
| 主链专属错误 (caller=cc4101-primary, status!=200) | **0 rows** | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×3 | ⚠️ 越界 |
| bad caller 归属 | 3 req 全 caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (106 请求, fb=0) | ✅ |
| scoped health | 4101/40006/40066 全 ok (200) | ✅ |

### 说明 (对齐本轮 live 实拉)
- 30min 全 caller×status = `cc4101-primary 106 × 200` + `hermes 11 × 200` + `hermes 3 × 502` = **120**,
  dsv4f0731_nv 整体 SR=97.5% (117/120)。
- **cc4101-primary 30min 实拉 = 106/106 全 200 (100% SR)**, 专属错误 (status!=200 AND caller='cc4101-primary') = **0 rows**。
- 唯一错误类 `all_tiers_exhausted ×3` 100% 属 caller=hermes (实拉铁证, 未泄漏进 cc2 主链)。

## 改动 + 依据
- **改动: 无 (NOP)。** cc2 主链连续 44 轮 (R892-R935) 100% 干净, 主专属错误 0 行。
- 依据: ①cc4101-primary SR 100% + 专属错误 0 rows; ②bad 全属 hermes 越 cc2 范围;
  ③fallback 0 次; ④无新错误类; ⑤多 tier round-robin + func_health 已达稳态。

## 验证
- curl 4101/40006/40066 → 全 ok (200)。
- 30min nv_requests cc4101-primary 实拉 = 106/106 (0 bad); 专属错误 0 rows。
- 30min 所有 bad 分组 (caller 列铁证): 3 条全 hermes, cc2 主链 0 bad。
- cc_requests fallback = 0 次。

## 下一步
- 继续 NOP 巡检; 下轮重拉 30min 窗口。
- 若 cc4101-primary 专属错误 > 0 或 SR < 99%, 先找根因再小步改 (铁律 1/2)。
- ⚠️ 连续两轮 `nv_gw Up 7h` (R934 亦 7h, R933 12h), 有外部 `nv_gw_stable Up 5d` 并存;
  若 nv_gw UP 时间继续缩短或重启频繁, 查是谁在重启 nv_gw (非 cc2 本轮动作)。