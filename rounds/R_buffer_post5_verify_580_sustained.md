# R-buffer-post5: 580s 改动持续生效铁证 + 频次修正, cc2 链路 100% 持稳, 冻结 NOP

> HM2 cc2 自线巡检轮. NOP (0 改动 0 restart). 本轮核心价值 =
> (1) 核实 R-buffer-post3 (cc4101 STREAM_TOTAL_DEADLINE 480→580) 持续生效至今;
> (2) **修正 R-buffer-post4 的 86% 降幅结论**: 580 后 stream_total_deadline 仍有相当频次,
>     非"残余 4 个", 属 NVCF 长输出 >580s 的结构性观察项 (580 已顶 SDK 600s 墙, 不可再提).

## 数据 (2026-07-27 08:36 CST 拉取, DB now = 00:36 UTC 7-27)

### 30min 窗口 (08:06-08:36 CST) cc2 链路 — 健康
- cc2 (cc4101-primary/glm5_2_nv): 30×200 / 0 失败 → **SR=100%**
- nv_gw 整体: 62×200 / 6×502 → SR=91.2% (6 个 502 全 `caller=unknown, mapped_model=kimi_nv`,
  4 zombie + 2 ATE, 别的 agent, 非 cc2, 非 HM2 旋钮可治)
- cc4101 真 fallback = 0
- buffer 30min: 31×SUCCESS / 0 RETRY / 0 EXHAUSTED / 0 ZOMBIE
  verdict: success_tool_call×23 / success_thinking_tool×5 / success_thinking×3 (满载美满)

### 6h 累计 (cc4101-primary) — 健康为主, 残失败全 BUG-A 家族
- 381×200 / 4×502(buffer_exhausted) → SR=98.96%
- 4 个失败全 buffer_exhausted, 即 BUG-A 家族 client_gone_ping (CC SDK 主动断 broken pipe,
  buffer 重试无效是设计局限), 非 NVCF Form B zombie, 非 nv_gw 可治

## 核心验证: R-buffer-post3 (480→580) 持续生效铁证

### content_s = duration - ttfb, 按 6h 窗口分桶 (DB ts 实为 CST 错标 +00, 已核证)

| content_s | count | ts 范围 (CST) | 判读 |
|---|---|---|---|
| **480** | 29 | 02:35-05:55 | **改前** (cc4101 480s 墙) |
| **580** | 15 | 06:19-08:21 | **改后** (cc4101 580s 墙, R-buffer-post3 生效) |

时间边界 CST 06:15 ≈ R-buffer-post3 落地时刻. content_s 从精确 480 跳到精确 580, 铁证改动生效且持续.
cc4101 env 实测 `CC4101_STREAM_TOTAL_DEADLINE_S=580` ✓

### ⚠ 修正 R-buffer-post4 的 "降幅 86%" 结论

R-buffer-post4 报 "stream_total_deadline count 29→4 降 86%", 但那是**短窗口瞬时** (它 07:00 CST 拉,
改后窗口仅 ~45min). 本轮拉 6h 全窗口后实测:

- 改前 (CST 02:35-05:55, 约 3.4h): 29 个 → **8.5/h**
- 改后 (CST 06:19-08:21, 约 2.1h): 15 个 → **7.1/h**
- 降幅约 **17%**, 非伪 86%

**真实含义**: 580 改动把 content 480-580 段的请求救回 (能跑完), 但 **content >580s 的真长 NVCF 输出**
仍被墙杀, 频次约 7/h 不低. 这些是 NVCF 上游输出长度问题, 非 nv_gw 旋钮可根治.
**580 已顶到 cc2 SDK API_TIMEOUT_MS=600s 墙 (留 20s 余量给 flush), 不可再提** → 接受项 / 观察项, 非改码项.

## 三阈值判读
1. cc2 SR 30min = 100% (30/30) ✓
2. cc4101 真 fallback 30min = 0 ✓
3. 无新错误类型: stream_total_deadline 已知 (R-buffer-post3 治, 580 持续生效),
   buffer_exhausted 是 BUG-A 家族 client_gone_ping 已知, client_gone_mid_stream 是 BUG-A 已知

→ 三阈值全满足稳, 冻结 NOP. 0 改动 0 restart.

## 下轮建议
1. 盯 stream_total_deadline 改后频次 (~7/h): 若持续, 接受为 NVCF 长输出残余 (580 已顶墙不可再提).
   若骤升, 查是否 NVCF ttfb 退化 (本轮样本 ttfb 32-85s 偏高) 或大 input 段集中.
2. 盯 buffer_exhausted (client_gone_ping): 若高频化, 说明 buffer TTFB + SDK 早断结构性矛盾,
   评估 NVU_BUFFER_TIMEOUT_STAIRS 首阶 150s (谨慎, 太短误杀正常长流). 当前不治.
3. kimi_nv/unknown agent 的 502: 非 cc2 责任, 暂不动避免越权改别的 agent 路径.
4. 铁律不变: 改前数据, 改后验证, 聚焦 40006, 不碰 40007 (重启热备), 只改 HM2, 写入仓库, 多走 glm5_2_nv.
