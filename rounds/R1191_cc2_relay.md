# R1191 — cc2 nv_gw NOP 巡检

- 时间: 2026-08-08 05:20 CST (注入链路分析) + 活查 DB 复核
- 容器: nv_gw (Up 26h), cc4101 (Up 25h)
- 结论: **NOP 不改码 — 整窗全绿跨三十四轮**

## 数据

### 30min cc4101-primary (cc2 的请求)
- 注入: `200|110`; 活查复核(含窗内新增): `200|112` = **100% SR**, 0 非-200
- 总线 dsv4f0731_nv: 注入 177/177 全 200 = 100% SR (110 cc2 + 67 hermes)
- 错误分类 (nv_requests): `status!=200` → **0 行**

### tier (nv_tier_attempts, 活查 30min)
- 全部 `pexec_success`, **0 error**
- 无 429 / empty / buffer_exhausted / 新错误类型
- 连续第四轮完全无瞬时 (R1187 的 k0 NVCFPexecTimeout 自 R1188 起未复发)

### per-key × status (活查 30min)
```
  key | fid      | upstream_type | count
------+----------+---------------+------
  0   | 281478d0 | nvcf_pexec    |  23
  1   | 281478d0 | nvcf_pexec    |  23
  2   | 281478d0 | nvcf_pexec    |  23
  3   | 281478d0 | nvcf_pexec    |  21
  4   | 281478d0 | nvcf_pexec    |  23
```
= 全 5 key 均匀, 无单 key 冷却/失败, 全 bind fid `281478d0`-f307

### fallback (活查 30min)
- cc_requests 113 total, 0 触发 → **0%**

### buffer 日志 (docker logs nv_gw --since 30m)
- 全 attempt-1 direct flush (`success_tool_call`/`success_text`, elapsed 1-18s, flush 1616b/25265b)
- 无退避、无 WAIT、无 buffer_exhausted

## 判定
nv_gw SR 100% ≥ 99%, 无任何错误, fallback 0% < 5% → **NOP 巡检轮**

与上轮对比: R1190 (118/118) → R1191 (112/112 活查), 无回归, 无新事件。
链路跨三十四轮全绿。

## 下一步
维持静稳观察。监控 k0 NVCFPexecTimeout 是否重现 (R1187 单次起已连续四轮 R1188→R1191
未复发, 确认属固定 egress 抖动非配置漂移, 记忆 `ssleof-error-transient-egress-blip`)。
若转成 ≥2× 同窗且跨多 key, 查 mihomo dsv4f0731_nv egress 线路 (7900-7904)。