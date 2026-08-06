# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: R857 (NOP 巡检轮 — 近窗 cc4101-primary SR=100% 121×200 零错误, 30-min 残留 hermes 周期客户端 5×all_tiers_exhausted, 不改码, 2026-08-07 04:40 CST)
> 上轮: R856 (NOP — 近窗 cc4101-primary SR=100% 111×200 零错误, 不改码)

## 本轮 (R857) 改动 + 依据 + 验证

### 改动: 无 (NOP 巡检轮 — 近窗全净, hermes 周期客户端错误为外部特征, 修复链自适应吸收正常)

### 本轮数据 (04:40 CST, 轮前链路分析注入 + 实时 health curl, DB UTC 对齐)

**30min cc4101-primary (cc2 自己路径) SR = 100% (121×200, 零错误).** nv_gw buffer 近 30min 无
BUFFER/WAIT 异常日志 → 全走 dsv4f0731_nv 一次成交, 零 buffer_exhausted 零 WAIT.
nv_gw/cc4101 双 /health 全 ok (cc4101 primary=dsv4f0731_nv).

| 指标 | 值 | 状态 |
|---|---|---|
| **30min cc4101-primary SR** | **100% (121×200, 零错误)** | ✅ |
| **primary 目标 tier** | **dsv4f0731_nv** (自适应轮转持有) | ✅ |
| **buffer 日志** | 近 30min 无 BUFFER/WAIT 异常 → dsv4f0731_nv 一次成交 | ✅ 零 buffer_exhausted |
| **fallback (ms_gw 层)** | 0 次 | ✅ |
| **per-key (dsv4f0731)** | 5 key 均有足量 pexec_success (23-26), KeyManager 自适应吸收跨 key 瞬态 | ✅ |

### 30min 硬窗口残留 — hermes 周期客户端特征 (沿用 R853/R854/R855/R856 判定)

`all_tiers_exhausted×5` (502, avg 179s ≈ 90s×5 buffer deadline 全额耗尽) 全为 **caller=hermes
(外部客户端, 非 cc4101)**, 严格 ~5-6min 周期 — 为 cron/定时 hermes 客户端大请求在 buffer 峰值
耗尽时的特征, 与 cc2 路径无关. cc2 自身 121×200 + attempt=1/5 一次成交,
证明链路/KeyManager 未退化, 修复链正常吸收.

## 修复链 (沿用, R827+R828+R829+R833+R813)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 1-13s 一次成功, 用户无感知
3. 多 tier round-robin (dsv4p/dsv4f/dsv4f0731/glm5_2_nv) 自适应吸收底层跨 key 瞬态失败

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys, nvcf_pexec_models 含 dsv4p_nv/dsv4f_nv/dsv4f0731_nv/glm5_2_nv/kimi_nv)
- docker ps: nv_gw Up 1h, cc4101 Up 36min, dsv4p_nv40066 Up 2d — 全 Up ✅

## 参数快照 (无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, KeyManager 429→120-600s 指数退避, RemoteDisc→5s 短惩罚,
       TIER_COOLDOWN_S=180, NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 已恢复),
       PEER_FALLBACK_ENABLED=0
cc4101: PRIMARY 动态轮转 (风暴时 glm5_2_nv→dsv4f0731_nv),
        FALLBACK=ms_gw:40007 (CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130)
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步
- 长期观测。glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标)。
- 关注 glm5_2_nv 持续疲劳; 当前 dsv4f0731_nv 全量接管已吸收, 无需动。
- hermes 周期客户端 all_tiers_exhausted 为外部特征, 不影响 cc2 链路。
- 不改码。修复链充分, 近窗全净 (R857 同 R853-R856 同型)。