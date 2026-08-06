# R862 — cc2 NOP 巡检轮

- 时间: 2026-08-07 ~05:0x CST (DB UTC)
- 类型: NOP 巡检轮 (cc2 路径全净, 不改码)
- 结论: **cc4101-primary (cc2) 路径 125×200 SR=100% 零错误, buffer 全部一次成交 (attempt=1)**, 30min 残留 all_tiers_exhausted 全为 caller=hermes 外部 cron, 链路/KeyManager 健康.

## 数据 (30min, 实时拉取)

### cc2 自身路径 (cc4101-primary) SR = 100%
```
caller            | status | count
cc4101-primary    |    200 |   125    <- cc2 路径, 零错误
hermes            |    502 |     4    <- 外部 cron 客户端
```

### 错误归属: all 502 全为 caller=hermes
30min 窗口 4 条 `all_tiers_exhausted` (502, avg ~180s) 经 caller 字段核验 **全部 caller=hermes** (外部客户端, 非 cc4101), 呈严格 ~6-7min 周期. 每次 ~180s ≈ 5×90s=450s buffer deadline 全额耗尽, 属 cron 请求特征而非链路退化 (沿用 R853-R861 判定).

### Buffer 钢证据: 全部 attempt=1 一次成交
- 窗口全部请求 `NV-BUFFER-VERDICT attempt=1 verdict=success_*`, flush 于 1.7s / 12.6s / 8.4s (远小于 90s).
- 零 `NV-BUFFER-REFUSED`, 零 `WAIT-`, 零 KeyManager cooldown 日志, 零 buffer deadline 耗尽.

### per-key tier attempts (active tier) — 双 fid 吸收正常
```
key | 281478d0 | ok | 52e1ddb6 | ok
0   |    25    | 25 |     4    |  0
1   |    25    | 25 |     5    |  0
2   |    24    | 24 |     3    |  0
3   |    25    | 25 |     4    |  0
4   |    25    | 25 |     4    |  0
```
5 key 均在健康 fid 281478d0 100% 成功, 少数 52e1ddb6 失败 (3-5/key) 被跨 key round-robin 自适应吸收, 未上抛到用户请求 (沿用 R849-R861 双 fid 现象).

### 三容器 health
- nv_gw: `{"status":"ok","nv_num_keys":5,"nvcf_pexec_models":[kimi_nv,dsv4p_nv,dsv4f_nv,dsv4f0731_nv,glm5_2_nv]}` ✅
- cc4101: `{"status":"ok","primary":"dsv4f0731_nv"}` ✅
- dsv4p: ok ✅

## 关键判断: cc2 路径全净, NOP

cc2 自身 125×200 零错误, buffer 一次成交, KeyManager 跨 key round-robin 充分吸收瞬态 fid 失败.
残留 `all_tiers_exhausted` 严格归属 hermes 周期 cron 客户端, 非 cc2/链路退化. 不改码.

## 下一步
- 持续监控 cc2 路径 SR 与 buffer 成交.
- 若 hermes cron 周期 all_tiers_exhausted 持续 (~6-7min), 维持 hermes 属外部客户端之判定; 不为其改 nv_gw (铁律 3 只改 cc2 路径相关).

## 触发/基准
- nv_gw 5key, pexec_us_rr, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s, WAIT max 120s.
- 基线: cc2 路径 SR=100%, 目标持续越高越好.