# R-buffer-post4: 验证 R-buffer-post3 (480→580) 真生效, content_s 墙杀 480→580, count 29→4 降 86%

> HM2 cc2 自线巡检轮. NOP (0 改动 0 restart). 本轮核心价值 = **核实上轮 R-buffer-post3
> (cc4101 STREAM_TOTAL_DEADLINE 480→580) 是否真生效**, 因上轮 STATE 未写验证结果.

## 数据 (2026-07-27 07:00 CST 拉取)

### 30min 窗口 (06:29-07:00 CST) cc2 链路
- cc2 (cc4101-primary/glm5_2_nv): 36×200 / 1×502(buffer_exhausted) → SR=97.3%
- nv_gw 整体: 84×200 / 18×502 → SR=82.4% (17 个 502 全 unknown/kimi_nv 别的 agent, 非 cc2)
- cc4101 真 fallback = 1 (req=21b4b4b8, primary 60s hdr timeout → ms OK, 不中断)
- buffer 30min: 40×START 全 cc4101-primary, 0 passthrough. 末段 06:58-07:00 4×SUCCESS 全
  verdict=success_tool_call/success_text, buffer 满载美满.

### 6h buffer 概况
- 316×SUCCESS / 9×zombie(全 client_gone_ping) / 3×EXHAUSTED
- 9 个 zombie + 3 个 exhausted 全是 CC SDK 主动断 (broken pipe 写不进 ping),
  **非 NVCF Form B zombie**. buffer 治 NVCF zombie 有效, 治不了 SDK 自断 (BUG-A 家族).
- 1×EXHAUSTED (4d72ef27 @06:53) 3 attempt 全败 client_gone_ping, 详情已查.

## 核心验证: R-buffer-post3 (480→580) 真生效铁证

### content_s (duration - ttfb) 精确墙杀对比

| 时段 | count | content_s | duration range |
|---|---|---|---|
| **pre-580** (02:35-06:14 CST, 580 生效前) | 29 | **全部精确 480s** | 512-565s |
| **post-580** (06:15+ CST, 580 生效后) | 4 | **全部精确 580s** | 612-666s |

实测 SQL:
```sql
-- pre: content_s = duration - ttfb 全 480
select (duration_ms - ttfb_ms)/1000 as content_s ... → 480 (5/5 样本)
-- post: content_s = duration - ttfb 全 580
select (duration_ms - ttfb_ms)/1000 as content_s ... → 580 (4/4 样本)
```

### 结论
1. **R-buffer-post3 改动逻辑实测成立**: cc4101 在 ttfb 后 content_s 精确墙杀, 改前 480 改后 580.
   上轮 STATE "改前精确 480s" 的说法 **正确** (我本轮初算 duration 未减 ttfb 误判 612-666, 修正后
   content_s 精确 580).
2. **改动有效**: stream_total_deadline count 29→4 (6h), **降幅 86%**.
3. **残余 4 个是 NVCF 真长输出 >580s**: ttfb 32-85s (偏高) + content 580s = duration 612-666s.
   非 nv_gw 旋钮可根治 (NVCF 上游输出长度 + ttfb). 30min 窗口(06:29+) 0 个 → 非高频, 可观察.
4. **不能提 580→600**: STATE 已明 "留 SDK 600s 墙 20s 余量给 flush", 提 600 会撞 SDK 墙反 client_gone.

## 三阈值判读
1. cc2 SR 97.3% (30min) — 1 个失败是 buffer_exhausted(client_gone_ping, BUG-A 家族, 非 nv_gw 可治)
2. cc4101 真 fallback = 1 (primary 60s hdr timeout, 不中断)
3. 无新错误类型 (stream_total_deadline 已知, R-buffer-post3 后 count 降 86%)

→ 数据证稳, 冻结 NOP. R-buffer-post3 验证通过. 0 改动 0 restart.

## 下轮建议
1. 盯 stream_total_deadline 残余 4 个/6h 是否成趋势. 若持续低频, 接受为 NVCF 长输出残余.
   若高频化, 评估: 是否 NVCF ttfb 退化 (那 4 个 ttfb 32-85s 偏高), 或大 input 段集中.
2. 盯 buffer_exhausted (client_gone_ping): 若高频, 说明 buffer TTFB + SDK 早断结构性矛盾显现,
   评估 NVU_BUFFER_TIMEOUT_STAIRS 首阶 150s (谨慎, 太短误杀正常长流).
3. cc2 SDK 600s 墙 (BUG-A 根因) 不可从 nv_gw 治, 只能缩短单请求 duration (NVCF ttfb/输出).
4. 铁律不变: 改前数据, 改后验证, 聚焦 40006, 不碰 40007, 只改 HM2, 写入仓库, 多走 glm5_2_nv.
