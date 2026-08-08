# R1239 cc2 nv_gw — NOP 巡检轮

**日期**: 2026-08-08 11:59 CST (03:59 UTC)
**结论**: NOP — cc2-primary 100% (56/56), 0 失败. 唯一失败聚类 = hermes 线 all_tiers_exhausted (单条 ~179s, out-of-scope). 不改码.

## 30min 数据 (注入分析 11:51 CST + DB 复核)

- **全 caller**: cc4101-primary`200|56`, hermes`200|25`+`502|1` → dsv4f0731_nv SR=98.8% (81/82).
- **cc4101-primary (cc2 主链) = 200|56 → SR=100% (56/56), 本轮 0 失败.**
  (DB 复核: cc4101-primary status!=200 → 0 rows. cc_requests 60 条全 fallback_triggered=f.)
- **错误分类 30min**: `all_tiers_exhausted × 1` (avg 178825ms). JOIN 复核归属 **caller=hermes**,
  request_id=937fe7b2 (同 R1238 画像 ~179s) → **非 cc2 主链, out-of-scope.**
- **tier attempts 30min (JOIN caller)**: 全部 NVCFPexecRemoteDisconnected/NVCFPexecTimeout 归属
  **hermes 请求** (937fe7b2 502 = 3×RemoteDisc+1×Timeout → hermes 单 caller 5key 瞬挂;
  c7e78710/5b04e7e5/4847d338/829d18d9/75882c89/4cb3c42c 各单条 transient 自愈).
  **cc4101-primary 请求无任何 tier failure error.** pexec_success 主导 cc2 全 key.
- **fallback**: 0% (cc_requests 全 fallback_triggered=f). cc2 主链 56/56 全直连 NVCF.
- **buffer 日志**: 正常 — cc4101-primary 全 attempt-1 success (多在 6-17s 完成), 无 exhausted, 无 WAIT,
  keymanager 无 clip/429 累积.
- **容器**: nv_gw /health ok (5 keys + dsv4f0731_nv), cc4101 /health ok (primary=dsv4f0731_nv).

## 判定
cc2 主链 100% (56/56), 连 5 窗 (R1235-R1239) cc2-primary NOP 健康延续. 唯一失败聚类 all_tiers_exhausted
归属 **hermes 线** (单 caller 同刻 5key 瞬挂), 而 cc2 同窗 56 次全成功 — **非共享 NVCF jitter**
(共享 jitter 应跨 caller 同刻失败, 不符合 memory `nvcf-shared-jitter` 门槛), out-of-scope, NOP 自愈.
无 cc2 失败聚类, 无单线/配置杠杆. **NOP, 不改码.**

## 下一步
维持观察。若 hermes all_tiers_exhausted 连续多轮复发且开始跨 caller 同刻失败 (共享 NVCF jitter 画像)
再升级排查; 若 cc2 主链出现失败立即查.