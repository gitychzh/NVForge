# R1238 cc2 nv_gw — NOP 巡检轮

**日期**: 2026-08-08 11:44 CST (03:44 UTC)
**结论**: NOP — cc2-primary 100% (52/52), 0 失败. 唯一失败聚类 = hermes 线 all_tiers_exhausted × 2 (~180s, out-of-scope). 不改码.

## 30min 数据 (注入分析 11:34 CST + DB 复核)

- **全 caller**: cc4101-primary`200|52`, hermes`200|24`+`502|1` → dsv4f0731_nv SR=98.7% (76/77).
- **cc4101-primary (cc2 主链) = 200|52 → SR=100% (52/52), 本轮 0 失败.**
  (DB 复核: cc4101-primary status!=200 → 0 rows. cc_requests 全 primary 200, fallback 0%.)
- **错误分类 30min**: `all_tiers_exhausted × 1` (duration_ms=180029). DB 复核归属 **caller=hermes**,
  request_id=1a6a4b35 (45min 窗另有 hermes 937fe7b2, 同画像 ~179s). **非 cc2 主链, out-of-scope.**
- **tier attempts 30min**: pexec_success 主导. NVCFPexecRemoteDisconnected + NVCFPexecTimeout
  弥散跨 key, 每条归属 **独立 hermes 请求** (4847d338/75882c89/b8a770e4/c7e78710 单条 transient),
  hermes 线 937fe7b2 = 3×RemoteDisconnected+1×Timeout → hermes 单 caller 5key 瞬挂. **cc2 请求无任何 tier error.**
- **per-key 45min fid 分布**: k0:18/k1:17/k2:17/k3:17/k4:22 全 bind 281478d0-f307 (正确单模式 fid), 分布正常.
- **fallback**: 0% (cc_requests 全 fallback_triggered=f). cc2 主链 52/52 全直连 NVCF.
- **buffer 日志**: 正常 — 1 条 cc4101-primary 请求 attempt-2 5s backoff 后自愈 (50s, 无 exhausted),
  其余全 attempt-1 success. keymanager 无 clip/429 累积.
- **容器**: nv_gw /health ok (5 keys + dsv4f0731_nv), cc4101 /health ok (primary=dsv4f0731_nv).

## 判定
cc2 主链 100% (52/52) 连多窗健康延续. 唯一失败聚类 all_tiers_exhausted 归属 **hermes 线**
(单 caller 同刻 5key 瞬挂, RemoteDisconnected/Timeout spread), 而 cc2 同窗 52 次全成功 —
**非共享 NVCF jitter** (共享 jitter 应跨 caller 同刻失败, 不符合 memory `nvcf-shared-jitter` 门槛),
属 hermes 单 caller transient, out-of-scope, NOP 自愈即可. 无 cc2 失败聚类, 无单线/配置杠杆. **NOP, 不改码.**

## 下一步
维持观察。若 hermes all_tiers_exhausted 连续多轮复发且开始跨 caller 同刻失败 (共享 NVCF jitter 画像)
再升级排查; 若 cc2 主链出现失败立即查.