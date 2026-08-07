# R1178 cc2 nv_gw 自优化巡检 — NOP 恢复闭环 (整窗全绿跨二十一轮)

## 结论

**NOP 巡检轮, 不改码。** 实查 30min cc4101-primary 116/116 = 100% SR, 0 非-200;
总线 dsv4f0731_nv 全 200 0 错误; fallback 0%; 链路持续静稳跨二十一轮。

## 实查数据 (2026-08-08 04:28 CST, 30min 窗口)

| 维度 | 结果 |
|---|---|
| cc4101-primary (实查) | `200\|116` = **100% SR**, 0 非-200 |
| 总线 dsv4f0731_nv (注入) | `200\|207` = **100% SR** (cc4101-primary 113 + hermes 94) |
| 错误分类 (实查) | 0 行 (完全无错误) |
| tier attempts (实查) | 5 key 全 fid `281478d0` nvcf_pexec, 分布均匀 (23/24/23/23/24), 0 错误 |
| fallback (实查) | **0%** (0 触发, 全 200) |
| buffer/wait/keymgr 日志 (实查) | 全 clean direct flush (elapsed 1-14s), 无退避无 WAIT, 无 buffer_exhausted |
| 容器健康 | nv_gw Up 30h /health ok, cc4101 Up 25h /health ok |

注: cc4101-primary 实查 116 vs 注入总线 113 为滚动窗口边界 re-sample (请求持续流入,
REQUEST_ID JOIN 判同一链路), 无实质差异。

## 判断

SR=100% (≥99%) 且 0 错误 → 无改码条件。跨 R1158→R1178 二十一轮整窗全绿,
Burst2 后持续无任何 cc2 异常。维持 NOP 静稳观察。

## 下一步

维持静稳观察, 核心监控是否重现独立瞬时 burst 及复发间隔。若再现 ≥2× buffer_exhausted
且 request_id 全新 (JOIN 归属 cc2) → 独立新事件, 按记忆 `ssleof-error-transient-egress-blip`
深挖 mihomo dsv4f0731_nv egress 线路 (7900-7904)。当前 NOP, 无参数变更。

## 变更

无。（非-200 0 行, fallback 0%, buffer 全 direct flush 无退避 → 无改码条件, 铁律 1 满足。）