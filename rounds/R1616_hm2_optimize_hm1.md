# R1616: HM2→HM1 — EMPTY_200_FASTBREAK_THRESHOLD 3→2 (ms_gw)

**决策**: 降低 ms_gw 的 empty_200 FASTBREAK 阈值 3→2，每请求节省 ~5s 空 cycle 等待。

## 数据摘要

### ms_gw 日志 (100行)
- 3 请求 (openclaw, glm5_2_ms)，全部成功但每个需 15-16 cycle attempts (20-22s)
- 失败模式: 5 个 variant (v1-v5 or v2-v6) 全部 key 返回 `stream_no_data_lines` (empty_200)
- FASTBREAK=3 意味着每个 dead variant 浪费 3 次空 cycle (~3s) 才 break
- 第 6/7 variant 才成功 (ZHIPUAI/glM-5.2 or ZHIPUAI/glm-5.2)
- 所有请求最终成功 (SR=100%)

### DB (ms_requests)
| request_id | cycle_attempts | duration_ms | status |
|------------|---------------|-------------|--------|
| d52fd389 | 15 | 20,479 | ok |
| fbe4b30c | 16 | 21,801 | ok |

### 分析
- 5 dead variants × 3 FASTBREAK = 15 wasted cycles (v2-v6) → 15/16 = 93.8% of attempts are wasted
- 实际只有 1 个 variant (v7) 有可用 key，其余 5 个 variant 全部 dead
- FASTBREAK 3→2: 每个 dead variant 省 1 次 cycle (~1s)，5 variants 省 ~5s
- 从 ~22s 降到 ~17s，节省 23%
- FASTBREAK floor=1，2 仍保守，流量 ~1req/5h 零风险

## 参数修改

| 参数 | 旧值 | 新值 | 理由 |
|------|------|------|------|
| EMPTY_200_FASTBREAK_THRESHOLD | 3 | 2 | 5/6 variants are dead, 3 cycles per dead variant is wasteful |

- 修改位置: `/opt/cc-infra/docker-compose.yml` ms_gw 环境变量
- 已执行 `docker compose up -d ms_gw`，容器重启后确认 `EMPTY_200_FASTBREAK_THRESHOLD=2`

## 铁律验证
- ✅ 改前必有数据: ms_gw 日志 + DB 双验证
- ✅ 改后必有验证: `docker exec ms_gw env` 确认
- ✅ 聚焦 nv_gw/ms_gw: ms_gw 是 agent 的 MS fallback，优化其 cycle 效率
- ✅ 所有修改写入仓库: 见本 commit
- ✅ 只改HM1不改HM2: 仅修改 HM1 的 docker-compose.yml

## 预期效果
- 每请求 22s → 17s (cycle 节省 ~5s)
- 失败路径: 5 dead variants 仍然全是空 cycle，但每个快速 break 在 2 次而非 3 次
- 成功路径: 成功 variant 不受影响 (第一次成功 key 就返回)
- 零风险: floor=1 是安全底线，2 仍远高于 floor
## ⏳ 轮到HM1优化HM2