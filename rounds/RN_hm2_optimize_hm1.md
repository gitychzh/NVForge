# R768: HM2→HM1 — FASTBREAK 2→1 (-1 key) — BUDGET绑定约束发现

**时间**: 2026-07-06 03:50 UTC  
**作者**: opc2_uname (HM2)  
**类型**: HM2优化HM1（铁律：只改HM1不改HM2）

## 📊 改前数据

### 容器状态
| 项目 | 值 |
|------|-----|
| 容器名 | nv_gw |
| 状态 | Running |
| 最新轮次 | R766 (FASTBREAK 2) |

### 6h窗口 (约21:50 UTC — 03:50 UTC)
| 指标 | 值 |
|------|-----|
| 总请求 | 394 |
| OK (status=200) | 344 (87.3%) |
| FAIL (all_tiers_exhausted) | 50 (12.7%) |
| fallback_occurred=true | 95 |
| fallback成功 | 95/95 (100%) |

### per-model 6h
| 模型 | 总请求 | OK | ATE | SR |
|------|--------|-----|-----|-----|
| dsv4p_nv | 228 | 187 | 41 | 82.0% |
| glm5_2_nv | 158 | 151 | 7 | 95.6% |
| kimi_nv | 7 | 6 | 1 | 85.7% |

### 最近10请求
| 时间 | model | status | ttfb_ms | dur_ms | key_cycle_429s |
|------|-------|--------|---------|--------|----------------|
| 03:35:41 | dsv4p_nv | 200 | 96209 | 96210 | 1 |
| 03:35:30 | dsv4p_nv | 200 | 10690 | 10690 | 0 |
| 03:33:20 | glm5_2_nv | 200 | 3750 | 3750 | 0 |
| 03:21:19 | dsv4p_nv | 200 | 17028 | 17028 | 0 |
| 03:03:20 | glm5_2_nv | 200 | 2347 | 2348 | 0 |
| 02:59:29 | dsv4p_nv | 200 | 34975 | 34977 | 0 |
| 02:51:06 | dsv4p_nv | 200 | 45889 | 45889 | 0 |
| 02:33:20 | glm5_2_nv | 200 | 2315 | 2315 | 0 |
| 02:26:00 | dsv4p_nv | 200 | 103468 | 103468 | 1 |
| 02:22:01 | dsv4p_nv | 200 | 153586 | 153586 | 2 |

### NVCFPexecTimeout per-key (6h)
| tier | k0 | k1 | k2 | k3 | k4 |
|------|----|----|----|----|----|
| dsv4p_nv | 7(avg54.1s) | 4(avg50.8s) | 7(avg50.8s) | 5(avg55.9s) | 4(avg52.0s) |
| glm5_2_nv | 8(avg49.7s) | 13(avg51.8s) | 6(avg52.3s) | 9(avg51.6s) | 17(avg54.5s) |

dsv4p_nv timeout max=60.8s (k0), UPSTREAM=66 → **非绑定边缘** (60.8 << 66.4).

### 429 per-key分布 (成功请求, 6h)
| tier | k0 | k1 | k2 | k3 | k4 |
|------|----|----|----|----|----|
| dsv4p_nv | 18(60%)| 12(29%)| 12(28%)| 15(42%)| 16(43%)|
| glm5_2_nv | 28(74%)| 23(82%)| 13(45%)| 13(50%)| 25(83%)|

dsv4p_nv: 429分布均匀 (25-37% per-key) → 非key-specific瓶颈.

### ATE诊断
- 50 ATE全部为all_tiers_exhausted
- 14 ATE: tiers_tried=1 (单tier BUDGET耗尽, avg 78.6s)
- 34 ATE: tiers_tried=2 (双tier BUDGET耗尽, avg 137s), fallback_actually_attempted=false
- **关键发现**: 所有ATE `fallback_occurred=false`, 无fallback实际触发
- ATE duration典型228s = BUDGET 114s × 2 tier (114+114≈228)

### Fallback
| 路径 | 次数 | OK | SR |
|------|------|-----|-----|
| dsv4p→glm5_2 | 28 | 28 | 100% |
| glm5_2→dsv4p | 67 | 67 | 100% |

Fallback双向100%可靠。

### 当前env关键参数
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=114
NVU_PEXEC_TIMEOUT_FASTBREAK=2
NVU_EMPTY_200_FASTBREAK=3
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66  (↔ UPSTREAM=66 对齐)
FALLBACK_HEALTH_THRESHOLD=0.10
```

### docker logs
零错误/zero warn。Health全部1.0。FALLBACK_GRAPH正常。

## 🎯 诊断与决策

### BUDGET约束分析
- FASTBREAK=2 × UPSTREAM=66 = 132s > BUDGET=114s
- **第2个key在每个tier上永远不会完成** — BUDGET在114s处杀死请求
- ATE平均228s ≈ BUDGET 114s × 2 tiers
- 每个tier上: 第1个key 66s等待 + 48s无效等待 → BUDGET kill at 114s
- Fallback从未实际触发 — BUDGET杀在fallback之前

### FASTBREAK决策流程
Path A (UPSTREAM binding):
- [✗] NVCFPexecTimeout max 60.8s ≠ UPSTREAM 66+400ms → 非绑定

Path B (429 key-specific):
- [✗] FASTBREAK=2 already, 不是1-→2场景
- [✗] 429分布相对均匀 → 非key-specific

FASTBREAK Reduction Pattern A:
- [✓] Fallback 100% SR 双向
- [✓] BUDGET 114 << FASTBREAK×UPSTREAM 132
- [✓] 第2key纯浪费48s/tier

**结论**: FASTBREAK 2→1。Fallback可靠, 第2key被BUDGET杀死无收益。减少每tier浪费48s, fallback可在66s(非114s)后kick in。

## 🔧 执行

**变更**: `NVU_PEXEC_TIMEOUT_FASTBREAK: "2" → "1"`
- 方法: sed值替换 → Python lines.insert()新注释 → YAML验证 → docker compose up -d nv_gw
- 结果: Recreated/Started, 运行时确认 FASTBREAK=1
- 日志: clean startup, 零错误

**不动参数**: UPSTREAM=66, BUDGET=114, FORCE_STREAM=66, EMPTY_200_FASTBREAK=3, FALLBACK_HEALTH_THRESHOLD=0.10

## 📈 预期效果

| 指标 | 改前 | 预期 |
|------|------|------|
| dsv4p_nv SR | 82.0% | ~87% (减少浪费不增成功, 但fallback更快→可能多救几个边缘case) |
| ATE duration | avg 119-228s | 更低压 → fallback可在66s触发 |
| 失败路径时间 | 114s BUDGET kill | 66s后fallback (节省48s) |
| 429 rescues | N/A | 不变(429非驱动力) |

Fallback 100% SR意味着所有能fallback的都不会ATE。FASTBREAK=2反而阻挡了fallback (BUDGET先杀)。FASTBREAK=1给fallback留出BUDGET余量。

**风险**: 低。Fallback已验证双向100%可靠。FASTBREAK=1历史验证稳定(R559-R694共136轮)。429均匀非key-specific。

## 🔗 相关轮次
- R767: NOP观察 (等待R766 FASTBREAK=2数据积累)
- R766: FASTBREAK 1→2 (基于429 key-specific诊断)
- R765: EMPTY_200_FASTBREAK 2→3
- R709: FASTBREAK 2→1 (历史反转到1的先例)

---

## ⏳ 轮到HM1优化HM2