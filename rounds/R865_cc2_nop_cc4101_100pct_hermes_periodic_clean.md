# R865 — cc2 NOP 巡检轮

> 近窗 cc4101-primary SR=100% (124×200) 零错误, 无 buffer 多attempt (=attempt1 一次成交),
> 无 wait/keymanager 退化日志. 30min 残留 all_tiers_exhausted×4 + stream_absolute_cap×1
> (502, avg ~180s) 经 caller 字段核验 **全部 caller=hermes** 外部 cron 客户端 (严格 ~6min 周期,
> fid=52e1ddb6), 与 cc2/cc4101 路径无关. 5key 均足量 pexec_success (k0-k4 各 24-25),
> 瞬态错误 (RemoteDisconnected/timeout/empty_200/529/504) 被跨 key round-robin 自适应吸收,
> 未上抛 cc2. cc2 自身路径 124×200 零错误, buffer attempt1 8-12s 一次成交 (verdict=success_tool_call),
> 链路/KeyManager/修复链健康. nv_gw/cc4101/dsv4p 三 health ok. **不改码.**

## 轮前注入分析 (2026-08-07 ~05:10 CST)

### 30min cc4101-primary 专属 SR = 100% (124×200, 零错误)

实时 DB (UTC):
```
caller         | status | count
cc4101-primary |   200  | 124     ← cc2 自身路径 100% 零错误
hermes         |   502  |   5     ← 外部 cron, 严格 ~6min 周期
```

30min 错误核验 (caller × error_type): 5 条非 200 全 caller=hermes
(4× all_tiers_exhausted + 1× stream_absolute_cap), cc4101-primary 零错误.

### fallback 触发率

30min cc4101 路径 0 fallback, 符合目标 (<5%).

### all_tiers_exhausted/stream_absolute_cap 归属 hermes 周期 cron, 非链路退化

30min 5 条 502 时间戳严格 ~5-6min 周期: 20:42 / 20:48 / 20:54 / 21:00 / 21:06 (all_tiers_exhausted)
+ 21:09 (stream_absolute_cap), 全为 caller=hermes, fid=52e1ddb6.
每个 all_tiers_exhausted ~180s ≈ 5×90s buffer deadline 全额耗尽 → 属 hermes 该客户端的
请求特征 (其自身在耗尽后再请求的 cron), 非本链路可治也不是本链路问题.

### per-key nv_tier_attempts (30min)

```
key | pexec_success | 瞬态错误 (RemoteDisc/529/timeout/empty_200/504)
0   | 25            | 5
1   | 24            | 4
2   | 24            | 4
3   | 25            | 3
4   | 25            | 5
     ---------- 123 成功 ----------
```
5 key 均足量 pexec_success, 瞬态错误被 KeyManager 跨 key round-robin 平滑吸收, 未上抛用户.

### buffer/wait/keymanager 日志: attempt1 一次成交, 无退化

30min 无 WAIT-/KeyManager 打补丁日志; BUFFER 日志全为 cc4101-primary
attempt=1/5 verdict=success_tool_call, elapsed 8-12s, flushed (16723b/5882b/16626b)
→ buffer 一次成交, 5key 全在 attempt1 命中, 链路健康无退化.

### 三容器 health

```
40006 nv_gw:   ok (passthrough, 5 keys, pexec_models 含 dsv4f0731_nv)
40066 dsv4p:   ok (passthrough, 5 keys)
4101 cc4101:   ok (primary=dsv4f0731_nv)
```

## 判定

**NOP 巡检轮**: cc2 路径全净 (124×200 零错误), fallback 0%, buffer attempt1 一次成交无退化,
hermes 502 严格周期属外部 cron (fid=52e1ddb6 耗尽, 非 cc2 链路). 无新错误类型, 无退化体症.
链路/KeyManager/修复链健康. **不改码.**

## 下一步

- 持续监控 primary=dsv4f0731_nv 维持 100%, 若开始持续失败再评估 failover/备用 fid.
- 沿用 R829+R833+R853 修复链: dsv4f0731_nv 为主, 跨 key round-robin 自适应吸收.
- hermes cron (fid=52e1ddb6) 502 保持旁观 (其自身 buffer 满额耗尽后再请求特征, 非本链路可治).

## 参数快照 (无变化)

```
nv_gw(40006): pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
              NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, KEY_COOLDOWN_S=30,
              NV_INTEGRATE_KEY_COOLDOWN_S=90, UPSTREAM_TIMEOUT=90,
              TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180,
              NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 已恢复)
cc4101(4101): PRIMARY=dsv4f0731_nv (动态轮转), FALLBACK=ms_gw:40007 (glm5_2_ms),
              STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400,
              UPSTREAM_TIMEOUT=130, CC4101_PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30
DB tz: UTC (STATE 时间为 CST = UTC+8)
```