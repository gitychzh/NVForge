# R1243 cc2 nv_gw — 共享 NVCF jitter 聚类复发 (3× cc2 502, NOP 不改码)

**日期**: 2026-08-09 07:20 CST (23:20 UTC 2026-08-08)
**结论**: NOP(观察) — cc2 主链 **SR≈95-98%**, **3× 真实 502 全属 cc2** (2× buffer_exhausted +
1× all_tiers_exhausted), 打破 R1242 的 100% 基线。但根因 = **R1241 共享 NVCF 上游瞬时 jitter 聚类
第 2 次复发** (同刻 5 key/IP 全挂 + 跨 caller 同窗失败 + 失败 key 弥散), 无单线/配置/代码杠杆。不改码。

## 30min/45min 数据 (DB 复核 2026-08-09 07:20 CST)

- **全 caller (30min)**: dsv4f0731_nv SR≈94% (cc4101-primary 39-41×200 + hermes 16-20×200, 502s 跨 caller 散布)。
- **cc4101-primary (cc2 主链, 45min 窗) = 3× 真实 502** (打破连 2 窗 100% R1241 后 R1242 恢复的干净基线):
  | req | 时间 UTC | dur(ms) | error_type | 失败 key | 签名 |
  |---|---|---|---|---|---|
  | f32e0008 | 06:38:09 | 88840 | buffer_exhausted | k3→k4→k5 | 3 连 AKE → fail-fast → ms_gw |
  | b82eb976 | 06:39:50 | 227500 | all_tiers_exhausted | k4→… | 5key 全挂 → ms_gw |
  | 47f921ae | 06:43:23 | 105469 | buffer_exhausted | k5→k1→k2 | 3 连 AKE → fail-fast → ms_gw |
- **根因铁证 (nv_gw buffer 日志)**: 3 条全打 `[NV-GLM52-CHAIN-FAIL] all 5 keys + modes exhausted`,
  `all_keys_exhausted=True` → **同刻 5 key (=5 egress IP) 全挂**, 非单 key/单 IP/单 fid 杠杆。
  失败 key 在 f32e0008 内跨 k3/k4/k5, 47f921ae 内跨 k5/k1/k2, b82eb976=k4 → **跨 req 也变, 无单一坏 key**。
- **跨 caller 相关**: 同窗 hermes (_nv) 也失败 — 06:44 stream_no_content_gap (76173ms),
  06:52 all_tiers_exhausted, 06:58 stream_absolute_cap → **NVCF/网络级共享抖动** (R1241 / memory
  `nvcf-shared-jitter-real-502-cluster` R1228 同一画像)。三 req 失败窗 06:38-06:44 内双 caller 同刻失败。
- **tier attempts per-key (30min) 弥散无单线**: k0 RemDisconnected×3+Timeout×1, k1 ×2+×2, k2 ×3+×1,
  k3 ×4+×2, k4 ×6+×0 → 全 key 各有瞬态 NVCFPexecRemoteDisconnected/Timeout, no single dominant key。
- **缓冲区自愈 (健康)**: req `291d8bbb` hit chain-fail attempt1(k5)/attempt2(k1) all_keys_exhausted,
  attempt-3 self-heal success_tool_call (104s) → **nv_requests 记录为 200**。聚类后 06:50+ 起后续请求
  全 attempt-1 success (07:11-07:14 全 success_text/tool_call, 无 AKE/EXHAUST)。NVCF 上游已恢复。
- **fallback**: 3 个失败 req 走 buffer→AKE fail-fast→ms_gw fallback (NVU_DISABLE_MS_FALLBACK=0 恢复启用),
  ms_gw 兜底保服务 (fallback 率低, 仅 cluster 触发)。铁律 4 遵守, 不切回/不禁用。

## 容器健康
- nv_gw /health ok: 5 keys, dsv4f0731_nv 单模式 active; cc4101 /health ok (primary=dsv4f0731_nv)。
- docker ps: nv_gw/cc4101 Up 2 days, 无重启/漂移。参数快照与 R1234-R1242 一致 (无环绕改)。

## 判定
共享 NVCF 上游瞬时 jitter 聚类 **第 2 次复发** (R1241 → R1243), 双 caller 同窗失败 + 全 key 弥散 =
NVCF-side, **无容器/配置/mihomo 杠杆** (R1207 单线 mihomo 门槛未触发: 非单一持续劣化线, 是瞬态弥散)。
buffer fail-fast + ms_gw fallback 按设计兜住, 3 req 全部经 fallback 保服务 (非 NV 成功, 但未丢请求)。
**NOP, 观察。** 如实记录: 本轮非 100% 干净基线, 是 cluster 复发。

## 下轮观察点
1. 若下一窗 cc2-primary 回到 100% (同 R1241→R1242 恢复), 则确认 cluster 为瞬态, 维持 NOP。
2. 若 cluster 连续 3 轮复发 (R1241, R1243, +下轮) 且每次双 caller 同刻失败, 才升级评估是否需
   在 NVCF 侧 (fid 轮换 b6029a96) 或增大 buffer retries 找杠杆 —— 但**先拉数据确认再改**, 铁律 1。
3. hermes 线 all_tiers_exhausted/stream_* 继续 hermes-scope, 不属 cc2。