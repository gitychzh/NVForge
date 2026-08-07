# R1066 cc2 — NOP 巡检轮 (不改码)

> 轮前链路分析 2026-08-07 19:33 CST 注入 + DB/容器复核
> 结论: **cc2(cc4101-primary) = 118/118 = 100% SR, 0 bad; 主链 fid 281478d0 零错误; fallback 0 次。
> R1060 遗留瞬时 ec39ddb9 已彻底滑出 30min lookback (预期兑现)。hermes 3 bads 非 cc2 范围。无参数可调 → NOP。**

## 数据 (30min 复核 2026-08-07)

| 指标 | 值 | 状态 |
|---|---|---|
| **cc2(cc4101-primary, 主 nv_gw:40006)** | **118/118 = 100% SR, 0 bad** | ✅ **0 bad 兑现** |
| fresh 窗口 | 全 200, 0 错误 | ✅ 当前健康 |
| 主链 scoped 错误 | **0** (R1060 瞬时 ec39ddb9 已彻底滑出 lookback) | ✅ 兑现上轮预测 |
| 主链 main fid 281478d0 nv_tier_attempts | pexec_success 全绿 (k0-k4) | ✅ |
| 30min cc_requests | 1961/1961 = 100% SR, **fallback 0 次 (0.0%)** | ✅ |
| hermes (越界宿主, 非 cc2 范围) | 200×38, 502×3 (zombie_empty_completion) | ⚠️(非主链) |
| nv_tier_attempts RemoteDisconnected | 3× (k0/k1/k3) — 均命中坏 fid 52e1ddb6 (hermes 越界) | ✅(非主链) |
| buffer 日志 | 无 fail/WAIT/KEYMGR | ✅ |
| 容器 | nv_gw Up 16h, cc4101 Up 16h, /health 40006/4101 全 200 | ✅ |

## 决策: NOP (不改码)

- **cc2 主链首次在完整 30min 窗口 0 bad**。R1060 瞬时 (SSLEOFError 3连 + ms_gw down) 已彻底滑出, 上轮预测兑现。
- 唯一 bads 归属 hermes 越界宿主 (zombie_empty_completion×3 + 3×RemoteDisconnected 命中坏 fid 52e1ddb6),
  request_id JOIN 铁证非 cc2 范围 (与 [[bad-fid-52e1ddb6-leaks-into-dsv4f0731-rotation]] 一致)。
- 无新错误、无参数偏离、fallback 0% → 无任何可调项。

## 验证
- `docker exec logs_db psql` 复核: cc4101-primary 118/118=100%, cc_requests 1961/1961=100% fallback 0。
- /health 40006/4101 全 200, 容器 Up 16h 稳定。

## 下一步
- 保持 NOP 观察。主链连续 2 轮 0 bad 后可视为抵达"完全健康基线"。
- 跟踪 SSLEOFError 密度: 仅当 >10 次/10min 且同窗多请求 502 才排查 egress; 当前低频常态, 无需动作。
- 单 key 连续多轮 100% 失败才考虑 KEY_FID_BIND 换 fid; 当前主链 fid 281478d0 全 pexec_success, 无此需。