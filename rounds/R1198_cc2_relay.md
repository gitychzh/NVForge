# R1198 cc2 nv_gw NOP 巡检轮

## 结论: NOP 不改码 — 整窗全绿 (cc4101-primary 110/110 = 100% SR, 0 非-200, 跨四十一轮)

本轮 (2026-08-08 06:00 CST) 注入链路分析 + 活查复核 30min 窗口, 链路完全静稳,
无任何新错误, 无改码条件。

## 活查数据 (注入 05:58:33 CST + docker logs 复核, 30min)

- **cc4101-primary SR**: `status 200 = 110` = **100% SR**, 0 非-200
  (活查 `select status,count(*) from nv_requests where created_at>now()-interval 30 min and caller='cc4101-primary'`
  → `200|110` 单行, 完全无非-200)。
- **30min 链路总览 (caller × model × status)**: 
  `cc4101-primary|dsv4f0731_nv|200|109`, `hermes|dsv4f0731_nv|200|72` →
  总计 181 req 全 200。
- **按模型成功率**: dsv4f0731_nv **SR=100.0% (181/181)**。
- **错误分类 (nv_requests)**: `(无错误)` → **0 行** (caller=cc4101-primary 0 非-200)。
- **tier (nv_tier_attempts)**: per-key 全 `nvcf_pexec` (k0=22,k1=22,k2=22,k3=22,k4=23)
  = 111, **0 error**。无 429 / empty / 新错误类型。
- **fallback**: 注入 f=181 (总线), SR 100% 无实际触发 ms fallback。
- **容器健康**: nv_gw Up 27h (容器启动 31h), cc4101 Up 26h, `nv_gw_stable` Up 6 days,
  /health 均 ok。

## 依据 + 决策

判稳 (SR≥99% 且无新错误) → NOP 巡检轮。链路穿越四十一轮 (R1158→R1198) 整窗全绿,
主链 dsv4f0731_nv fid 281478d0-f307 稳定, 无需改任何参数。

## 验证

活查 110/110 = 100% SR, 0 非-200; tier 111 全 nvcf_pexec 0 error; fallback 0%; 容器健康。

## 下一步

维持静稳观察。核心监控仍是"是否重现独立瞬时 burst 及复发间隔"。
k0 偶发 NVCFPexecTimeout 已连续 11 轮 (R1188→R1198) 未复发 (最近一次 R1187),
继续通过 `ssleof-error-transient-egress-blip` 记忆跟踪, 持续分布才查 mihomo 线路。