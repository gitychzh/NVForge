# R2155 (hm2_cc2): 复盘验证 R2154 cc4101 动态 header timeout 落地

> 本轮**不改代码**, 只做 R2154 (CC 监督者直接落地, commit ab66ba6) 的复盘验证 + 数据记录.
> 职责边界: cc4101 适配层是 nv 链一部分 (可改但本轮不改), nv_gw(40006) 源码 / ms_gw(40007) 源码 / HM1 全不碰.

## 1. 上一轮(=R2154, 监督者做)发生了什么

- 监督者发现 cc4101 `upstream.py` 的 R1420 动态 header timeout 早已存在, 只是分档太粗
  (旧 4 档: >350K→120s, >200K→120s, >50K→75s, else→25s). 旧 50-200K 一档全给 75s 太粗,
  实测 60-150K 段 p99 ttfb 141-246s 全被 75s 误杀滑 ms_gw fallback.
- 监督者直接精化分档表 4→6 档 (HM2 only, commit ab66ba6, 已 push):
  - PRIMARY: `<30K→25s / 30-50K→40s / 50-90K→150s / 90-150K→160s / 150-350K→120s / >350K→120s`
  - FALLBACK 对齐 6 档: `50-350K→120s / 30-50K→60s / else→25s`
  - 倒挂规避铁律: cc4101 header_timeout > nv_gw first-byte deadline, 让 nv_gw 用满自己检测
    主动 break 发 err_chunk (干净 Scenario A, CC 重试), cc4101 不抢先断切 ms.
- bind-mount `/opt/cc-infra/proxy/cc4101/gateway/upstream.py`, `docker compose restart cc4101` 已做.

## 2. 本轮验证方法 (改前必有数据 → 验证 R2154 已落地 + 效果)

### 2.1 确认新分档表在位 (grep R2154 命中)
```
212:            # R2154: 精化 R1420 分档表 4->6 档. 旧 50-200K 一档全给 75s 太粗, 实测 60-150K
226:                _hdr_to = 120  # R2154: 150-200K 新拆档, 沿用 120s 对齐 chain budget
228:                _hdr_to = 160  # R2154: 90-150K 档. nv_gw first-byte 60s 先 break 发 err_chunk,
232:                _hdr_to = 150  # R2154: 50-90K 档. nv_gw first-byte 60s + 90s 余量. 实测 p99 141s,
235:                _hdr_to = 40   # R2154: 30-50K 新拆档. nv_gw first-byte 20s + 20s 余量. 小请求
325:            # R2154: fallback 分档对齐 primary 6 档 (ms_gw chain budget 同 120s). ms_gw 不走 nv
```
✅ 新 6 档表在 `_try_primary` (212-235行) 和 `_try_fallback` (325行) 内确认在位.

### 2.2 cc4101 StartedAt 确认 = R2154 restart 后
- `docker inspect cc4101 --format '{{.State.StartedAt}}'` = `2026-07-21T05:28:51.920960268Z`
  (UTC) = 本地 CST 13:28:52. 与 STATE 记录一致.
- 日志确认: `[13:28:52.4] [START] cc4101 listening on 0.0.0.0:4101 (role=cc4101)`.

### 2.3 cc4101 6h 日志按 R2154 restart 点 (13:28:52) 硬切分 (awk 时间戳比较)

| 指标 | R2154 前 (08:15-13:28:52, ~5h13min) | R2154 后 (13:28:52-14:14, ~45min) |
|---|---|---|
| FALLBACK-OK (滑 ms_gw) | 83 | **0** |
| 75s 抢先断 (header/ttfb timeout after 75s) | 162 | **0** |

**R2154 旧 bug (75s 误杀) 完全归零.** 新档 150s/160s 未产生新抢先断 (0 PRIMARY-FAIL in post 窗口).

### 2.4 nv_gw 侧 30min 巡检 (R2154 后纯窗口)
```
nv_requests 30min:  status=200 → 42, status=502 → 7   (SR = 85.7%)
  error_type (502): all_tiers_exhausted → 6  (NVCF 侧 5 key 全 429/超限, 非 cc4101 误杀)
cc4101 30min: FALLBACK-OK = 0, PRIMARY-FAIL = 0, 75s timeout = 0
```
✅ 重点验证项达成: 90-150K / >150K 档不再出现卡 75s 的 fallback. 6h 验证期的"75s 类归零"成立.

### 2.5 90min 混合窗口 (含 R2154 前后) 参考
- nv_requests 90min: 200→170, 502→26, SR = 86.7% (混合窗口, R2154 前贡献了部分 fallback+慢成功).

## 3. 验证结果 (本轮结论)

1. **R2154 已正确落地**: 6 档表在 `_try_primary`/`_try_fallback` 内, cc4101 StartedAt 与 restart 点对齐.
2. **旧 75s 误杀类归零**: R2154 后 45min 窗口 0 次 75s 抢先断, 0 次 fallback (vs 改前 5h 内 162 次 75s 误杀 + 83 次 fallback).
3. **新档 150s/160s 未产生新抢先断**: post 窗口 0 PRIMARY-FAIL, 倒挂规避铁律生效.
4. **nv_gw 侧剩余错误是 NVCF 上游类** (all_tiers_exhausted, 5 key 全 429/超限), 非 cc4101 误杀导致, 非 nv_gw 旋钮能修, 不影响"R2154 消除 75s 误杀"结论.
5. **0 真中断**: R2154 前 83 次 fallback 全被 ms_gw 兜住成功, R2154 后 0 fallback. 用户诉求 "可以报错但不能让 cc2 中断" 持续满足.
6. **长期目标 "撤 40007" 仍需后续轮**: all_tiers_exhausted 时仍需 ms_gw 兜, R2154 只消除了"cc4101 自己误杀"那部分. 进 R2155+ nv_gw 动态 absolute_cap + zombie content ratio 方案的前提 (R2154 验证稳) 已部分满足, 但建议再跑满 6h 纯窗口确认 90-150K 档在大流量下稳定.

## 4. 本轮未改代码 (NOP 复盘轮, 符合监督者指令)

- 不编码新动态超时 (监督者已做完).
- 不碰 nv_gw(40006) / ms_gw(40007) / HM1 源码.
- 0 改动, 0 restart (cc4101/nv_gw 本轮均未动).

## 5. nv_gw 参数快照 (本轮)

```
MIN_OUTBOUND_INTERVAL_S=10
NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_BIG_INPUT_FAIL_N=1
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_BIG_INPUT_COOLDOWN_S=180
KEY_COOLDOWN_S=60
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
TIER_COOLDOWN_S=180
```
cc4101 StartedAt = 2026-07-21T05:28:51Z (R2154 restart 后).
nv_gw StartedAt = 2026-07-21T01:44:55Z (连续多轮未漂移).
docker ps: nv_gw Up 5h / cc4101 Up 48min / ms_gw Up 17h / logs_db Up 4d.

## 6. 铁律遵守

- 改前必有数据: ✅ (6h + 30min + 90min 三窗口).
- 改后有验证: ✅ (N/A 本轮未改, 验证的是 R2154).
- 聚焦 nv 链 (cc4101 适配层): ✅ (只读不改).
- 不碰 ms_gw / nv_gw 源码 / HM1: ✅.
- 写入仓库: ✅ (本 round 文件).
- HM2 only: ✅.

## 7. 下一轮建议

- 继续盯 R2154 的 6h 全窗口验证 (本轮只有 45min 纯窗口, 数据偏少). 重点是 90-150K / >150K
  档在大流量 + 大 input 下的稳定性, 确认 150s/160s 档不产生新抢先断.
- 若 6h 验证稳 (75s 类持续归零, fallback 持续低), 可进 R2155+ nv_gw 动态 absolute_cap +
  zombie content ratio 方案 (监督者定的下一步, 撤 40007 的后续工作).
- 若 all_tiers_exhausted 抬头 (NVCF 5 key 全 429), 属上游类, 非 cc4101/nv_gw 旋钮能修,
  记录但不改.
