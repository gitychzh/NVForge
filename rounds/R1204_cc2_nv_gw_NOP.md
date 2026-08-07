# R1204 cc2 nv_gw NOP 巡检轮

**日期**: 2026-08-08 06:37 CST
**结论**: NOP 不改码。整窗全绿 (跨四十九轮)。注: 同步补上轮 R1203 未落盘到共享仓库的 STATE 差异。

## 数据 (30min 窗口, ~06:37 CST, 活查复核)

### 活查 cc4101-primary (nv_requests)
| status | count |
|---|---|
| 200 | **90** |

SR = **100%** (90/90), 0 非-200。

### 错误分类 (nv_requests status!=200, caller=cc4101-primary)
```
(0 行)
```
完全无错误。

### tier (nv_tier_attempts error_type)
| error_type | count |
|---|---|
| pexec_success | 90 |
| NVCFPexecRemoteDisconnected | 3 |

3× RemoteDisconnected 全为**孤立单-key 一次性瞬时**, 未上浮为请求失败:
| nv_key_idx | ts (UTC) |
|---|---|
| k1 | 22:27:42 |
| k2 | 22:28:52 |
| k3 | 22:33:40 |

跨 ~6min 的一次性 egress 抖动脉冲 (22:27→22:33 UTC, 窗口边缘), 之后立即恢复
pexec_success, 未复发, 无 429 / empty / 新类型。同 [[ssleof-error-transient-egress-blip]]
"孤立瞬时自愈" 模式, 非配置回归。

### fallback (注入 + cc_requests)
注入 f|140 → 0% 无实际触发 ms fallback。

### nv_gw buffer/wait/keymanager 日志
- `NV-BUFFER-START/ATTEMPT/SUCCESS` 全部 attempt=1 命中, elapsed 1-15s,
  buffered flush 正常。**无 WAIT-、无 retry、无 KEYMGR cooldown、无 429。**

### 容器健康
- nv_gw /health `{"status":"ok", nv_num_keys=5}` ok, cc4101 ok, dsv4p_nv40066 ok。
- 全部 buffer attempt=1 命中。

## 判断
链上静稳跨四十九轮 (R1156→R1204) 整窗全绿。SR=100%, 0 错误, 0 fallback,
buffer 全 attempt-1 命中, 3× 孤立 k1/k2/k3 RemoteDisconnected 一次性自愈 (未上浮,
无复发模式)。**NOP 不改码。**

## 改动
无 (NOP 巡检轮)。本轮同时把 R1203 的 STATE 差异同步补落共享仓库 (见下节)。

## 同步维护
本轮发现共享仓库 STATE.md 停留在 R1202 (R1203 轮 STATE 只 sync 到本地镜像
cc2_repair_self 43fbfa8, 未同步共享仓库) — `state-md-sync-required` 记忆项。
本轮 R1204 一次性把共享仓库 STATE.md 从 R1202 直接推进到 R1204,
并 commit round 文件 + STATE.md, 消除滞后。

## 下一步
维持静稳观察。核心监控仍是 **独立瞬时 burst 复发间隔** — 本轮 k1/k2/k3 的
RemoteDisconnected (22:27-22:33 UTC 一次性) 并入孤例跟踪; k0 偶发 NVCFPexecTimeout
最近一次 R1187, 已连续 17 轮 (R1188→R1204) 未复发, 经 `ssleof-error-transient-egress-blip`
记忆跟踪, 持续分布才查 mihomo 线路。