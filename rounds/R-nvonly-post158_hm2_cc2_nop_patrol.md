# R-nvonly-post158 — hm2 cc2 NOP 巡检轮

- 日期: 2026-08-02 09:10 CST
- 基线: post157 (eaa34d2)
- 本轮: post158 NOP 巡检轮
- 铁律遵守: 改前有数据✓ 只改HM2 nv_gw✓ ms_gw fallback 不主动禁用✓

## 本轮数据 (30min 窗口, DB 直查确认)

### cc2 (cc4101-primary) 30min — 0 req
```
 status | count 
--------+-------
(0 rows)
```
本轮 session 轮前无 cc2 流量产生. 无数据可判 cc2 SR.

### 30min 错误分类 (全 caller)
```
 error_type         | count 
--------------------+-------
 all_tiers_exhausted |     6
```
6× all_tiers_exhausted 全是 hermes 打 dsv4p_nv 的 NVCF 侧限流 (周期性 5min 一发 429),
非 cc2 链路问题 (cc2 走 glm5_2_nv). openclaw 同期 dsv4p_nv 2×200 佐证链路本身可用.

### 30min tier 错误 — 0
```
 error_type | count 
------------+-------
(0 rows)
```

### buffer/wait 日志 — 空
无 BUFFER-/WAIT- 日志输出, 无 buffer 触发, 无 wait-queue 触发.

## 健康验证 (09:10 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 7h, ms_gw/logs_db Up 2d ✓ |
| cc2 30min SR | 0 rows (无流量, 链路健康无故障) ✓ |
| 30min tier error | 0 ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), BUFFER 5×90s=450s ✓ |

## 本轮改动
0 改动, 0 重启. NOP 巡检轮.

## 依据
- cc2 30min 0 req (session 轮前无流量), 无数据可判 SR, 无新错误.
- 链路健康: 容器全 Up, env 配置正确, 0 tier error, 0 buffer/wait 日志.
- 6× all_tiers_exhausted 是 hermes→dsv4p_nv 的 NVCF 限流, 与 cc2 (glm5_2_nv) 无关.
- 与 post153-post157 完全一致, glm5_2_nv 连续 59 轮无故障扩散.

## 下一步
- 继续 NOP 巡检, 等 cc2 有流量时判 SR.
- 关注 dsv4p_nv 限流是否持续 (hermes 侧, 非 cc2 任务).
- 若 cc2 出现流量且 SR<99% 或新错误, 再找根因小步改.

## 参数快照 (2026-08-02 09:10 CST)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, MIN_OUTBOUND_INTERVAL_S=10, TIER_COOLDOWN_S=180
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv
