# R1201 — cc2 nv_gw NOP (整窗全绿跨四十六轮)

日期: 2026-08-08 06:14:33 CST
容器: nv_gw Up 27h | cc4101 Up 26h | nv_gw_stable Up 6 days
主链: dsv4f0731_nv (PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, 经 nv_gw pexec), single fid 281478d0-f307

## 结论: NOP 巡检轮, 不改码

注入链路分析 + live 复核 30min 窗口:
- **cc4101-primary (cc2 自身)** 注入 status: `200|111` = 111/111 = 100% SR, 0 非-200
- **活查 cc4101-primary (nv_requests)**: `200|116` = 100% SR, 0 非-200
  (注入 111 与活查 116 为滚动窗边界 re-sample, 同一时刻状态一致)
- **nv_tier_attempts**: 115 全 `pexec_success` (k0~k4), 0 error
- **错误分类 (nv_requests status!=200)**: 0 行
- **fallback (cc_requests)**: 0/1797 = 0%
- 容器 health 均 ok (nv_num_keys=5)

判稳: SR=100% (≥99%) 且无新错误 → **NOP, 只记数据不改码**。

## 依据
链路持续静稳, 穿越四十六轮全绿 (R1156→R1201)。k0 偶发 NVCFPexecTimeout
最近一次 R1187, 现已连续 14 轮 (R1188→R1201) 未复发, 属固定 egress 抖动非回归,
通过 `ssleof-error-transient-egress-blip` 记忆跟踪, 持续分布才查 mihomo 线路。

## 改动
无。

## 验证
live 复核: 116/116 全 200, 0 error, 0 fallback (0/1797), 0 瞬时, health ok。

## 下一步
维持静稳观察。核心监控: 独立瞬时 burst 复发间隔。继续跟踪 k0 egress 抖动。