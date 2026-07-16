# R1634: HM2→HM1 — PEER_FB_SKIP_MODELS add dsv4p_nv (save ~70s/ATE on useless peer-fb)

## 触发分析

- HM1 提交: `8fd2cb0` — R1633: HM2→HM1 NOP (5th consecutive)
- 判定: 轮到HM2 — 需要评估是否有新数据可优化

## 数据采集 (改前必有数据)

### HM1 nv_gw 日志 (17:03-18:26)

**dsv4p_nv: 3/3 ATE (NVCF 504 function-level), peer-fb 3/3 FAILED (100%):**
| 时间 | 结果 | 详情 |
|------|------|------|
| 17:05:51 | 502 ATE | k4→504, budget 66.0s remaining 1.9s < 5s min→break, peer-fb→502 after 70,404ms |
| 17:33:58 | 502 ATE | k5→504, peer-fb→TimeoutError after 72,084ms |
| 18:05:53 | 502 ATE | k1→504, peer-fb→502 after 70,369ms |

**glm5_2_nv: 5/5 success (100% post-restart):**
| 时间 | 结果 | 详情 |
|------|------|------|
| 18:19:20 | 200 | k4 pexec, 1,928ms |
| 18:19:41 | 200 | k5 pexec, 7,211ms |
| 18:21:59 | 200 | k1 pexec, 8,876ms |
| 18:25:35 | 200 | k2 pexec, 12,490ms |
| 18:25:47 | 200 | k3 pexec, 9,310ms |
| 18:25:57 | 200 | k4 pexec, 17,226ms |

### HM1 DB (3h窗口)
| mapped_model | status | count | avg_ms | max_ms |
|--------------|--------|-------|--------|--------|
| dsv4p_nv     | 200    | 3     | 14,852 | 18,518 |
| dsv4p_nv     | 502    | 5     | 67,130 | 72,030 |
| glm5_2_nv    | 200    | 14    | 9,208  | 17,529 |
| glm5_2_nv    | 502    | 6     | 8,901  | 13,905 |

### HM2 nv_gw 日志 (18:24-18:30)
- dsv4p_nv: 504 (k2) + NVCFPexecTimeout (k3, 70,211ms), all 5 keys failed
- HM2 PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv — HM2 already skips dsv4p_nv peer-fb
- HM2 logs: "dsv4p_nv in peer-fb skip list (NVCF DEGRADING, peer same function also bad)"

## 分析

### 根因: dsv4p_nv peer-fb is 100% useless, wastes ~70s/ATE

HM1 dsv4p_nv ATE 3/3, peer-fb 3/3全部失败(100%):
- 2/3: HM2返回502 (HM2 nv_gw dsv4p_nv也all_tiers_exhausted)
- 1/3: TimeoutError after 72,084ms

HM2日志证实: HM2自己也遇到dsv4p_nv 504+timeout, 且HM2已配置`PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`跳过peer-fb。

**HM1当前PEER_FB_SKIP_MODELS为空** — 每次dsv4p_nv ATE浪费~70s在已知无用的peer-fb上, 然后才返回502给agent。

### 优化: 添加 dsv4p_nv 到 PEER_FB_SKIP_MODELS

**对齐HM2**: HM2已配置`PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv`, HM1同步添加dsv4p_nv。

**效果**: 每次dsv4p_nv ATE省~70s peer-fb等待 → agent更快获知失败 → 更快fallback到ms_gw/其他模型。

**glm5_2_nv**: 保持peer-fb enabled (当前post-restart 100% SR, 但如果以后退化, peer-fb给HM2独立key池救急)。

**为什么不加glm5_2_nv**: glm5_2_nv当前post-restart 6/6 success (100%), peer-fb path健康保留。HM2加了glm5_2_nv是因为HM2的glm5_2_nv走integrate_us_rr+zombie路径, 与HM1不同。

## 变更

| 参数 | 旧值 | 新值 | 节省 |
|------|------|------|------|
| NVU_PEER_FB_SKIP_MODELS | "" | "dsv4p_nv" | ~70s/ATE (跳过无效peer-fb) |

- 单参数修改
- compose only, 无代码修改
- docker compose up -d nv_gw 重启验证

## 验证

- `docker exec nv_gw env | grep PEER_FB_SKIP`: **NVU_PEER_FB_SKIP_MODELS=dsv4p_nv** ✅
- `curl http://localhost:40006/health`: **{"status":"ok"}** ✅
- 预算安全: 66s tier + 0s peer-fb (skip) = 66s < 205s BUDGET ✅
- 铁律: 只改HM1不改HM2 ✅

## 铁律:只改HM1不改HM2 ✅
## ⏳ 轮到HM1优化HM2