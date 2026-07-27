# R-buffer-post6 (hm2_cc2): NOP 巡检 + 修正 post5 content_s 铁证查询 bug

> **本轮性质**: NOP 巡检轮 (三阈值全满足稳冻结). 本轮唯一实质产出 = 发现并修正 post5 STATE 里
> 一个**真实数据认知 bug**: post5 报的 "content_s 480→580 时间边界铁证" 查询对 cc2 链路恒返回 0 行
> (cc4101-passthrough 路径的 nv_gw 不记 ttfb_ms), 实际查的是 unknown/kimi_nv 流量. 结论方向不变但
> 铁证论据需以 cc_requests.stream_total_deadline 取代.

## 改前数据 (30min + 6h, 本轮实测 2026-07-27 08:46-08:50 CST)

### 30min (00:16-00:46 UTC)
- nv_gw 整体: 44×200 / 8×502 → SR=84.6%
- **cc2 (cc4101-primary/glm5_2_nv): 27×200 / 0 失败 → SR=100%** ✓
- unknown/kimi_nv: 17×200 / 8×502 (4 zombie + 3 ATE + 1 IncompleteRead, 别的 agent, 非 cc2, 非 HM2 旋钮可治)
- cc4101 真 fallback = 0 ✓
- buffer: 27×SUCCESS / 0 EXHAUSTED (全 1 attempt, verdict=success_tool_call / success_thinking_tool / success_thinking)

### 6h
- cc2 nv_requests: 383×200 / 3×buffer_exhausted → SR=99.2% (3 个全 BUG-A 家族 client_gone_ping, buffer 重试无效是设计局限)
- cc_requests error_type: 512×空(成功) / 47×stream_total_deadline / 8×client_gone_mid_stream
- stream_total_deadline 6h 47× → 7.8/h (post5 报 7.1/h, 范围 4-9/h 波动一致, NVCF 长输出残余接受项)
- client_gone 6h 8× (历史低位)

## 本轮关键发现: post5 content_s 铁证查询 bug (必须下轮起纠正)

### post5 的错误论据
post5 STATE 写:
> "content_s (duration-ttfb) 按 6h 分桶: 480 段 29 个 ts CST 02:35-05:55 (改前), 580 段 15 个
> ts CST 06:19-08:21 (改后), 时间边界 CST 06:15 ≈ R-buffer-post3 落地, content_s 从精确 480 跳
> 精确 580, 铁证持续生效"

### 本轮实测证伪
```
cc2 (cc4101-primary) 6h 200 样本: 383 行, has_ttfb=0 (ttfb_ms 全空)
unknown (kimi_nv)     6h 200 样本: 367 行, has_ttfb=367 (全有)
```
→ **cc4101-passthrough 路径 (cc2) 的 nv_gw 记 duration_ms 但不记 ttfb_ms**; `unknown` caller 走
nv_gw-native 路径才记 ttfb_ms. 所以 post5 的 `duration_ms - ttfb_ms` 对 cc2 恒为 0 行,
"29 个 480 / 15 个 580" 实际是 **unknown/kimi_nv 流量**, 不是 cc2 流量. 铁证论据失效.

### 但结论方向不变 (本轮用对的数据重证)
cc4101 env `CC4101_STREAM_TOTAL_DEADLINE_S=580` ✓ 本轮实测持续生效 (改前 480 → post3 改 580).
真正的 cc2 链路 580 墙铁证应来自 **cc_requests.stream_total_deadline** (这是 cc4101 侧记的,
passthrough 路径适用):
- 6h 47× → 7.8/h, 范围 4-9/h 波动, 无骤升骤降 → 580 墙持续工作, NVCF 长输出 >580s 残余接受.
- post5 报 7.1/h 与本轮 7.8/h 在同范围 → 接受项判定不变.

### 下轮起改用查询 (替代 post5 失效的 content_s 桶)
```sql
-- cc2 580 墙铁证 (正确路径: cc_requests, 非 nv_requests content_s)
select date_trunc('hour', ts) as hr, count(*)
from cc_requests
where ts > now()-interval '6 hours' and error_type='stream_total_deadline'
group by 1 order by 1;
```

## 三阈值判稳
| 阈值 | 30min 实测 | 判定 |
|------|-----------|------|
| cc2 (cc4101-primary) SR | 27/27 = 100% | ✓ 满足 |
| cc4101 真 fallback | 0 | ✓ 满足 |
| 无新错误类型 | 仅 buffer_exhausted(BUG-A家族) + unknown/kimi_nv 502(别的agent) | ✓ 满足 |
→ 三阈值全满足 → **冻结 NOP, 0 改动 0 restart**

## nv_gw env 快照 (无漂移, 同 post5)
- `UPSTREAM_TIMEOUT=90 TIER_TIMEOUT_BUDGET_S=180 TIER_COOLDOWN_S=180`
- `NVU_BUFFER_CALLERS=cc4101-primary NVU_BUFFER_MAX_RETRIES=3 NVU_BUFFER_TIMEOUT_STAIRS=150,200,200 NVU_BUFFER_TOTAL_DEADLINE_S=580`
- `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv NVU_EMPTY_200_FASTBREAK=3`
- cc4101: `CC4101_STREAM_TOTAL_DEADLINE_S=580` ✓ (post3 改, 持续生效)

## 容器状态
- nv_gw: Up (RC=0, restarts=0), 本轮无 restart
- cc4101: `CC4101_STREAM_TOTAL_DEADLINE_S=580` ✓, `UPSTREAM_IDLE_TIMEOUT=150`
- ms_gw: Up (重启热备就位, 未碰)

## R2192 三任务进度 (无变化)
- 任务1 (cc4101 透传 cache_control): ✅ 落地持续生效
- 任务2 (zombie body dump probe): ✅ 终判完成 (440 dump, 55 zombie 全 cm/oc/th ABSENT, 推测 A 证伪)
- 任务3 (路径B zombie 内部 key 重试): ⚠ 被 R-buffer buffer-then-flush + 同 key 重试部分取代, 暂搁置 (spec+骨架暂存)

## 下一轮该做什么
1. 继续巡检. 盯 cc2 (cc4101-primary) SR 是否保持 100%, buffer 是否 0 EXHAUSTED, cc4101 fb 是否 0.
2. **改用 cc_requests.stream_total_deadline** 查 580 墙铁证 (post5 的 content_s 桶对 cc2 失效).
3. 盯 stream_total_deadline 频次 (~7-8/h): 持续则接受为 NVCF 长输出残余 (580 已顶 SDK 600s 墙
   不可再提); 骤升则查 NVCF ttfb 退化或大 input 段集中.
4. 盯 client_gone (BUG-A 家族, buffer 重试无效是设计局限, 当前不治).
5. kimi_nv/unknown agent 的 502: 非 cc2 责任, 不动避免越权.
6. 铁律: 改前数据, 改后验证, 聚焦 40006, 不碰 40007 (重启热备), 只改 HM2, 写入仓库, 尽量多走
   glm5_2_nv 少 fallback.
