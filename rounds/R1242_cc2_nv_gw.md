# R1242 cc2 nv_gw — cc2-primary 100% (51/51), 恢复 R1235-R1240 基线, NOP 不改码

**日期**: 2026-08-09 06:02 CST (22:02 UTC 2026-08-08)
**结论**: NOP(观察) — cc2 主链 **SR=100% (51/51), 0 失败**。R1241 (3× buffer_exhausted 共享 NVCF
jitter 聚类) 已彻底恢复, 当前窗回到 R1235-R1240 的 100% 基线。唯一 2 条错误全属 hermes 线,
out-of-scope。不改码。

## 30min 数据 (DB 复核 2026-08-09 06:02 CST)

- **cc4101-primary (cc2 主链) = 200|51 → SR=100%, 0 失败** (DB 复核 status!=200 → 0 rows)。
  R1241 的 3× buffer_exhausted (04:05/04:21/04:25) 无任何残留, 同窗全 attempt-1 success。
- **错误分类 30min (JOIN 归属 caller)**: **2 条 errors 全属 hermes, 无一属 cc2**:
  | req | caller | error_type | dur(ms) |
  |---|---|---|---|
  | d0a0875a | hermes | stream_absolute_cap | 172854 |
  | d3d23b4f | hermes | all_tiers_exhausted | 180071 |
  stream_absolute_cap = hermes 线单请求超绝对 cap (172s, 超 cc4101 470s? 否 — 属 hermes 自身配置)。
  all_tiers_exhausted = hermes 线 5key 瞬挂 (180s, 同 R1238/R1239/R1240/R1241 画像, ~180s 跨窗残留)。
  全 non-shared (cc2 同窗 51 次全成功), out-of-scope, NOP 自愈。
- **tier attempts 30min (dsv4f0731_nv 线, 全 key)**: k0-k4 各 key 有分散 NVCFPexecTimeout/
  NVCFPexecRemoteDisconnected 单条 (全都属 dvc4 线 transient), pexec_success 主导, 无 exhausted,
  无单 key 劣化。cc2 请求 (JOIN request_id) 全部 pexec_success + attempt-1。
- **fallback**: 0% (cc_requests 52 条全 fallback_triggered=f) — cc2 主链 51/51 全直连 NVCF。
- **buffer/wait 日志**: cc4101-primary 全 attempt-1 success (9-13s, success_tool_call flush),
  无 WAIT-、无 all_keys_exhausted。

## 判定
R1241 (cc2-primary 94.3% 50/53, 3× buffer_exhausted 共享 NVCF jitter 聚类) → **R1242
(100% 51/51, 0 失败)**: 该共享 jitter 聚类确已彻底自愈, 与 R1241 恢复窗复核一致。
cc2 主链回到 R1235-R1241 期间 100% 基线。当前窗唯一 2 条错误全属 hermes 线 (all_tiers_exhausted +
stream_absolute_cap, ~180s 各自画像), 非共享 jitter, 无杠杆可改。**NOP, 不改码**, 如实记录观察。

## 下一步
1. **维持观察不改码**。cc2 主链 100% (R1242), 无 cc2 失败聚类, 无 mihomo 逐线排查需求
   (R1207 门槛未触发)。
2. **hermes 线 all_tiers_exhausted** (连 4 轮到 R1241 仍在, R1242 又 1 条 ~180s, 多 req 跨窗):
   单 caller 同刻 5key 瞬挂, 非共享 NVCF jitter (cc2 同窗 51 次全成功)。若 hermes all_tiers_exhausted
   连续多轮复发且开始跨 caller 同刻失败 (共享 jitter 画像), 才升级排查共享线路; 当前 NOP。
3. **共享 NVCF jitter 聚类 (R1241 3× buffer_exhausted)**: 已恢复, 不旋转 key / 不改 fid (全 key
   同刻同败, 单 key 层面无杠杆 R1228 结论)。维持 5 key 全 bind fid 281478d0-f307 现状。
4. 下一窗口若 cc2 SR 维持 99%+ 且无新聚类 → 连续 NOP 巡检; 若聚类跨多轮复发 → 升级排查。