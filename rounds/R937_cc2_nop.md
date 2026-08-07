# R937 cc2 NOP 巡检轮 (HM2 nv_gw 主链路)

> 轮次: R937 | 日期: 2026-08-07 CST | 类型: NOP (不改码)
> 结论: cc2 主链路连续 **46** 轮 100% 干净 (R892→R937);
> cc4101-primary 30min = **109/109 = 100% SR, 0 bad**;
> cc4101-primary 专属错误 = **0 rows**; 坏请求全属 hermes 线, 未进 cc2 主链; fallback = 0 次。

## 改动

**无 (NOP)**。主链 SR 100% + 专属错误 0 行 + fallback 0, 无优化需求, 不改码。

## 依据 (live DB 30min 实拉 ≈2026-08-07 10:55 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **109/109 全 200, 0 bad (100% SR)**。
- 30min **cc4101-primary 专属错误 = 0 rows** (`status!=200 AND caller='cc4101-primary'` 全空)。
- 30min 所有 bad = `caller=hermes` ×2, 全 `all_tiers_exhausted` (502)。**caller 列铁证**归属 hermes, 0 条进 cc2 主链。
- fallback (cc_requests 30min) = **0 次** (109 请求, fb=0)。
- buffer 日志健康: cc4101-primary 请求全 attempt=1 成功 (elapsed 6~12s), 无 WAIT/QUEUE/exhausted; 主链无 KeyManager cooldown/429 痕迹。
- 容器 health: 4101/40006/40066 全 200 ok。

### 30min 数据表

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **109/109 = 100% SR, 0 bad** (实拉) | ✅ |
| 主链专属错误 (caller=cc4101-primary) | **0 rows** | ✅ |
| hermes 线 bad (502) | all_tiers_exhausted ×2 | ⚠️ 越界 |
| bad caller 归属 | 2 req 全 caller=hermes; cc2 primary 0 条 | ✅ 隔离 |
| fallback (cc_requests) | 0 次 | ✅ |
| buffer 首尝试成功率 | attempt=1 全成功 (6-12s) | ✅ |
| scoped health | 4101/40006/40066 全 200 | ✅ |

## 验证

- curl 4101/40006/40066 → 全 200 ok。
- 30min nv_requests cc4101-primary 实拉 = 109/109 (0 bad); 专属错误 0 rows。
- 30min 所有 bad 分组 (caller 列铁证): 2 条全 hermes, cc2 主链 0 bad。
- cc_requests fallback = 0 次。
- nv_gw buffer 日志全 attempt=1 成功, 无 exhausted/queueing。

## 关键判断

cc4101-primary 30min 真实 SR = 100% (109/109), 主链专属错误 0 行, fallback 0。
2 条 bad (all_tiers_exhausted) 100% 属 hermes 线 (caller 列实拉, 非 cc2 范围), 已用 func_health/容器隔离吸收。
**不改码**: ①主链 100% 干净无优化需求; ②坏请求属 hermes 越 cc2 范围; ③健康状态与 R936 一致。

> ⚠️ 观察项 (延续): nv_gw Up = 7h (稳定在 7h 节奏, R935/R936 had same), 同机 `nv_gw_stable Up 5d` 并存。
> 下轮若 nv_gw UP < 7h 或重启间隔异常 (已达观察条件连续多轮), 查外部 restart 来源
> (`docker events` + 宿主机 cron/systemd)。本轮 UP 时间未缩短, 维持节奏, 不触发。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)

1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid 281478d0), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败
4. 坏 fid 52e1ddb6 (hermes 宿主) 与主链健康 fid 281478d0 容器+候选池双层隔离

## 下一步

- 继续 NOP 巡检; 下轮重拉 30min 窗口。
- 若 cc4101-primary 专属错误 > 0 或 SR < 99%, 先找根因再小步改 (铁律 1/2)。
- 若 nv_gw UP 时间 < 7h 或重启间隔异常, 查外部 restart 来源。