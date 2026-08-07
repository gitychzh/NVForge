# R930 — cc2 NOP 巡检轮 (不改码)

> cc2 主链路 (cc4101-primary → nv_gw:40006) 连续第 **39 轮** 100% 干净 (R892-R930)。
> 30min live 实拉: cc4101-primary 115/115 = 100% SR, 0 bad; 主链专属错误 0 rows。
> 4 个 bad (502) 全属 hermes 线 (caller 列实拉铁证), fallback 0 次。不改码。

## 数据 (30min 窗口, caller × status × error 实拉)

```
caller            | status | error_type              | count
------------------+--------+-------------------------+-------
cc4101-primary    |  200   |                         |  115   ← cc2 主链 100% clean
hermes            |  200   |                         |   18
hermes            |  502   | all_tiers_exhausted     |    3   ← 越界
hermes            |  502   | zombie_empty_completion |    1   ← 越界
```

### 关键指标
| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **115/115 = 100% SR, 0 bad** | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×3 + zombie_empty_completion ×1 | ⚠️ 越界 |
| bad caller 归属 | 4 条全 caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests 115 total) | **0 次** | ✅ |
| 容器 health | nv_gw 200, cc4101 200 | ✅ |

### 错误分类 (全部 bad 属 hermes, 非 cc2)
- `all_tiers_exhausted ×3` (all_tiers_failed_in_mapped_tier, avg_dur 180s) — hermes 5-key 全挂耗尽
- `zombie_empty_completion ×1` (avg_dur 7.8s) — hermes 空完成僵尸

### tier 层错误 (被 round-robin + func_health 吸收, 未浮现为 cc2 primary bad)
- NVCFPexecRemoteDisconnected: k0×4, k1×5, k2×3, k3×3, k4×3
- NVCFPexecTimeout: k1×1, k3×2
- 504_nv_gateway_timeout: k2×1, k3×1
- 每 key 均有 ~21-23 pexec_success, 多 tier 轮转吸收瞬态失败

## 判断
- cc2 主链路连续 **39 轮** (R892-R930) 100% SR 干净, 主链专属错误实拉 0 rows。
- 4 个 bad 100% 属 hermes (caller 列铁证, host-separated), fallback 0 次, 无新错误类。
- **不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②坏请求全属 hermes 越 cc2 范围;
  ③多 tier round-robin + func_health 健康选择已达稳态。

## 下一步
- 继续 NOP 巡检; 下轮重拉 30min 窗口。
- 若 cc4101-primary 专属错误 > 0 或 SR < 99%, 先找根因再小步改 (铁律 1/2)。