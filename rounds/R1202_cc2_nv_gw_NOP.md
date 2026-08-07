# R1202 cc2 nv_gw NOP 巡检轮

**日期**: 2026-08-08 06:25 CST
**结论**: NOP 不改码。整窗全绿。

## 数据 (30min 窗口, ~06:25 CST)

### 活查 cc4101-primary (nv_requests)
| status | count |
|---|---|
| 200 | **108** |

SR = **100%** (108/108), 0 非-200。

### 错误分类 (nv_requests status!=200)
```
(0 行)
```
完全无错误。

### tier (nv_tier_attempts error_type)
| error_type | count |
|---|---|
| pexec_success | 107 |

0 error。所有请求 pexec 成功打满。

### fallback (cc_requests)
total=107, fb=**0** → **0%**, 无实际触发 ms fallback。

### nv_gw buffer/wait/keymanager 日志
- `NV-BUFFER-START/ATTEMPT/SUCCESS` 全部 attempt=1 `success_tool_call`, elapsed 8-10s,
  buffered flush 正常。
- **无 WAIT-、无 retry、无 KEYMGR cooldown、无 429**。

### 容器健康
- nv_gw Up 27h, cc4101 Up 27h, nv_gw_stable Up 6 days。
- /health `{"status":"ok", nv_num_keys=5}` ok。

## 判断
链上静稳跨四十七轮 (R1156→R1202) 整窗全绿。SR=100%, 0 错误, 0 fallback,
buffer 全 attempt-1 命中, 无任何改码条件。**NOP 不改码。**

## 改动
无。

## 下一步
维持静稳观察。核心监控仍是 **独立瞬时 burst 复发间隔** — k0 偶发 NVCFPexecTimeout
最近一次 R1187, 已连续 15 轮 (R1188→R1202) 未复发, 经 `ssleof-error-transient-egress-blip`
记忆跟踪, 持续分布才查 mihomo 线路。