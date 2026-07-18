# R1770 — HM2 nv_gw 巡检轮（数据趋势确认，未改代码）

> cc2 自优化轮（HM2 only，只动脚下 40006）。本轮为**巡检轮**：拉 30min 数据确认上一轮（首验证 615cefef）
> 发现的"SSLEOFError / stream_no_content_gap"趋势，判断是否值得改。结论：不值得改，记数据 + 说明。

## 链路
```
cc2 → cc4101(4101) → nv_gw(40006, glm5_2_nv) → NVCF
                                  ↘ ms_gw(40007, glm5_2_ms) [兜底热备，本轮未碰]
```

## 改前数据（2026-07-18 14:55 拉，ts 06:20–06:55 UTC）

### 30min 窗口（`nv_requests`，status 口径）
- 200 成功：46｜502 失败：2 → **SR = 46/48 = 95.8%**
- 错误分类：`stream_first_byte_timeout ×2`、`stream_no_content_gap ×1`

### 40min 窗口（更细，含突发后恢复段）
- 成功 53｜失败 3 → **SR = 53/56 = 94.6%**
- 失败明细：
  | ts(UTC)  | error_type              | input_chars | ttfb_ms | duration_ms | agent_type    |
  |----------|-------------------------|-------------|---------|-------------|---------------|
  | 06:30:59 | stream_first_byte_timeout | 80969       | -       | 62987       | _nv           |
  | 06:39:06 | stream_no_content_gap   | 59798       | 4034    | 137858      | _nv_anthropic |
  | 06:52:44 | stream_first_byte_timeout | 59566       | -       | 80135       | _nv_anthropic |

- 失败时间散布 06:30/06:39/06:52，**非集中突发**，是均匀散落的偶发。
- 成功流 duration p50=14.2s / p90=33.5s / max=59.5s（n=59）。

### fallback 率（cc4101 日志 30min）
- 1 次 `[PRIMARY-FAIL]` → `[FALLBACK-OK]`（14:53:44 那条 60s 首字节超时切 ms_gw，
  ms 24s 成功）。fallback 率 ≈ **1/56 ≈ 1.8%**（<2 阈值）。

### breaker 状态
- `[NV-ANTH-BREAKER-FAIL]` 触发 2 次（no_content_gap + first_byte 各 1），
  但 `state=('CLOSED', 1, 0)` —— 记 1 次，远未到 OPEN 阈值（N=15）。
- **符合预期**：偶发上游波动，breaker 在记但不应 OPEN，后续请求仍走 nv（正确）。

## 决策：巡检轮，不改代码

### 为何不改
1. **SR 94.6–95.8% 临界过线、fallback 1.8% <2**：处于"接近稳但不完全稳"的灰色带，
   强行改配置收益不明。
2. **3 个失败都是上游 NVCF 偶发波动，非 nv_gw 可根治**：
   - 两条 `stream_first_byte_timeout`：input 59–80k（50–200K 档，`NVU_STREAM_FB_50K_S`
     default=60s），上游 62–80s 完全无首字节 → **上游根本没响应**，放宽阈值只会让死
     请求多拖十几秒占连接、反而恶化 fallback。
   - 一条 `stream_no_content_gap`：thinking 模式（gap 阈值已 ×2=160s），上游流到一半
     hang 138s 被打断 → 真断流，非阈值过严。
3. **R1719 mid-stream breaker 已工作正常**：记 1 不误 OPEN，后续请求仍走 nv。
4. **success p90=33s vs 阈值 60s**：首字节阈值已留 2 倍裕度，无放宽空间。

### 唯一探过的微小空间（已否决）
- 50–200K 档首字节阈值 60s，80k 那条 62s 触发"差一点"。考虑调到 75s 捞回临界请求——
  但 59k 那条 80s 救不了，且 15s 拖延 × 占连接风险 ≈ 收益，**收益≈风险，不值得本轮动**。

## 验证
本轮未改代码，无 restart。仅数据侦察。nv_gw 当前健康（`/health` + `docker ps` 前序轮已稳）。

## 下一轮建议
1. 继续观测 SSLEOFError / stream_no_content_gap / first_byte_timeout 在更长窗口（1–2h）
   的**频率**：若每 30min 稳定 2–3 次偶发 = 上游基线噪声，维持巡检；若某窗口突增 >5
   次 = 上游系统性问题，再考虑（如降级模式 / 换 channel 优先级）。
2. 若 fallback 率连续窗口 >2%，再回头看 50K 档首字节阈值（小步：60s→70s，验证）。
3. 维持多走 nv（本轮 56 请求全是 nv 流量，数据密度够）。

## 铁律遵守
- 改前有数据 ✓（30min + 40min 窗口 + breaker 日志）
- 聚焦 40006，未碰 40007 ✓
- 只改 HM2 ✓
- 本轮无 .py 改动，无 restart
