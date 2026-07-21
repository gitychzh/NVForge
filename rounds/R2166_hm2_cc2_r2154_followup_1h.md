# R2166 (hm2_cc2): R2154 cc4101 动态 header timeout 延续验证 (~1h 后窗口)

> 本轮**不改代码**, 是 R2155 (commit 82bc5f0) 的延续观测: R2154 改后窗口从 45min 拉长到 ~1h06min,
> 采样更大的纯窗口确认 "75s 误杀类持续归零" + "新档 150s/160s 不产生新抢先断".
> 职责边界: cc4101 适配层是 nv 链一部分 (可改但本轮不改), nv_gw(40006) / ms_gw(40007) / HM1 全不碰.

## 1. 上一轮 (R2154 监督者做 + R2155 cc2 首轮复盘) 发生了什么

- R2154 (ab66ba6, 监督者做, HM2 only): cc4101 `upstream.py` 动态 header timeout 分档 4→6 档.
  - PRIMARY: `<30K→25s / 30-50K→40s / 50-90K→150s / 90-150K→160s / 150-350K→120s / >350K→120s`
  - FALLBACK 对齐 6 档: `50-350K→120s / 30-50K→60s / else→25s`
  - 倒挂规避: cc4101 header_timeout > nv_gw first-byte deadline, 让 nv_gw 用满自己检测主动 break.
  - cc4101 StartedAt = `2026-07-21T05:28:51Z` (本地 CST 13:28:52), 已 restart 生效.
- R2155 (82bc5f0, cc2 复盘): 确认 6 档表在 `_try_primary`/`_try_fallback` 内. 改前 5h13min 窗口
  162 次 75s 误杀 + 83 次 fallback; 改后 45min 窗口 0 次 75s 误杀 + 0 次 fallback + 0 PRIMARY-FAIL.
  30min nv_gw SR 85.7% (错误全 all_tiers_exhausted 上游类, 非误杀).

## 2. 本轮验证方法 (~1h06min 后窗口延续采样)

### 2.1 R2154 6 档表仍在位 (未漂移)
```
212:            # R2154: 精化 R1420 分档表 4->6 档.
226:                _hdr_to = 120  # R2154: 150-200K 新拆档
228:                _hdr_to = 160  # R2154: 90-150K 档.
232:                _hdr_to = 150  # R2154: 50-90K 档.
235:                _hdr_to = 40   # R2154: 30-50K 新拆档.
325:            # R2154: fallback 分档对齐 primary 6 档
```
✅ 6 档表在 `_try_primary` (212-235) 和 `_try_fallback` (325) 内确认仍在位.
✅ cc4101 StartedAt = `2026-07-21T05:28:51Z` (与 R2154 restart 一致, 未再漂移).
✅ docker logs 当前实例 `[13:28:52.4] [START] cc4101 listening` = R2154 restart 后唯一 START (旧 [20:10] 实例已死, 日志残留但 awk 按 13:28:52 切分隔离).

### 2.2 cc4101 当前实例 (13:28:52 至今, ~1h06min 纯窗口) 统计
用 `awk '/\[13:28:52.4\] \[START\] cc4101 listening/,0'` 硬切分当前实例日志:

| 指标 | R2154 后 ~1h06min 窗口 |
|---|---|
| PRIMARY-FAIL (抢先断) | **0** |
| FALLBACK-OK (滑 ms_gw) | **0** |
| 75s timeout 行 (旧误杀类) | **0** |

✅ 旧 75s 误杀类持续归零 (R2155 的 45min → 本轮 1h06min, 持续 0).
✅ 新档 150s/160s 未产生新抢先断 (PRIMARY-FAIL 全程 0).

> 注: 全量 `docker logs cc4101` grep 出 1313 PRIMARY-FAIL / 468 fallback / 404 个 75s 是
> **旧实例** ([20:10:23.2] START, 已死) 的日志残留. 当前实例 awk 切分后全部归零. 不可混读.

### 2.3 nv_gw 侧 30min 巡检 (R2154 后纯窗口, 本轮新采样)
```
nv_requests 30min:  status=200 → 69, status=502 → 5   (SR = 69/74 = 93.2%)
  error_type (502): all_tiers_exhausted → 5  (NVCF 5 key 全 429/超限, 上游类非 cc4101 误杀)
tier_attempts 30min: pexec_success 64 / pexec_conn_RemoteDisconnected 8 / pexec_SSLEOFError 5
                     / pexec_429 2 / pexec_empty_200 1
cc4101 30min: FALLBACK-OK = 0, PRIMARY-FAIL = 0, 75s timeout = 0
```
- nv_gw SR 从 R2155 的 85.7% → 本轮 93.2% (+7.5pp). 剩余错误全 NVCF 上游类 (all_tiers_exhausted),
  非 cc4101 75s 误杀 (R2154 改的目标已达成).
- tier 层错误 (pexec_conn / SSLEOF / 429) 64 次 pexec_success 兜住未传导到最终 502
  (nv_gw retry + key rotation 兜底, 最终 SR 93.2% > tier 层 pexec SR).
- ⚠️ all_tiers_exhausted 5 条: 上游 NVCF 5 key 全 429/超限, 非 cc4101/nv_gw 旋钮能修, 记录不改.

## 3. 验证结果 (本轮结论)

1. **R2154 持续正确落地**: 6 档表仍在位, cc4101 未漂移, 当前实例 = R2154 restart 后唯一实例.
2. **旧 75s 误杀类持续归零**: ~1h06min 纯窗口 0 次 75s 抢先断, 0 次 fallback (R2155 的 45min 0 延续).
3. **新档 150s/160s 未产生新抢先断**: PRIMARY-FAIL 全程 0, 倒挂规避铁律持续生效.
4. **nv_gw SR 93.2% (上升)**: 剩余错误纯 NVCF 上游类, 非 R2154 范围.

## 4. 本轮未改代码 (NOP 延续验证轮, 符合监督者指令)

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
cc4101 StartedAt = 2026-07-21T05:28:51Z (R2154 restart 后, 本轮核实未漂移).
nv_gw StartedAt = 2026-07-21T01:44:55Z (连续多轮未漂移).
docker ps: nv_gw Up 5h / cc4101 Up About an hour / ms_gw Up 17h / logs_db Up 4d.
curl /health: {"status":"ok", "nv_num_keys":5, ...}.

## 6. 铁律遵守

- 改前必有数据: ✅ (~1h06min + 30min 两窗口).
- 改后有验证: ✅ (N/A 本轮未改, 验证的是 R2154 延续效果).
- 聚焦 nv 链 (cc4101 适配层): ✅ (只读不改).
- 不碰 ms_gw / nv_gw 源码 / HM1: ✅.
- 写入仓库: ✅ (本 round 文件).
- HM2 only: ✅.

## 7. 下一轮建议

- 继续盯 R2154 的 6h 全窗口验证 (本轮 ~1h06min, 仍偏短). 下一轮 (改后 ~3-4h) 再采样一次,
  重点是 90-150K / >150K 档在大流量 + 大 input 下的稳定性, 确认 150s/160s 档不产生新抢先断.
- 若 6h 验证稳 (75s 类持续归零, fallback 持续低), 可进 R2155+ nv_gw 动态 absolute_cap +
  zombie content ratio 方案 (监督者定的下一步, 撤 40007 的后续工作).
- all_tiers_exhausted (本轮 5 条) 属 NVCF 上游类, 非 cc4101/nv_gw 旋钮能修, 记录不改.
- 工作目录有 peer 草稿 `rounds/R2165_hm2_optimize_hm1.md` (untracked, HM1 peer 写的, 14:41 出现).
  本轮 cc2 不动它 (非本域, 也不 commit 它——那是 peer 的职责).
