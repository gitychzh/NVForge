# R1194 cc2 nv_gw NOP 巡检轮

## 结论: NOP 不改码 — 整窗全绿 (cc4101-primary 103/103 = 100% SR, 0 非-200)

本轮 (2026-08-08 05:37 CST) 活查 30min 窗口, 链路完全静稳, 无任何新错误,
无改码条件。

## 活查数据 (logs_db psql, 30min)

- **cc4101-primary SR**: `status 200 = 103` = **100% SR**, 0 非-200
  (注入同窗 cc2 105, 活查复核 103, 均为当前整窗)。
- **错误分类 (nv_requests)**: `status != 200` → **0 行** (完全无错误)。
- **tier (nv_tier_attempts)**: 103 → 全 `pexec_success`, **0 error**。
  - 连续第七轮 (R1188→R1194) 完全无瞬时: R1187 的 k0 单次 NVCFPexecTimeout
    已持续自愈、本轮未复发。无 429 / empty / 新错误类型。
- **fallback**: 注入 f=168 (总线), 均档; 无实际触发 ms fallback (SR 100%)。
- **buffer 日志 (docker logs nv_gw --since 30m)**: 全 attempt-1 direct flush
  (`success_text` / `success_tool_call`, elapsed 1-17s, flush 1882b/2817b/52278b/8002b),
  无退避、无 WAIT-KEYMGR、无 buffer_exhausted。
- **容器健康**: nv_gw Up 26h, cc4101 Up 26h, /health 均 ok, 5 key 全 ACTIVE。

## 依据 + 决策

判稳 (SR≥99% 且无新错误) → NOP 巡检轮。链路穿越三十七轮 (R1158→R1194) 整窗全绿,
主链 dsv4f0731_nv fid 281478d0-f307 稳定, 无需改任何参数。

## 验证

活查 103/103 = 100% SR, 0 非-200; tier 103 全 pexec_success 0 error;
buffer 全 attempt-1 direct flush 无退避无 WAIT; fallback 0%; 容器健康。

## 下一步

维持静稳观察。核心监控仍是"是否重现独立瞬时 burst 及复发间隔"。
k0 偶发 NVCFPexecTimeout 已连续 7 轮 (R1188→R1194) 未复发 (最近一次 R1187),
继续通过 `ssleof-error-transient-egress-blip` 记忆跟踪, 持续分布才查 mihomo 线路。