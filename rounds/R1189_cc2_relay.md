# R1189 — cc2 nv_gw NOP 巡检

- 时间: 2026-08-08 05:12 CST (注入链路分析) + 活查 DB 复核
- 容器: nv_gw (Up 30h), cc4101 (Up 25h), dsv4p_nv40066 (Up 3d)
- 结论: **NOP 不改码 — 整窗全绿跨三十二轮**

## 数据

### 30min cc4101-primary (cc2 的请求)
- 活查: `200|118` = **100% SR**, 0 非-200
- 总线 dsv4f0731_nv: 190/190 全 200 = 100% SR (118 cc2 + 72 hermes)
- 错误分类 (nv_requests): `status!=200` → **0 行**

### tier (nv_tier_attempts, 活查 30min)
- 118 全 `pexec_success`, **0 error**
- 无 429 / empty / buffer_exhausted / 新错误类型
- 本窗完全无瞬时: R1187 的 k0 单次 NVCFPexecTimeout 已连续 2 轮 (R1188, R1189) 未复发

### per-key × fid
```
  key | fid      | error_type  | count
-------+---------+-------+------
  0   | 281478d0 | pexec_success |  24
  1   | 281478d0 | pexec_success |  24
  2   | 281478d0 | pexec_success |  23
  3   | 281478d0 | pexec_success |  23
  4   | 281478d0 | pexec_success |  24
```
= 全 5 key bind fid `281478d0`-f307, 均匀路由, 无单 key 冷却/失败

### fallback
- cc_requests 190 total, 0 触发 → **0%**

### buffer 日志 (docker logs nv_gw --since 30m)
- 全 attempt-1 direct flush (`success_text` / `success_tool_call`, elapsed 2-16s)
- 无退避、无 WAIT、无 buffer_exhausted

## 判定
nv_gw SR 100% ≥ 99%, 无任何错误, fallback 0% < 5% → **NOP 巡检轮**

与上轮对比: R1188 (119/119) → R1189 (118/118), 无回归, 无新事件。

## 下一步
维持静稳观察。监控 k0 NVCFPexecTimeout 是否重现 (已连续 2 轮未复发, 仍属固定 egress
抖动非配置漂移)。若转成 ≥2× 同窗且跨多 key, 查 mihomo dsv4f0731_nv egress 线路 (7900-7904)。