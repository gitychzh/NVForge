# R267: HM1→HM2 — KEY_COOLDOWN_S 34→38 (+4s)

**回合类型**: 单参数优化  
**方向**: HM1→HM2 (HM1优化HM2)  
**日期**: 2026-06-29 03:16 CST  
**作者**: opc_uname  
**原则**: 更少报错 更快请求 超低延迟 稳定优先  
**铁律**: ⚠️ 只改HM2配置绝不改HM1本地 ⚠️ 绝不停止/重启/kill mihomo  
**单轮规则**: 少改多轮积累

---

## 数据收集 (03:13 CST)

### HM2运行容器环境变量
```
KEY_COOLDOWN_S=34
TIER_COOLDOWN_S=22 (DEAD — 不在config.py)
MIN_OUTBOUND_INTERVAL_S=12.0
UPSTREAM_TIMEOUT=75
TIER_TIMEOUT_BUDGET_S=128
HM_CONNECT_RESERVE_S=24
PROXY_TIMEOUT=300
```

### 30分钟窗口 — hm_requests
| 指标 | 值 |
|------|-----|
| 总请求 | 1114 |
| 成功(200) | 1024 |
| 成功率 | **91.92%** |
| p50延迟 | 23.3s |
| p95延迟 | 118.4s |
| 平均延迟 | 33.8s |

### 错误分布 (30min)
| 错误类型 | 数量 |
|----------|------|
| all_tiers_exhausted | 89 |
| NVStream_IncompleteRead | 1 |

### 10分钟突发窗口
| 指标 | 值 |
|------|-----|
| 总请求 | 1057 |
| 错误数 | 90 |
| 成功率 | 91.50% |
| 结论 | 错误全在最近10分钟,99%集中 |

### Tier分布 (30min)
| Tier | 请求数 | 平均延迟 | 回退次数 |
|------|--------|----------|----------|
| glm5.1_hm_nv | 187 | 43.6s | 4 |
| deepseek_hm_nv | 837 | 22.8s | 1 |
| (null/失败) | 89 | 116.3s | 0 |

### 429 per-key (30min)
| Key | 429次数 |
|-----|---------|
| k0 | 4 |
| k1 | 6 |
| k2 | 3 |
| k3 | 3 |
| k4 | 4 |
| 范围 | 1.5× (均匀,非单key热点) |

### Budget Breaks (今日日志)
```
20次 budget break (从00:00到03:13)
全部在 glm5.1_hm_nv tier
remaining 1.3s-9.7s < 10s minimum
```

### error_detail JSONL (最近20条)
```
all_429: false × 100% ← 混合故障模式确认
错误混合: NVCFPexecTimeout(10-44s) + empty_200 + 500_nv_error + SSLEOFError + 429
不是纯function级429饱和
```

### 10min tier_attempts错误分类
| Tier | 错误类型 | 数量 |
|------|---------|------|
| deepseek_hm_nv | NVCFPexecSSLEOFError | 45 |
| deepseek_hm_nv | NVCFPexecTimeout | 9 |
| glm5.1_hm_nv | 500_nv_error | 28 |
| glm5.1_hm_nv | 429_nv_rate_limit | 20 |
| glm5.1_hm_nv | NVCFPexecSSLEOFError | 17 |
| glm5.1_hm_nv | NVCFPexecConnectionResetError | 2 |

---

## 分析

1. **成功率仅91.92%** — 远低于99%阈值，需要参数优化。89 ATE + 1 NVStream = 90个错误/30min。

2. **all_429: false × 100%** — 所有error_detail JSONL都显示 `all_429: false`，这是R264定义的**混合故障模式**：NVCFPexecTimeout + empty_200 + 500_nv_error + SSLEOFError + 429的混合，不是纯function级429饱和。这证实NV API函数正在正常响应但返回服务器端错误，而非被限流。

3. **10min vs 30min 错误几乎全部重叠** — 1057/90 (10min) vs 1114/89 (30min)，`10min ≥ 30min` 是R262定义的需要变更信号：所有错误都集中在最近10分钟窗口。

4. **R258均衡值未达到**: KEY_COOLDOWN_S=34，距离R258目标38差4s。R264→R266正在逐步向38回推，当前还差一步。

5. **为什么选KEY_COOLDOWN_S**: 这是**唯一的活跃参数**中还没有达到R258均衡值的。当前34→38(+4s)是R264定义的双参数收敛路径中的最后一步——R264同时改了KEY_COOLDOWN(30)和MIN_OUTBOUND(12.0)，现在KEY_COOLDOWN补到38。

6. **为什么不是其他参数**:
   - `TIER_COOLDOWN_S=22` → DEAD PARAMETER,不在config.py。改它无效果。
   - `HM_CONNECT_RESERVE_S=24` → DEAD PARAMETER,不在config.py。改它无效果。
   - `MIN_OUTBOUND_INTERVAL_S=12.0` → 刚在R264从8.0→12.0(+4s)，已在向R258=15.6收敛中。本轮继续KEY_COOLDOWN收尾，下轮再动MIN_OUTBOUND。
   - `UPSTREAM_TIMEOUT=75` → 已经是高值，p95=118s比75高很多是因为NVCFPexecTimeout(~44s)占主导，不是UPSTREAM_TIMEOUT瓶颈。减小UPSTREAM_TIMEOUT会切掉合法慢请求。
   - `TIER_TIMEOUT_BUDGET_S=128` → 已经是高值，20次budget break中are用尽(remaining 1-7s)但128已足够。没有budget break是"有预算未用完"的情况。

7. **单参数规则**: 本次只改KEY_COOLDOWN_S一个参数 → 符合"少改多轮"原则。+4s delta在4-unit cap内。

---

## 执行

### 变更: KEY_COOLDOWN_S: 34 → 38 (+4s)

```bash
# 修改docker-compose.yml
ssh HM2 "sed -i 's|KEY_COOLDOWN_S: \"34\"|KEY_COOLDOWN_S: \"38\"|' /opt/cc-infra/docker-compose.yml"

# 重建容器(只改compose文件,不动mihomo)
ssh HM2 "cd /opt/cc-infra && docker compose up -d --force-recreate --no-deps hm40006"

# 验证
sleep 3 && docker exec hm40006 env | grep KEY_COOLDOWN_S  # → 38 ✓
```

### 验证结果
```
✅ KEY_COOLDOWN_S=38 (运行容器确认)
✅ docker ps: Up 20 seconds (healthy)
✅ mihomo PID 2008535 仍运行 (未触碰)
✅ curl http://localhost:40006/health → 200
```

### 预期效果
| 参数 | 变更前 | 变更后 | 方向 |
|------|--------|--------|------|
| KEY_COOLDOWN_S | 34s | 38s | +4s → R258均衡值=38 |

**效果**: 增加key级冷却 (+4s) → 当key遇到空200/超时/SSLEOF错误后进入更长的冷却期 → 减少在冷却key上立即重试的浪费 → 降低 `all_tiers_exhausted` 速率（每个key有机会在前一个key冷却结束后以更健康的状态重新尝试）。

**KEY_COOLDOWN_S收敛路径**:
- R264: 30 (from R263降到18后又抬到30)
- R266: 30→34 (+4s)
- **R267: 34→38 (+4s) ← 本回合,达到R258均衡值**

---

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记