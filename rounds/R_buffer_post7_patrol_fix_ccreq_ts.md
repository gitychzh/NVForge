# R-buffer-post7 (hm2_cc2): 巡检 NOP + 发现 cc_requests.ts 非单调时序

> 2026-07-27 09:04 CST, HM2 only, 新 session 接棒 (STATE 停 R-buffer-post6).
> 本轮: NOP 巡检, 0 改动 0 restart. 实质产出 = 发现 cc_requests.ts 非单调时序, 不能做精确窗口查询.

## 数据 (本轮 09:02-09:04 CST 实测)

### nv_gw 30min 整体 (单调时序, 可信)
- nv_gw 整体: 61×200 / 6×502 / 1×499 → SR=89.7% (61/68)
- cc2 (cc4101-primary/glm5_2_nv): 32×200 / 1×499 → **SR=32/33=97.0%**
  - 唯一非200: 1×499 `client_gone_during_flush` = BUG-A 家族 (cc4101 SDK ~131s 客户端首字节墙)
- unknown/kimi_nv (别的agent): 26×200 / 6×502 (2 IncompleteRead + 3 all_tiers_exhausted + 1 zombie) → 非 cc2 责任

### cc4101 真 fallback = 1 (08:57:11)
```
[08:57:11.1] [PRIMARY-FAIL] primary timeout status=0 after 60063ms: header/ttfb timeout after 60s
[08:57:11.2] [PRIMARY-FAIL-SKIP-CIRCUIT] 60063ms < chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit
[08:57:11.2] [PRIMARY-FAIL] -> trying fallback ms_gw glm5_2_ms
[08:57:14.6] [FALLBACK-OK] fallback succeeded after 3356ms
```
- 触因: NVCF ttfb>60s 撞 cc4101 `PRIMARY_HEADER_TIMEOUT=60`, cc4101 主动切 ms, 1×/30min 稀疏偶发
- post6 是 0 fallback, 本轮 1 → 轻微波动, 非持续退化
- fb 3356ms 救回, cc2 无感 (那一条请求最终 200)

### cc_requests 6h error_type (累积, 非精确窗口)
- 527×空(成功) / 49×stream_total_deadline / 8×client_gone_mid_stream
- stream_total_deadline 小时分布: 02h=4 / 03h=9 / 04h=8 / 05h=8 / 06h=4 / 07h=8 / 08h=8 → 范围 4-9/h 波动内部, 无骤升

## 三阈值判稳
| 阈值 | 实测 | 判定 |
|------|------|------|
| cc2 SR | 32/33=97.0% (1×BUG-A 499) | ⚠ 略降于 post6 100% 但属 BUG-A 已知局限 |
| cc4101 真 fallback | 1 (NVCF ttfb>60s 偶发, fb 救回) | ⚠ 稀疏偶发 |
| 无新错误类型 | 仅 client_gone_during_flush(BUG-A) + unknown 502(别的agent) | ✓ |
→ 无 nv_gw 退化 / 无新错误 / 1×499+1×fb 均已知偶发项 → **冻结 NOP, 0 改动 0 restart**

## 关键发现: cc_requests.ts 非单调时序 (查询方法论修正)

本轮实测一个查询陷阱, 下轮起必改:

```sql
-- 错误查询 (30min 窗口, 期望抓最近半小时)
select error_type, count(*) from cc_requests
where ts > now() - interval '30 minutes' group by 1 order by 2 desc;
-- 实际返回: 49×stream_total_deadline (min ts=02:35, max ts=08:49, 跨度6h!)
```

**根因**: cc_requests 表的 ts 列**不按时间单调递增**, 是按"请求完成/批次记录"写入的.
- `min(ts)=01:47`, `max(ts)=09:04`, 跨度 8 小时全混进 30min 窗口
- 所以 cc_requests 用 `ts > now()-30min` 抓的是"最近 30min 内写入的行"非"最近 30min 发生的请求"
- 6h 累积的 49×stream_deadline / 8×client_gone 全被这个伪 30min 窗口吃进来, 误以为 30min 真有 49 个

**修正**: cc_requests 做时序窗口查询**不可靠**, 改用:
1. **时序窗口成功率/SR**: 用 `nv_requests.created_at` (单调时序, 按 caller 过滤 cc2), 这是 cc2 链路真相
2. **stream_total_deadline 频次**: 用 hourly 分桶 `date_trunc('hour', ts)` 看分布 (本轮验证此查法可信, 4-9/h 波动)
3. **绝对不要**用 `cc_requests.ts > now()-30min` 做精确窗口计数

**post6 报的"47×/6h=7.8/h"** 实际是 6h 累积正确 (那条查询是 6h 窗口 + hourly 分桶, 无误).
本轮"伪 30min = 49"是我第一遍查询写错窗口语义被坑, 已用 nv_requests 重证真相.

## env 快照 (无漂移, 同 post6)
```
nv_gw: UPSTREAM_TIMEOUT=90 TIER_TIMEOUT_BUDGET_S=180 TIER_COOLDOWN_S=180 KEY_COOLDOWN_S=60
       MIN_OUTBOUND_INTERVAL_S=10 NVU_BUFFER_CALLERS=cc4101-primary NVU_BUFFER_MAX_RETRIES=3
       NVU_BUFFER_TIMEOUT_STAIRS=150,200,200 NVU_BUFFER_TOTAL_DEADLINE_S=580
       NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150 KEY_AUTHFAIL_COOLDOWN_S=60
cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=580 PRIMARY_HEADER_TIMEOUT=60 UPSTREAM_IDLE_TIMEOUT=150
        UPSTREAM_TIMEOUT=130 PRIMARY_UPSTREAM_MODEL=glm5_2_nv
/health: nv_default_model=glm5_2_nv ✓ (三处一致)
```
容器: nv_gw Up 8h RC=0 restarts=0 / cc4101 Up 3h / ms_gw Up 5d (热备未碰) / logs_db Up 10d

## R2192 三任务进度 (无变化)
- 任务1 (cc4101 透传 cache_control): ✅ 落地持续生效 (cache_read 历史验证 38.8%)
- 任务2 (nv_gw zombie body dump probe): ✅ 终判完成 (R-buffer-post1: 440 dump, 55 zombie 全 cm/oc/th=ABSENT, 推测A证伪)
- 任务3 (路径B zombie 内部 key 重试): ⚠ 被 R-buffer 部分取代暂搁置 (buffer-then-flush + 同 key 重试已覆盖 cc2 Form B 根治)

## 下一轮该做什么
1. 继续巡检. 盯 cc2 (cc4101-primary) SR (用 nv_requests.created_at 查, 别用 cc_requests.ts).
2. 盯 cc4101 真 fallback: 持续 >1/30min (如 3-5/h) 才算退化, 1×/30min 偶发可接受.
3. **新方法论**: cc_requests 只做 6h 累积或 hourly 分桶, 不做精确 30min 窗口计数 (ts 非单调).
4. 盯 stream_total_deadline hourly (4-9/h 内部波动 = 接受; 骤升查 NVCF ttfb 退化).
5. 盯 client_gone_during_flush/mid_stream (BUG-A 家族, 当前不治, 接受 ~1-2/h).
6. kimi_nv/unknown agent 502: 非 cc2 责任, 不越权改.
7. 长驻机制: 30min touch heartbeat (watchdog 15min); 改 .py 触发 R-guard; auto-compact 后从 STATE 接棒.
8. 铁律: 改前数据, 改后验证, 聚焦 40006, 不碰 40007, 只改 HM2, 写入仓库, 多走 glm5_2_nv 少 fallback.

## 本轮产出小结
0 改动 / 0 restart / 0 行 gateway 源码变动. 实质产出 = 1 个查询方法论修正 (cc_requests.ts 非单调,
下轮起改用 nv_requests.created_at 做 cc2 时序窗口). 链路稳定 (SR 97% 被唯一 1×BUG-A 499 拉低,
非 nv_gw 退化). 三阈值无骤变 → 冻结 NOP.
