# R863 — cc2 NOP 巡检轮 (MEME)

> 近窗 cc4101-primary SR=100% (128×200) 零错误, buffer 全部 attempt=1 一次成交
> (flush 7-10s ≪ 90s). 30min 残留 all_tiers_exhausted×5(502) 全为 caller=hermes
> 外部 cron 客户端严格 ~6/12/18/24/30 min 周期分布 (20:36/42/48/54/21:00 UTC),
> 每次 ~180s=5×90s buffer deadline 全额耗尽, 属 cron 请求特征而非链路退化
> (沿用 R853-R862 判定). primary fid 281478d0 5key 均 25-26/25-26 100% 成功,
> failover fid 52e1ddb6 全败 (26) 被跨 key round-robin 自适应吸收. cc2 自身路径
> 128×200 零错误, 链路/KeyManager 健康, 修复链自适应吸收正常. nv_gw/cc4101/dsv4p
> 三 health ok. **不改码.**

## 轮前注入分析+实测核验 (2026-08-07 ~05:0x CST)

### 30min cc4101-primary 专属 SR = 100% (128×200, 零错误)

r/o 实测 (实时 DB, UTC):
```
caller         | status | count
cc4101-primary |   200  | 128     ← cc2 自身路径 100% 零错误
hermes         |   502  |   5     ← 外部 cron, 严格 ~6min 周期
```

15min 快窗: cc4101-primary **63×200 零错误**, 持续健康.

### buffer 全部一次成交 (attempt=1), 无退化

r/o nv_gw logs 抽样 (05:00-05:01):
```
NV-BUFFER-START  dsv4f0731_nv attempt=1/5 timeout=90s input=67785c
NV-BUFFER-VERDICT attempt=1 verdict=success_tool_call elapsed=7s
NV-BUFFER-FLUSH  flushing 11521b, verdict=success_tool_call
NV-BUFFER-SUCCESS flushed after 1 attempt(s), elapsed=7347ms   ← 一次成功
NV-BUFFER-SUCCESS ... elapsed=10239ms
NV-BUFFER-SUCCESS ... elapsed=8566ms
```
全部 attempt=1, elapsed 7-10s ≪ 90s budget, 无 WAIT-, 无 KeyManager 打补丁日志.

### all_tiers_exhausted×5 归属 hermes 周期 cron, 非链路退化

r/o 502 timeline (UTC, 严格 ~6min 周期):
```
20:36:01 hermes | 20:42:01 hermes | 20:48:01 hermes | 20:54:02 hermes | 21:00:01 hermes
```
与 R853-R862 判定一致: hermes 外部 cron 每次把 5key 全跑去 buffer deadline 耗尽后被拒,
与 cc2/cc4101 路径完全无关.

### per-key × fid (primary dsv4f0731_nv = fid 281478d0)

r/o nv_tier_attempts (30min, error_type='pexec_success'):
```
key | fid 281478d0 ok/total | fid 52e1ddb6 ok/total
0   | 25/25  (100%)         | 0/6    (failover 全部失败)
1   | 26/26  (100%)         | 0/6
2   | 26/26  (100%)         | 0/4
3   | 26/26  (100%)         | 0/5
4   | 25/25  (100%)         | 0/5
     ---------- 127/127 100% ----------
```
- **primary fid 281478d0 (dsv4f0731_nv): 127/127 = 100% 成功**, 5key 均衡.
- **failover fid 52e1ddb6: 全败 (26)**, 被 KeyManager 跨 key round-robin 吸收, 未上抛用户.
- 符合 R853 起观测的"双 fid 现象", 修复链自适应吸收正常.

### 三容器 health

```
40006 nv_gw:   ok (passthrough, 5 keys, pexec_models 含 dsv4f0731_nv)
40066 dsv4p:   ok (passthrough, 5 keys)
4101 cc4101:   ok (primary=dsv4f0731_nv)
```

## 判定

**NOP 巡检轮**: cc2 路径全净 (128×200 零错误, 15min 快窗 63×200), 主 fid 100% 成交,
buffer 一次成交无退化, hermes 502 严格周期臣服外部 cron. 无新错误类型, 无退化体症.
链路/KeyManager/修复链健康. **不改码.**

## 下一步

- 持续监控 primary fid 281478d0 维持 100%, 若其开始持续失败再评估 failover fid
  52e1ddb6 或切 b6029a96 备用.
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