# R1240 cc2 nv_gw — NOP 巡检轮

**日期**: 2026-08-08 12:05 CST (04:05 UTC)
**结论**: NOP — cc2-primary 100% (60/60), 0 失败. 唯一失败聚类 = hermes 线 3 条
(NVStream_IncompleteRead / all_tiers_exhausted / zombie_empty_completion, 全 out-of-scope). 不改码.

## 30min 数据 (DB 复核 2026-08-08 12:04 CST)

- **全 caller**: cc4101-primary`200|60`, hermes`200|23`+`502|3` → dsv4f0731_nv SR=97.6% (83/86).
- **cc4101-primary (cc2 主链) = 200|60 → SR=100% (60/60), 本轮 0 失败.**
  (DB 复核: cc4101-primary status!=200 → 0 rows. cc_requests 61 条全 fallback_triggered=f.)
- **错误分类 30min (JOIN 归属 caller)**: 3 条 errors **全属 hermes**, 无一属 cc2:
  - `all_tiers_exhausted × 1` (178825ms, req **937fe7b2**) — 同 R1238/R1239 画像 (~180s),
    同一 hermes 请求 5key 瞬挂, 跨窗残留 re-sample (per-memory `ssleof-...` R1130 同簇画像).
  - `zombie_empty_completion × 1` (44067ms, req 13b3f407) — 新 error type 出现, 属 **hermes**
    dsv4f0731_nv 线已知特症 (per-memory `primary-model-dsv4f0731-r1095`), 非 cc2.
  - `NVStream_IncompleteRead × 1` (35318ms, req 59692048) — hermes transient, R1154 容忍带内.
- **tier attempts 30min**: k0-k4 各有 NVCFPexecRemoteDisconnected/Timeout 单条 transient
  (全属 hermes 请求), pexec_success 主导 cc2 全 key 无 tier failure.
- **fallback**: 0% (cc_requests 61 条全 fallback_triggered=f). cc2 主链 60/60 全直连 NVCF.
- **buffer 日志**: 唯一 cc2 异常 = req 986af010 k2 execute_failed attempt-1 → 5s backoff →
  attempt-2 success (55s self-heal, 健康, 无 exhausted/WAIT). 其余 cc4101-primary 全 attempt-1 success.
- **容器**: nv_gw /health ok (5 keys + dsv4f0731_nv), cc4101 /health ok (primary=dsv4f0731_nv).

## 判定
cc2 主链 100% (60/60), 连 6 窗 (R1235-R1240) cc2-primary NOP 健康延续. 唯一错误聚类 = hermes 线 3 条
all out-of-scope (all_tiers_exhausted 单 caller 5key 瞬挂, zombie/IncompleteRead hermes ds4 线特症),
而 cc2 同窗 60 次全成功 — **非共享 NVCF jitter**. 无 cc2 失败聚类, 无单线/配置杠杆. **NOP, 不改码.**

## 下一步
维持观察。zombie_empty_completion 为本窗 hermes 线新出现 error type, 记录观察 (若 hermes 连续多轮
复发且开始跨 caller 同刻失败才查); all_tiers_exhausted 同 R1238/R1239 画像持续 out-of-scope. 若 cc2
主链出现失败立即查.