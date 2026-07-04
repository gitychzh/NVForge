# R700: HM2→HM1 — dsv4p_nv 跨 model fallback 启用 (FALLBACK_GRAPH)

**日期**: 2026-07-05
**主机**: HM2 (opc2_uname) → SSH 改 HM1 (opc_uname @ 100.109.153.83)
**触发**: HM1 commit 2a338d9 (R699), cron 检测到新提交轮到 HM2

## 背景

R699 (HM2 全链路 bug 审计 + 8 项修复) 部署后, dsv4p_nv 仍持续高失败率.
本 round 通过启用 dsv4p_nv → glm5_2_nv 跨 model fallback 修复该问题.

## 改前数据 (24h, SSH → HM1 logs_db)

### 6h 总体统计
| 指标 | 值 |
|------|-----|
| 总请求 | 190 |
| 成功 | 142 (74.7%) |
| 失败 | 48 (25.3%) |
| avg_ttfb | 17026ms |
| avg_dur | 23868ms |
| max_dur | 90312ms |

### 24h 按模型分组
| 模型 | 总数 | 成功 | 成功率 | avg_ttfb | avg_dur | max_dur |
|------|------|------|--------|----------|---------|---------|
| glm5_2_nv | 109 | 100 | 91.7% | 14207ms | 15173ms | 90312ms |
| dsv4p_nv | 77 | 38 | **49.4%** | 26544ms | 37665ms | 51876ms |
| kimi_nv | 8 | 7 | 87.5% | 4554ms | 9368ms | 27635ms |

### 24h 错误分类
| error_type | model | cnt |
|------------|-------|-----|
| all_tiers_exhausted | dsv4p_nv | 39 |
| all_tiers_exhausted | glm5_2_nv | 9 |
| all_tiers_exhausted | kimi_nv | 1 |

### 失败请求详情 (6h, 全部 502 ATE)
- 全部 `tiers_tried_count=1`, `fallback_occurred=f`
- 全部 `upstream_type=NULL` (未建立上游连接)
- 全部 `fallback_tiers_used={dsv4p_nv}` (单 tier, 无 fallback)
- duration ~50s (2 keys × 25s timeout + FASTBREAK=2)

### docker logs 关键证据
```
[NV-REQ] mapped_model=dsv4p_nv start_tier=dsv4p_nv stream=True tier_chain=['dsv4p_nv'] (no fallback, 3model)
[NV-TIER-FAIL] tier=dsv4p_nv all 5 keys failed: 429=0, empty200=0, timeout=2, other=0, elapsed=50689ms
[NV-ALL-TIERS-FAIL] All 1 tiers failed (ring tiers tried: ['dsv4p_nv']), elapsed=50691ms, ABORT-NO-FALLBACK
```

## 根因分析

`config.py` 的 `FALLBACK_GRAPH` 字典:
- `glm5_1_nv` → `["dsv4p_nv"]` ✅ 有 fallback
- `glm5_2_nv` → `["dsv4p_nv"]` ✅ 有 fallback
- `dsv4p_nv` → **无条目** ❌ 无 fallback (注释掉了 `"dsv4p_nv": ["kimi_nv"]`)

当 dsv4p_nv 的 NVCF function (74f02205) 发生 timeout/empty200 surge 时:
1. 5 个 key 尝试, FASTBREAK=2 在 2 次连续 timeout 后放弃 (省剩余 3 key)
2. `tier_chain=['dsv4p_nv']` 单元素, 无下一 tier 可 fallback
3. peer fallback 到 HM2 也失败 (HM2 同样 NVCF 限制)
4. 最终 `ABORT-NO-FALLBACK` → 502

**关键洞察**: glm5_2_nv (3b9748d8) 成功率 91.7%, avg 15s, 完全可作为 dsv4p_nv 的 fallback.
且 FALLBACK_GRAPH 已有 glm5_2_nv → dsv4p_nv 反向 fallback, 说明跨 model fallback 已被接受.

## 优化方案

**单参数修改**: `config.py` FALLBACK_GRAPH 添加 `"dsv4p_nv": ["glm5_2_nv"]`

```python
# 改前
FALLBACK_GRAPH = {
    "glm5_1_nv": ["dsv4p_nv"],
    "glm5_2_nv": ["dsv4p_nv"],
}

# 改后
FALLBACK_GRAPH = {
    "dsv4p_nv": ["glm5_2_nv"],   # R700: 新增
    "glm5_1_nv": ["dsv4p_nv"],
    "glm5_2_nv": ["dsv4p_nv"],
}
```

### 安全性分析
- **Budget**: TIER_TIMEOUT_BUDGET_S=82 每 tier 独立. dsv4p_nv 82s + glm5_2_nv 82s = 164s < PROXY_TIMEOUT=300s ✅
- **glm5_2_nv 性能**: avg 15s, max 90s. 82s budget 充足 (91.7% 成功) ✅
- **func_health 门控**: fallback 仅在 glm5_2_nv 健康度 ≥ 0.80 时触发 (FALLBACK_HEALTH_THRESHOLD) ✅
- **跨 model 语义**: dsv4p (deepseek) → glm5_2 (zhipu) 思考质量不同, 但优于 502 完全失败 ✅
- **已有先例**: glm5_2_nv → dsv4p_nv 反向 fallback 已运行多轮, 跨 model fallback 被接受 ✅

## 执行步骤

1. **备份**: `cp config.py config.py.bak.R700` ✅
2. **修改**: Python str.replace 精确插入 `"dsv4p_nv": ["glm5_2_nv"],` 条目 ✅
3. **重启**: `docker compose restart nv_gw` (源码 volume-mounted, 无需 rebuild) ✅
4. **验证**: docker logs 确认 `tier_chain=['dsv4p_nv', 'glm5_2_nv']` ✅

## 改后验证 (重启后 ~3min)

### docker logs — fallback 实际触发
```
[02:12:53.8] [NV-REQ] mapped_model=dsv4p_nv tier_chain=['dsv4p_nv', 'glm5_2_nv'] (dynamic fallback, health={})
[02:15:04.5] [NV-FALLBACK] Tier dsv4p_nv all-failed → falling back to glm5_2_nv
[02:15:04.5] [NV-TIER] Starting tier=glm5_2_nv model=z-ai/glm-5.2 func=3b9748d8-1d8...
[02:15:10.8] [NV-SUCCESS] tier=glm5_2_nv k4 succeeded after 2 cycle attempts
[02:15:10.8] [NV-FALLBACK-SUCCESS] Success on fallback tier glm5_2_nv after primary dsv4p_nv failed
```

### DB 验证 (重启后 5 条请求)
| ts | request_model | status | ttfb_ms | dur_ms | tiers_tried | fallback | fallback_tiers |
|----|---------------|--------|---------|--------|-------------|----------|----------------|
| 02:16:40 | dsv4p_nv | 200 | 23026 | 23027 | 1 | f | {dsv4p_nv} |
| 02:15:22 | dsv4p_nv | **200** | 92391 | 92392 | **2** | **t** | **{dsv4p_nv,glm5_2_nv}** |
| 02:14:47 | dsv4p_nv | 200 | 11163 | 11164 | 1 | f | {dsv4p_nv} |
| 02:14:13 | dsv4p_nv | **200** | 56960 | 56960 | **2** | **t** | **{dsv4p_nv,glm5_2_nv}** |
| 02:12:53 | dsv4p_nv | 200 | 35139 | 35140 | 1 | f | {dsv4p_nv} |

**5/5 成功 (100%)**, 其中 **2 个由 glm5_2_nv fallback 救回** (改前必为 502 ATE).

### func_health 追踪
```
health={'74f02205-c7ba-...': 0.667, '3b9748d8-1d85-...': 1.0}
```
dsv4p_nv function 健康度 0.667 (< 0.80 阈值), glm5_2_nv 健康度 1.0 — 系统正确识别了 dsv4p_nv 的不健康状态.

## 预期效果 (稳态)
- dsv4p_nv 49.4% → 预期 ~85-90% (39 ATE 中多数可被 glm5_2_nv 救回)
- 总体成功率 74.7% → 预期 ~90%+
- 失败路径延迟: 50s (ATE) → 50s + 15s = 65s (fallback 成功), 但获得 200 而非 502
- 成功路径无变化 (dsv4p_nv 直接成功仍 ~15-25s)

## 文件修改清单
| 文件 | 机器 | 操作 |
|------|------|------|
| `/opt/cc-infra/proxy/nv-gw/gateway/config.py` | HM1 | FALLBACK_GRAPH 添加 dsv4p_nv→glm5_2_nv |
| `/opt/cc-infra/proxy/nv-gw/gateway/config.py.bak.R700` | HM1 | 备份 |

## 备注
- 改动仅 HM1 config.py (volume-mounted 源码), 不涉及 docker-compose.yml
- HM2 未改动 (铁律: 只改 HM1 不改 HM2)
- 下轮 HM1 可观察稳态效果, 若 dsv4p_nv function 持续不健康可考虑调低 FALLBACK_HEALTH_THRESHOLD 或调整 FASTBREAK

## ⏳ 轮到HM1优化HM2
