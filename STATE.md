# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R951 (NOP 巡检轮/不改码 — cc2 主链路连续第 59 轮 100% 干净; 坏请求 all_tiers_exhausted + stream_absolute_cap + zombie 全属 hermes 线, caller 归属非 cc2 范围; fallback 0 次; zombie_empty_completion 本轮 45min 再现 1 但属越界 hermes)**
> cc4101-primary (主 nv_gw:40006) 实时 30min = **115/115 = 100% SR, 0 bad** (live 实拉);
> cc4101-primary 专属错误 45min = **0 rows** (115 request 全 200);
> 容器: nv_gw Up 8h, cc4101 Up 8h, nv_gw_stable Up 5d(并存), dsv4p_nv40066 Up 2d, dsvf0731_nv40666 Up 18h
> 上轮: R950 (NOP, 主链 117/117=100%)

## 本轮 (R951) 改动 + 依据 + 验证

### 改动: 无 (NOP。cc2 主链路连续 59 轮 100% 干净, 主专属错误 0 行; bad 请求全属 hermes 非 cc2; zombie_empty_completion 再现 1 属越界 hermes)

### 依据 (live DB 30-45min 实拉 ≈2026-08-07 13:0x CST)

- 30min cc4101-primary (主 nv_gw:40006) = **115/115 全 200, 0 bad (100% SR)** (live re-pull)。
- 45min 宽窗口 **cc4101-primary 专属错误 = 0 rows** (status != 200 AND caller='cc4101-primary' 全空)。
- 45min 所有 bad (非 200) = **全 `caller=hermes` ×5**: `all_tiers_exhausted ×3` + `stream_absolute_cap ×1` + `zombie_empty_completion ×1` (越界泄漏源 40666 decked, 未进 cc2 主链)。
- bad 请求 100% 属 hermes (caller 列归属: all_tiers_exhausted/stream_absolute_cap/zombie 全 hermes), 0 个属于 cc2 主链。
- zombie_empty_completion 45min 窗口再现 1 (R949 0 → R950 0 → R951 1, 属 hermes 越界, 不构成 cc2 风险)。
- fallback (cc_requests 30min) = **0 次** (1827 req, fb=0; cc4101-primary 专属 SR=100%)。
- nv_tier_attempts 30min: pexec_success (k0:22/k1:23/k2:24/k3:22/k4:24) + NVCFPexecRemoteDisconnected (k0:3/k1:4/k2:5/k3:4/k4:3) + NVCFPexecTimeout (k4:1)。瞬态错误被多 tier round-robin + buffer 重试吸收, 全部 resolve 为 200。
- buffer 日志: cc4101-primary 全 attempt=1 成功, 无 WAIT-/KEYMGR- 错误。
- 容器 health: 4101/40006/40066 全 ok (200)。
- 容器 UP: nv_gw 8h, cc4101 8h, dsv4p_nv40066 2d, nv_gw_stable 5d(并存), dsvf0731_nv40666 18h(hermes 越界泄漏源)。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **115/115 = 100% SR, 0 bad** (实拉) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** (45min 宽窗) | ✅ |
| hermes 线 bad (非 200) | all_tiers_exhausted ×3 + stream_absolute_cap ×1 + zombie ×1 (45min) | ⚠️ 越界 |
| bad caller 归属 | 全 caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (cc4101-primary SR=100%) | ✅ |
| zombie_empty_completion | 45min 再现 1 (R949→R950 0 → R951 1, 属 hermes) | ⚠️ 越界 |
| tier 瞬态错误 | RemoteDisconnected 19 + Timeout 1, 全被吸收 | ✅ |
| scoped health | 4101/40006/40066 全 ok (200) | ✅ |
| 容器 UP | nv_gw 8h / cc4101 8h / dsv4p 2d / 40666 18h(越界) | ✅ |

### 验证
- curl 4101/40006/40066 → 全 ok (200)。
- 30min nv_requests cc4101-primary live re-pull = 115/115 (0 bad); 45min 专属错误 0 rows。
- 45min 所有 bad 分组 (caller 列归属): 全 hermes, cc2 主链 0 bad。
- cc_requests fallback = 0 次 (cc4101-primary SR=100%)。
- docker logs nv_gw buffer 段: cc4101-primary 全 attempt=1 success, 无错误噪音。

### 关键判断
cc2 主链路连续第 **59** 轮 (R893-R951) 100% SR 干净, 且主链专属错误实拉 0 rows (45min 宽窗)。
bad 请求 100% 属 hermes (caller 列归属, 越界泄漏源 40666), fallback 0 次, 无新 cc2 主链错误类。
hermes zombie_empty_completion 本轮 45min 再现 1 (transient), 0 泄漏进 cc2 主链, 不构成 cc2 风险。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②坏请求全属 hermes 越 cc2 范围;
③多 tier round-robin + func_health 健康选择已达稳态, buffer 全 1-attempt 成功, tier 瞬态错误全被吸收 (RemoteDisconnected 19 全被 round-robin 消化)。

> ⚠️ 观察项 (R951): nv_gw Up = 8h (平稳无重启回归);
> 同机有 `nv_gw_stable Up 5d` 并存, dsv4p_nv40066 Up 2d, dsvf0731_nv40666 Up 18h(hermes 越界泄漏源)。
> hermes zombie_empty_completion 本轮 45min 再现 1 (transient), 全属 hermes 宿主越 cc2 范围, 不构成 cc2 风险。下轮继续观察。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid 281478d0), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败
4. 坏 fid 52e1ddb6 (hermes 宿主) 与主链健康 fid 281478d0 容器+候选池双层隔离

## 下一步
- 继续 NOP 巡检; 下轮重拉 30min 窗口。
- 若 cc4101-primary 专属错误 > 0 或 SR < 99%, 先找根因再小步改 (铁律 1/2)。
- 观察 hermes 线 zombie_empty_completion 是否持续 (>0 但 0 泄漏进 cc2 即无行动)。