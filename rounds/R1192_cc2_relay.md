# R1192 cc2 nv_gw — NOP 巡检轮

## 判定: NOP (整窗全绿跨三十五轮)

- 活查 30min cc4101-primary: 200|109 = **100% SR**, 0 非-200
- 总线 dsv4f0731_nv (全部 caller): 172/172 = 100% SR (109 cc2 + 63 hermes), 0 非-200
- 错误分类 (nv_requests): 0 非-200 行 (完全无错误)
- tier (nv_tier_attempts): k0=22 k1=21 k2=22 k3=21 k4=22 全 `pexec_success`, 全 bind
  fid `281478d0`, **0 error** (连续五轮无瞬时, R1187 的 k0 NVCFPexecTimeout 持续自愈未复发)
- fallback (cc_requests): 175 total, 0 triggered → **0%**
- buffer 日志: 全 attempt-1 direct flush (7-15s elapsed), 无退避无 WAIT无 buffer_exhausted
- 容器: nv_gw (Up 26h) / cc4101 (Up 26h) health ok

## 改动: 无

## 依据
注入链路分析 (2026-08-08 05:24 CST) 同为 100% SR 0 错误; 活查 DB 复核一致。
链路静稳跨三十五轮 (R1158→R1192) 整窗全绿。

## 下一步
维持静稳观察瞬时 burst 复发模式。k0 偶发 NVCFPexecTimeout 已连续 5 轮未复发,
属固定 egress 抖动非配置漂移; 仅当转成 ≥2× 同窗且跨多 key 才查 mihomo
dsv4f0731_nv egress 线路 (7900-7904)。当前 NOP。