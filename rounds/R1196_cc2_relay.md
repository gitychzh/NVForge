# R1196 cc2 nv_gw NOP 巡检轮

## 结论: NOP 不改码 — 整窗全绿 (cc4101-primary 104/104 = 100% SR, 0 非-200)

本轮 (2026-08-08 05:45 CST) 注入链路分析 + 活查复核 30min 窗口, 链路完全静稳,
无任何新错误, 无改码条件。

## 活查数据 (注入 05:45:33 CST + docker logs 复核, 30min)

- **cc4101-primary SR**: `status 200 = 104` = **100% SR**, 0 非-200
  (总时长 11479s, 平均 ~110s/req, 含缓冲等待)。
- **30min 链路总览 (caller × model × status)**: 
  `cc4101-primary|dsv4f0731_nv|200|104`, `hermes|dsv4f0731_nv|200|62` →
  总计 166 req 全 200。
- **按模型成功率**: dsv4f0731_nv **SR=100.0% (166/166)**。
- **错误分类 (nv_requests)**: `(无错误)` → **0 行**。
- **tier (nv_tier_attempts)**: per-key 全 `pexec_success` (k0=22,k1=21,k2=20,k3=20,k4=21)
  = 104, **0 error**。无 429 / empty / 新错误类型。
- **fallback**: 注入 f=166 (总线), SR 100% 无实际触发 ms fallback。
- **buffer 日志 (docker logs nv_gw --since 30m)**: `(无 buffer/wait/keymanager 日志)`
  — 全 attempt-1 direct flush 无退避无 WAIT。
- **容器健康**: nv_gw Up 26h, cc4101 Up 26h, `nv_gw_stable` Up 6 days,
  /health 均 ok (nv_gw 5 key FULL, dsv4f0731_nv 在 pexec 模型列)。

## 依据 + 决策

判稳 (SR≥99% 且无新错误) → NOP 巡检轮。链路穿越三十九轮 (R1158→R1196) 整窗全绿,
主链 dsv4f0731_nv fid 281478d0-f307 稳定, 无需改任何参数。

## 验证

活查 104/104 = 100% SR, 0 非-200; tier 104 全 pexec_success 0 error;
buffer 无日志 (全 direct flush); fallback 0%; 容器健康。

## 下一步

维持静稳观察。核心监控仍是"是否重现独立瞬时 burst 及复发间隔"。
k0 偶发 NVCFPexecTimeout 已连续 9 轮 (R1188→R1196) 未复发 (最近一次 R1187),
继续通过 `ssleof-error-transient-egress-blip` 记忆跟踪, 持续分布才查 mihomo 线路。