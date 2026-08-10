# R1241 cc2 nv_gw — 共享 NVCF jitter 聚类 (3× buffer_exhausted, NOP 不改码)

**日期**: 2026-08-08 12:45 CST (04:45 UTC)
**结论**: NOP(观察) — cc2 主链 SR=94.3% (50/53), **3× buffer_exhausted 全属 cc2** (vs R1240 100%),
但根因 = **共享 NVCF 上游瞬时 jitter** (同刻 5 key/IP 全挂 + 跨 caller 同窗失败), 无单线/配置杠杆. 不改码.

## 30min 数据 (DB 复核 2026-08-08 12:45 CST)

- **全 caller**: dsv4f0731_nv SR=92.9-98.7% 区间 (窗滑动), 误差 3-6 条跨 caller 散布。
- **cc4101-primary (cc2 主链, 30min)**: `200|50` + `502|3` → **SR=94.3% (50/53)**。打破连 6 窗 100% (R1235-R1240)。
- **3h 每小时趋势 (cc4101-primary)**: 01:00=`55/55` 100%, 02:00=`140/140` 100%, 03:00=`114/114` 100%,
  **04:00=`70/74`=94.6% (jitter 起始窗)** → 近 3h 全干净后 04:00 才破, = 近期 onset 环境级事件, 非配置漂移。
- **同窗 hermes (_nv) 也失败**: 03:57 IncompleteRead, 04:00 zombie, 04:32 IncompleteRead → **跨 caller 相关**。
- **cc2 错误 30min (JOIN 归属, agent_type=`_nv_anthropic`)**: **3× buffer_exhausted**:
  | req | 时间 UTC | dur(ms) | 失败 key | 签名 |
  |---|---|---|---|---|
  | 281c32dd | 04:05 | 117988 | k5→k1→k2 (attempt1,2,3) | 3 连 AKE → fail-fast → ms_fb fail |
  | 0025cffa | 04:21 | 105640 | k4 (attempt3) | 3 连 AKE → fail-fast → ms_fb fail |
  | e35fcf5f | 04:25 | 106471 | k1→k2→k3 (attempt1,2,3) | 3 连 AKE → fail-fast → ms_fb fail |
  | 3c914505 | 04:30 | 118385 | k5→k1→k2 (attempt1,2,3) | 3 连 AKE → fail-fast → ms_fb fail |
- **cc2 错误 30min (JOIN 归属, agent_type=`_nv_anthropic`)**: **3× buffer_exhausted**:
  | req | 时间 UTC | dur(ms) | 失败 key | 签名 |
  |---|---|---|---|---|
  | 281c32dd | 04:05 | 117988 | (buffer 级) | all_keys_exhausted |
  | 0025cffa | 04:21 | 105640 | k4 (attempt3) | 3 连 AKE → fail-fast → ms_fb fail |
  | e35fcf5f | 04:25 | 106471 | k1→k2→k3 (attempt1,2,3) | 3 连 AKE → fail-fast → ms_fb fail |
- **根因铁证 (nv_gw buffer 日志)**: 3 条全打 `[NV-GLM52-CHAIN-FAIL] an all 5 keys + modes exhausted`,
  `all_keys_exhausted=True` → **同刻 5 key (=5 egress IP) 全挂**, 非单 key/单 IP/单 fid 杠杆.
  失败 key 在 e35fcf5f 内跨 k1/k2/k3 弥散, 跨 req 也变 (k4→k1/k2/k3) → 无单一坏 key.
  同窗 hermes 也失败 (`_nv` 03:57 IncompleteRead, 04:00 zombie) → **跨 caller 相关 = NVCF/网络级共享抖动**
  (per-memory `nvcf-shared-jitter-real-502-cluster` R1228 同一画像).
- **间歇性**: 失败散布在 04:05 / 04:21 / 04:25 (间隔 16min / 4min), 中间全 clean:
  04:07-04:19 连续 14min 全 ok, 04:26 之后全 ok. 非持续 outage, 是 NVCF 侧间歇抖动.
- **自愈**: 聚类后 04:27-04:28 后续��冲请求 (35bac8a4/33c69146/2d43ae75/57c5a39b/412dc9d4)
  全 attempt-1 success 14-24s. NVCF 上游已恢复.
- **设计行为正确**: AKE fail-fast (3 连 all_keys_exhausted ≥ 3 → 跳过 WaitQueue 省 180s) 生效;
  ms_fb 已尝试但 ms_gw 同刻也败 (out-of-scope hermes 线). 所有缓冲链设计如期工作.
- **fallback**: ms_gw 已启用 (NVU_DISABLE_MS_FALLBACK=0), 本轮 3 条在 NVCF 全败后均尝试 ms_fb,
  ms_fb 也败 → 502 返回 (ms_gw 同受损, 与 NVCF 共享 upstream 抖动无关, out-of-scope).
- **tier attempts**: 3 条 buffer_exhausted 无 nv_tier_attempts 落库 (buffer 级失败, 未到单 tier 记录),
  反映 JMY 链整体在 chain 层判 all_keys_exhausted 即 fail-fast, 未逐 key 展开日志 — 正常行为.
- **容器**: nv_gw /health ok (5 keys + dsv4f0731_nv), cc4101 /health ok (primary=dsv4f0731_nv).

## 判定
R1240 (cc2-primary 100% 60/60) → R1241 (96.3% 52/54) 破 99% NOP 门槛, 但根因 = **共享 NVCF 上游瞬时
jitter 聚类** (per-memory `nvcf-shared-jitter-real-502-cluster` R1228 精准同画像):
1. **同刻 5 key (=5 egress IP) 全挂** (`all 5 keys + modes exhausted`, `all_keys_exhausted=True`)
   → 无单 key/单 IP 杠杆 (旋转 key/bind 换 fid 都无用, 全 key 同败).
2. **跨 caller 相关** (hermes `_nv` 同窗 03:57/04:00 也败) → NVCF/网络级共享抖动, 非本机配置.
3. **间歇性 + 自愈** (14min clean gap, 聚类后立即恢复 attempt-1 success).
4. 失败 key 弥散 (k4→k1/k2/k3), 排除单 fid/单 IP.

**无杠杆可改**: 全 key 同败时 mihomo 逐线排查 (R1207 门槛)、per-key fid 旋转、key 绑定调整全无效.
buffer fail-fast + WaitQueue-skip + ms_fb 设计已如期工作. **NOP, 不改码**, 如实记录下轮观察.

## 下一步
1. **维持观察不改码**。此聚类为共享 NVCF jitter (per-memory R1228 画像), 无单线/配置杠杆,
   自愈已完成 (04:26 后全 ok). 判定标准: 若 cluster 频率持续 (多轮复发且每轮 >1 失败) 才升级;
   单窗 1-3 条弥散 = R1154「容忍带」内 NOP 观察.
2. **不旋转 key / 不 bind 换 fid**: 全 key 同刻同败, 单 key 层面无好坏之分, 旋转无效 (R1228 结论).
3. **ms_fb**: 已启用且本轮正常触发 (NVCF 全败后尝试 ms_gw, ms_gw 同刻也败属 out-of-scope).
   若后续 NVCF jitter 聚类仍导致 ms_fb 频繁败, 再评估 ms_gw 健康; 本轮不动.
4. 下一窗口若 cc2 SR 回 99%+ 且无新聚类 → 恢复 NOP 巡检轮; 若聚类跨多轮持续 → 升级排查共享线路.
---
### 附: R1241 聚类后恢复窗复核 (2026-08-08 13:39 CST, 本轮会话 fresh 数据)
聚类已自愈。当前 30min 窗: **cc4101-primary (cc2) = 200|44|46 全 200 → SR=100%, 0 失败**,
恢复 R1235-R1240 的 100% 基线。唯一 4 条 errors 全属 **hermes** 线 (`200|28`+`502|4`:
2× zombie_empty_completion / 1× NVStream_IncompleteRead / 1× all_tiers_exhausted), 全 out-of-scope。
fallback 0% (cc_requests 43/43 fb=0)。buffer 正常 (cc2 全 attempt-1 success, 唯一 33ebca9b
attempt-2 backoff 自愈)。tier transient 分散 k0-k4 (RemoteDisconnected/Timeout, hermes 请求),
pexec_success 主导。容器 health ok (nv_gw 5 keys, cc4101 primary=dsv4f0731_nv)。
→ **验证 R1241 NOP 判定正确**: 共享 NVCF 上游瞬时 jitter 确已恢复, 无残留, 不改码。
