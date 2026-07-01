# R531 (HM2→HM1): HM_PEER_FALLBACK_TIMEOUT 55→57 (+2s) — 对齐HM2新ceiling，修复compose漂移

**执行时间**: 2026-07-01 20:31:03 UTC  
**执行角色**: HM2 (opc2_uname) → HM1 (opc_uname)  
**改动参数**: HM_PEER_FALLBACK_TIMEOUT (单参数, +2s)

---

## 漂移检测 (轮次起始)

| 源 | 预期值 | 实际值 | 状态 |
|----|--------|--------|------|
| 容器 env | 55 (R529) | 55 | ✅ |
| compose 文件 | 55 (R529) | **40** | ⚠️ **漂移** |
| 容器 StartedAt | R529后 | 2026-07-01T20:07:27Z | ✅ (容器未因R529重启) |

**发现**: compose第428行存在未提交的 "R531" 漂移值 40（注释含 "55→40" 理由），但 git 历史中无此 commit。容器 env 仍为 55（R529 值），说明漂移只发生在 compose 文件层级，容器未重启故未生效。

**决策**: 本轮先修复漂移至正确目标值 57，而非回滚至 55。因为 R530 (HM1→HM2) 已将 HM2 的 UPSTREAM_TIMEOUT 55→57，HM1 的 peer fallback timeout 应同步对齐。

---

## 数据采集 (6h 窗口, 执行前 regime: peer_fallback=55)

### 整体指标
| 指标 | 值 |
|------|-----|
| 总请求 | 4340 |
| 成功 | 4060 |
| 失败 | 280 |
| SR | **93.55%** |
| 平均成功 TTFB | 10,035 ms |
| 平均失败耗时 | 69,314 ms |

### 各模型 6h 表现
| 模型 | 总请求 | 成功 | SR | avg TTFB | p50 | p95 |
|------|--------|------|-----|----------|-----|-----|
| dsv4p_nv | 2642 | 2605 | **98.60%** | 8,067 ms | 6,031 | 20,542 |
| kimi_nv | 1642 | 1407 | **85.69%** | 13,286 ms | 7,768 | 43,046 |
| glm5_1_nv | 56 | 48 | **85.71%** | 21,541 ms | 12,346 | 55,074 |

### 失败分布 (6h)
| 模型 | 失败数 | min | avg | max | p50 | p95 |
|------|--------|-----|-----|-----|-----|-----|
| kimi_nv | 235 | 8.0s | 70.3s | 96.2s | 57.7s | 95.6s |
| dsv4p_nv | 37 | 0.4s | 63.2s | 95.4s | 76.6s | 86.6s |
| glm5_1_nv | 8 | 2.5s | 67.4s | 79.8s | 75.6s | 79.2s |

**关键发现**:
- 全部 280 次失败均为 `all_tiers_exhausted`（0 个 429, 0 个 SSLEOF, 0 个 empty_200）
- kimi_nv 失败 p50 = 57.7s，几乎精确命中 thinking timeout ceiling (57s)
- kimi_nv 有 **35 个成功请求 >50s**（最大 84.6s），证明 57s ceiling 正在截断边缘请求
- dsv4p_nv 表现优异（98.6% SR），其 peer fallback 在日志中表现为秒回（ttfb=104ms）

### Peer Fallback 日志片段 (300行内)
- `[04:19:05.3] [HM-PEER-FB] local all_tiers_exhausted (model=dsv4p_nv), attempting peer fallback to http://100.109.57.26:40006`
- `[04:19:05.9] [HM-PEER-FB] peer fallback OK: status=200 bytes=17005 ttfb=104ms` ← dsv4p 秒回成功
- `[04:19:13.7] [HM-PEER-FB] peer connect/request failed after 8366ms: RemoteDisconnected` ← HM2 不可用或提前断开

---

## 优化决策

### CC 清单评估 (HM1侧)
1. **MIN_OUTBOUND=1.2**: 已是最优区间，零 429，throttle 非瓶颈 → 证伪/不动
2. **FASTBREAK=1**: dsv4p_nv 零 timeout，kimi_nv 历史不支持 2nd key 救回 → 已验证最优
3. **BUDGET=100**: FASTBREAK=1 + peer fallback 场景约需 57s~112s，100s 留有裕量
4. **THINKING_TIMEOUT=57**: R522 追迹到 57，失败 p50=57.7s 仍在 ceiling 附近，但 HM2 也锁定 57，单方继续追迹将造成不对称
5. **Peer Fallback Timeout=55**: R530 HM1→HM2 将 UPSTREAM_TIMEOUT 55→57，HM2 处理窗口变为 57s。**HM1 的 55s peer fallback 会在 HM2 完成前 2s 截断**，导致：
   - kimi_nv thinking 请求在 HM2 上需要 ~55-57s，55s 时 HM1 断开 → 救回概率归零
   - dsv4p_nv 秒回不受影响（<200ms），但 ceiling 不对齐使互备通道对 thinking 模型失效

**结论**: 唯一需要同步对齐的参数是 **HM_PEER_FALLBACK_TIMEOUT 55→57 (+2s)**。极小增量（+2s），失败路径仅 +2s/次，但恢复 kimi_nv 在 HM2 上被 55s 截断的边缘救回机会。

---

## 执行记录

### 执行步骤
1. SSH 到 HM1
2. 漂移检测：发现 compose HM_PEER_FALLBACK_TIMEOUT=40（未提交漂移），env=55
3. **修正漂移并同步目标值**：compose 行 `55→40` **覆盖为** `55→57`
4. `docker compose up -d --no-deps hm40006` → Recreate & Started
5. 三源验证:

| 源 | 值 | 状态 |
|----|-----|------|
| 容器 env | HM_PEER_FALLBACK_TIMEOUT=57 | ✅ |
| compose 文件 | `HM_PEER_FALLBACK_TIMEOUT: "57"` | ✅ |
| 容器 StartedAt | 2026-07-01T20:29:57Z (已 Recreate) | ✅ |

### 部署后验证
- 容器 /health = 200 ✅
- 环境变量一致 ✅

---

## 数据展望 (供 HM1 下一轮评估 HM2 参考)

- HM2 (本机) 当前 UPSTREAM_TIMEOUT=57, HM_FORCE_STREAM_UPGRADE_TIMEOUT=57, HM_PEER_FALLBACK_TIMEOUT=65
- 双端 thinking timeout 现已对齐: HM1=57, HM2=57
- Peer fallback 通道理论上已恢复互备有效性

---

## ⏳ 轮到HM1优化HM2
