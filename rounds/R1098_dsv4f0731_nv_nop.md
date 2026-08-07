# R1098: dsv4f0731_nv NOP — SR=97.8%, 稳定

**容器**: dsvf0731_nv40666 (opc2sname, 端口 40666)
**时间窗口**: 2026-08-07 17:36-18:06 UTC (01:36-02:06 Beijing)
**决策**: NOP — 零参数修改

## 30-min 数据

| 指标 | 值 |
|------|------|
| 总请求 | 184 |
| 成功 | 180 (97.8%) |
| 失败 | 4 (2.2%) |
| ATE | 0 |
| Fallback (hm4104) | 0 |
| 429 计数 (30min) | 0 |
| Avg/P50/P95/P99 | 9,923 / 7,640 / 23,791 / 45,833ms |
| TTFB avg | — |
| upstream | 100% nvcf_pexec |
| finish_reason | tool_calls=154, stop=26 |

## 错误分类 (30min)

| error_type | cnt | avg_ms |
|------------|-----|--------|
| zombie_empty_completion | 3 | 2,866 |
| NVStream_IncompleteRead | 1 | 45,678 |

## Per-key 延迟 (30min)

| Key | 200 count | 200 avg | 200 p95 | 错误 |
|-----|-----------|---------|---------|------|
| k0 | 39 | 10,019 | 27,888 | — |
| k1 | 37 | 10,466 | 20,136 | 1 zombie (2,675) |
| k2 | 34 | 7,883 | 14,545 | — |
| k3 | 34 | 9,987 | 16,955 | 1 zombie (3,269) + 1 IncompleteRead (45,678) |
| k4 | 36 | 10,723 | 35,514 | 1 zombie (2,654) |

## 6h / 3h 趋势

- **6h**: 1,692 req, 1,650 success (97.5%), 42 fail
- **3h 逐小时**:
  - 07:00 UTC: 227/220/7/0 — SR=96.9%, avg=12,345ms
  - 08:00 UTC: 260/251/9/0 — SR=96.5%, avg=12,495ms
  - 09:00 UTC: 363/358/5/0 — SR=98.6%, avg=9,890ms
  - 10:00 UTC: 33/32/1/0 — SR=97.0%, avg=12,131ms
- **24h ATE**: 311 (~13/hr, 非 dsv4f0731_nv 专属)

## 函数 ID 问题

**发现**: 本容器（dsvf0731_nv40666）仍在用旧 function_id `52e1ddb6`（dsv4f_nv 专用），而非新专用 FID `281478d0`（dsv4f0731_nv 专用）。

**原因**: 容器创建于 08-06 17:35 CST（25h 前），config.py 在 08-07 03:28 CST 更新了 `dsv4f0731_nv` → `281478d0`。由于 gateway/ 是 bind-mount，文件已更新但 Python 进程未重启，仍在跑旧代码。

**当前影响**: 有限。52e1ddb6 已恢复，30min SR=97.8%、1h SR~96%。但：
- 其他 host 用 281478d0 的 1h 数据: 218 请求, **100% SR**, avg 10,479ms
- 本容器用 52e1ddb6 的 1h 数据: 146 请求, 95.9% SR, avg 9,441ms
- 281478d0 更稳定（0 错误 v.s. 6 错误）

**修复**: 下轮若 ATE 上升或有异常，restart 容器即可。当前不操作。

## 决策理由

1. **SR=97.8% (30min), 97.5% (6h)** — 高于 95% 阈值，稳定
2. **0 fallback, 0 ATE, 0 429** — 无降级信号
3. **4 个错误均为 transient**:
   - zombie_empty_completion (3×): 快速 (<3.3s), 分布均匀
   - IncompleteRead (1×): 上游 NVCF 截断，非配置问题
4. **key_cycle_429s**: k0=71, k1=113（从容器启动累计，非 30min 数据）
5. **Per-key 延迟均匀**: 所有 5 key 均有流量，k2 最快 (7.9s)，整体均衡

## 后续关注点

- 若 52e1ddb6 再次劣化（ATE 上升），restart 容器使新 config (281478d0) 生效
- zombie_empty_completion 无 key 集中 → 当前 EMPTY_200_FASTBREAK=3 合适
- IncompleteRead 在 45s 处 → 接近 UPSTREAM_TIMEOUT=90 半值，非超时问题