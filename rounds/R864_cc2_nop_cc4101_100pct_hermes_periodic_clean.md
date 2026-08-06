# R864 — cc2 NOP 巡检轮 (MEME)

> 近窗 cc4101-primary SR=100% (127×200) 零错误, 无 buffer/wait/keymanager 日志
> (buffer 一次成交). 30min 残留 all_tiers_exhausted×5(502, avg~180s) 全为 caller=hermes
> 外部 cron 客户端 (严格 ~6min 周期), 每次 ~180s=5×90s buffer deadline 全额耗尽,
> 属 cron 请求特征而非链路退化 (沿用 R853-R863 判定). 5key 均足量 pexec_success
> (k0-k4 各 25-26), 瞬态错误 (RemoteDisconnected/529/timeout/empty_200/504) 被跨 key
> round-robin 自适应吸收, 未上抛 cc2. fallback 触发率 0% (133 请求 0 fallback).
> cc2 自身路径 127×200 零错误, 链路/KeyManager 健康, 修复链自适应吸收正常.
> nv_gw/cc4101/dsv4p 三 health ok. **不改码.**

## 轮前注入分析 (2026-08-07 ~05:06 CST)

### 30min cc4101-primary 专属 SR = 100% (127×200, 零错误)

r/o 实测 (实时 DB, UTC):
```
caller         | status | count
cc4101-primary |   200  | 127     ← cc2 自身路径 100% 零错误
hermes         |   502  |   5     ← 外部 cron, 严格 ~6min 周期
```

30min 错误核验: nv_requests 全 5 个非 200 的 caller=hermes, cc4101-primary 零错误.

### fallback 触发率 0%

r/o 30min: 133 条请求 fallback field 全空, **0 次 fallback**. 符合目标 (<5%).

### all_tiers_exhausted×5 归属 hermes 周期 cron, 非链路退化

30min 5 条 all_tiers_exhausted (502, avg ~180041ms≈5×90s buffer deadline 全额耗尽)
经 caller 字段核验 **全部 caller=hermes** (外部 cron, ~6min 周期), 与 cc2/cc4101 无关.

### per-key nv_tier_attempts (30min)

```
key | pexec_success | 瞬态错误 (RemoteDisc/529/timeout/empty_200/504)
0   | 25            | 5
1   | 25            | 5
2   | 26            | 4
3   | 26            | 4
4   | 26            | 4
     ---------- 128 成功 ----------
```
5 key 均足量 pexec_success, 瞬态错误被 KeyManager 跨 key round-robin 平滑吸收, 未上抛用户.

### buffer/wait/keymanager 日志: 无

30min 无 BUFFER-/WAIT-/KeyManager 打补丁日志 → buffer 一次成交, 链路健康无退化.

### 三容器 health

```
40006 nv_gw:   ok (passthrough, 5 keys, pexec_models 含 dsv4f0731_nv)
40066 dsv4p:   ok (passthrough, 5 keys)
4101 cc4101:   ok (primary=dsv4f0731_nv)
```

## 判定

**NOP 巡检轮**: cc2 路径全净 (127×200 零错误), fallback 0%, buffer 一次成交无退化,
hermes 502 严格周期属外部 cron. 无新错误类型, 无退化体症. 链路/KeyManager/修复链健康.
**不改码.**

## 下一步

- 持续监控 primary=dsv4f0731_nv 维持 100%, 若开始持续失败再评估 failover/备用 fid.
- 沿用 R829+R833+R853 修复链: dsv4f0731_nv 为主, 跨 key round-robin 自适应吸收.
- hermes cron 502 保持旁观 (其自身 buffer 满额耗尽特征, 非本链路可治).

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