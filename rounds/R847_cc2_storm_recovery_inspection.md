# R847 (cc2) — NOP 巡检轮: R846 风暴延续观测 + 恢复确认 (dsv4f0731_nv 全量接管)

> 轮号: R847  |  观测时刻: 2026-08-07 04:01 CST (= 20:01 UTC, DB UTC 对齐)
> 容器: nv_gw Up 32min, cc4101 Up 6min(dfsv4f0731_nv 主)
> 结论: **NOP, 不改码** — R846 的 glm5_2_nv NVCF 风暴已充分退去, 修复链多 tier 自适应把
> cc4101 primary 轮转到健康 tier dsv4f0731_nv, 后者以稳定 6-10s/请求 全量成功。

## 判稳依据 (04:01 CST 实时拉取)

| 指标 | 值 | 状态 |
|---|---|---|
| **最近 5min cc4101-primary SR** | **100% (24/24)** 全走 dsv4f0731_nv | ✅ |
| **最近 15min 失败 (分钟级)** | 全在 19:53 以前 (glm5_2_nv 残留), 19:55 后零失败 | ✅ 恢复 |
| **glm5_2_nv tier 最近 10min** | 0 请求 (0 rows) — 风暴已退, 冷却中未被命中 | ✅ |
| **buffer 日志** | 全走 dsv4f0731_nv, 6-10s/请求 一次成功, 无 buffer_exhausted | ✅ |
| **fallback (ms_gw 层)** | 0% (满窗口 f=52/t=1, 唯一 t 也是 correct 未 relay) | ✅ |
| 容器健康 | 全 Up | ✅ |

## 30min 硬窗口残留 (缓解释义)

硬窗口数据里 glm5_2_nv|502×7, buffer_exhausted×14, all_tiers_exhausted×5 等都是
**19:53 以前的风暴残留**, 时间轴上已被自适应轮转吸收 (19:55 起 dsv4f0731_nv 全量成功)。
与 R836/R838/R840/R846 同型: NVCF glm5_2_nv 后端瞬时风暴 → 修复链多 tier 自适应 → 自限恢复。

## 修复链作用 (R827+R828+R829+R833+R813 + 多 tier 路由)

1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast (178s avg, vs 历史 465s)
2. cc4101 动态把 primary 轮转 → dsv4f0731_nv
3. dsv4f0731_nv 以稳定 6-10s/请求 全量成功, 用户无感知

## 健康检查

- `curl localhost:4101/health` → ok, **primary=dsv4f0731_nv** (自适应轮转仍生效)
- `curl localhost:40006/health` → ok (nv_gw, 5 keys, default=glm5_2_nv)
- `curl localhost:40066/health` → ok (dsv4p_nv40066)
- `curl localhost:40666/health` → ok (dsvf0731_nv40666)
- docker ps: 全 Up

## 参数快照 (无变化)

```
nv_gw: pexec_us_rr 单模式, KEY_FID_BIND 全 bind b1b22d03, BUFFER 5×90s=450s,
       WAIT max 120s, KeyManager 429→120-600s 指数退避, RemoteDisc→5s 短惩罚,
       TIER_COOLDOWN_S=180, NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 已恢复),
       PEER_FALLBACK=0
cc4101: PRIMARY 动态轮转 (风暴时 glm5_2_nv→dsv4f0731_nv),
        FALLBACK=ms_gw:40007 (CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400)
DB tz: UTC (STATE 时间为 CST = UTC+8)
```

## 下一步

- 长期观测。glm5_2_nv 冷却退去后, 观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标)。
- 继续关注 glm5_2_nv 恢复期间的 tier 状态; 若恢复未回归, 需判断是否 bind b6029a96 备用 fid。
- 不改码。修复链充分, 风暴自限。