# R1190 — cc2 nv_gw NOP 巡检

- 时间: 2026-08-08 05:18 CST (注入链路分析) + 活查 DB 复核
- 容器: nv_gw (Up 30h), cc4101 (Up 25h)
- 结论: **NOP 不改码 — 整窗全绿跨三十三轮**

## 数据

### 30min cc4101-primary (cc2 的请求)
- 活查: `200|118` = **100% SR**, 0 非-200
- 总线 dsv4f0731_nv: 注入 190/190 全 200 = 100% SR (118 cc2 + 72 hermes)
- 错误分类 (nv_requests): `status!=200` → **0 行**

### tier (nv_tier_attempts, 活查 30min)
- 全部 `pexec_success`, **0 error**
- 无 429 / empty / buffer_exhausted / 新错误类型
- 连续第三轮完全无瞬时 (R1187 的 k0 NVCFPexecTimeout 自 R1188 起未复发)

### per-key × status (活查 30min)
```
  key | status       | count
-------+--------------+------
  0   | pexec_success |  24
  1   | pexec_success |  24
  2   | pexec_success |  23
  3   | pexec_success |  23
  4   | pexec_success |  23
```
= 全 5 key 均匀, 无单 key 冷却/失败, 全 bind fid `281478d0`-f307

### fallback (活查 30min)
- cc_requests 117 total, 0 触发 → **0%**

### buffer 日志 (docker logs nv_gw --since 30m)
- 全 attempt-1 direct flush (`success_tool_call`, elapsed 8-10s direct flush 10156b/10074b)
- 无退避、无 WAIT、无 buffer_exhausted

## 判定
nv_gw SR 100% ≥ 99%, 无任何错误, fallback 0% < 5% → **NOP 巡检轮**

与上轮对比: R1189 (118/118) → R1190 (118/118), 无回归, 无新事件。
链路跨三十三轮全绿。

## 下一步
维持静稳观察。监控 k0 NVCFPexecTimeout 是否重现 (连续三轮 R1188→R1190 未复发,
仍属固定 egress 抖动非配置漂移)。若转成 ≥2× 同窗且跨多 key, 查 mihomo
dsv4f0731_nv egress 线路 (7900-7904)。