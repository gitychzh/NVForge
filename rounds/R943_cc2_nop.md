# R943 cc2 NOP 巡检轮 (HM2 nv_gw 主链路)

> 轮次: R943 | 日期: 2026-08-07 CST | 类型: NOP (不改码)
> 结论: cc2 主链路连续 **51** 轮 100% 干净 (R893→R943);
> cc4101-primary 30min = **119/119 = 100% SR, 0 bad**;
> cc4101-primary 专属错误 = **0 rows**; 坏请求全属 hermes 线, 未进 cc2 主链; fallback = 0 次。

## 改动

无 (NOP。主链 100% 干净 + 专属错误 0 行, 无新错误类, bad 全越界 hermes)。

## 依据 (live DB 30min 实拉 ≈2026-08-07 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **119/119 全 200, 0 bad (100% SR)**。
- 30min **cc4101-primary 专属错误 = 0 rows** (status != 200 AND caller='cc4101-primary' 全空)。
- 30min 所有 bad (非 200) = `caller=hermes` ×4: `all_tiers_exhausted ×2` + `stream_absolute_cap ×1` + `zombie_empty_completion ×1`。
- **caller 列实拉铁证 (带 request_id)**: 4 bad 全 caller=hermes (105fb55f, e4f8ea10, 57772fd8, 4dd0664d), 0 个属于 cc2 主链 (host-separated)。
- zombie_empty_completion 保持 **1** (R941 首现 1, R942 保持 1, R943 保持 1 → 稳定, 越界 hermes 不构成 cc2 风险)。
- fallback (cc_requests 30min) = **0 次** (120 req, fb=0, SR=100.0)。
- nv_tier_attempts 30min: pexec_success 119 + NVCFPexecRemoteDisconnected 17 + empty_200 4 + NVCFPexecTimeout 2。
  瞬态错误被多 tier round-robin + buffer 重试吸收, 全部 resolve 为 200 (主链 0 bad)。
- buffer 日志: cc4101-primary 全 attempt=1 成功 (verdict=success_tool_call/success_text), 无 WAIT-/KEY- 错误, 450s 预算内。
- 容器 health: 4101/40006/40066 全 ok (200)。
- 容器 UP: nv_gw 8h (与 R942 持平, 平稳, 非重启回归), cc4101 7h (固定节奏), dsv4p_nv40066 2d。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **119/119 = 100% SR, 0 bad** (实拉) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| hermes 线 bad (非 200) | all_tiers_exhausted ×2 + stream_absolute_cap ×1 + zombie_empty_completion ×1 | ⚠️ 越界 |
| bad caller 归属 | 4 req 全 caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 (SR=100.0%) | ✅ |
| zombie_empty_completion | 1 (R941 首现 → R943 连续保持 1 未扩散) | ⚠️ 观察 |
| tier 瞬态错误 | RemoteDisconnected 17 + empty_200 4 + Timeout 2, 全被吸收 | ✅ |
| scoped health | 4101/40006/40066 全 ok (200) | ✅ |
| 容器 UP | nv_gw 8h (平稳) / cc4101 7h / dsv4p 2d | ✅ |

### 验证
- curl 4101/40006/40066 → 全 ok (200)。
- 30min nv_requests cc4101-primary 实拉 = 119/119 (0 bad); 专属错误 0 rows。
- 30min 所有 bad 分组 (caller 列铁证带 request_id): 4 条全 hermes (105fb55f, e4f8ea10, 57772fd8, 4dd0664d), cc2 主链 0 bad。
- cc_requests fallback = 0 次。
- docker logs nv_gw buffer 段: cc4101-primary 全 attempt=1 success, 无错误噪音。

### 关键判断
cc2 主链路连续第 **51** 轮 (R893-R943) 100% SR 干净, 且 30min 主链专属错误实拉 0 rows。
bad 请求 100% 属 hermes (caller 列实拉铁证带 request_id, 未进 cc2 主链), fallback 0 次, 无新 cc2 主链错误类。
zombie_empty_completion 连续第 3 轮保持单例 (R941→R942→R943), 未扩散, 属 hermes 越界。
**不改码**: ①主链 SR 100% + 专属错误 0 行, 无优化需求; ②坏请求全属 hermes 越 cc2 范围;
③多 tier round-robin + func_health 健康选择已达稳态, buffer 全 1-attempt 成功, tier 瞬态错误全被吸收。

> ⚠️ 观察项 (R943): nv_gw Up = 8h (与 R942 持平, 平稳无重启回归);
> 同机有 `nv_gw_stable Up 5d` 并存。zombie_empty_completion 连续保持单例未扩散,
> 全属 hermes 宿主越 cc2 范围, 不构成 cc2 风险。下轮继续观察 hermes zombie 是否扩散。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid 281478d0), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败
4. 坏 fid 52e1ddb6 (hermes 宿主) 与主链健康 fid 281478d0 容器+候选池双层隔离

## 下一步
- 继续 NOP 巡检; 下轮重拉 30min 窗口。
- 若 cc4101-primary 专属错误 > 0 或 SR < 99%, 先找根因再小步改 (铁律 1/2)。
- 观察 hermes 线 zombie_empty_completion 是否扩散 (0 泄漏进 cc2 即无行动)。