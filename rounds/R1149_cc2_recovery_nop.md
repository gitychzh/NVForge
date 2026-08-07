# R1149 cc2 — R1148 风暴带的过境尾窗 (恢复期 NOP)

## 结论: 不改码 — R1148 瞬时 DEGRADED-fid + egress 风暴已完全过境, 最新窗口 100% SR

本轮是 R1148 判定为"瞬时过境已自愈"后的**恢复期 NOP**。30min 窗口内仍有 R1148 那场风暴带
(17:47-18:02 UTC) 的 6 次 502 残留(`all_tiers_exhausted` × 5 + `buffer_exhausted` × 1), 但:
- **1) 6 个失败全部落在 17:47-18:02 UTC 的降级带内**, 之后 18:03→18:14 连续 28+ 个 200 = **0 错误**;
- **2) 最新 5min 实查 20/20 = 100% SR** (又补了 7 个 200), 无失败;
- **3) 错误签名与 R1148 完全相同** (all_tiers_exhausted + buffer_exhausted, avg_dur ~220s), 无新错误类型;
- **4) tier 错误只有 2× NVCFPexecRemoteDisconnected** (瞬时 egress blip), 全程 429=0 / empty200=0
  → 非 KeyManager/cooldown/配置根因;
- **5) buffer 全 attempt-1 direct flush** (8-13s/req, success), 无 exhaust/无 WAIT — 干净稳态。

**无码可改** — 这是同一场风暴的尾窗, 非新事件, 降级带已过境, 健康链回到 100%。

## 依据 (本 session 实查 2026-08-08 02:14 CST)

### 表面 (30min nv_requests, caller=cc4101-primary 实查)
- 42|200 + 6|502 = 48 total, SR 87.5% (30min 整窗)。⚠️ 但 30min 整窗含 R1148 风暴带。
- **最新 5min: 20/20 = 100% SR** — 降级带已完全过境。
- 失败时间线 (created_at 实查): `buffer_exhausted`(acdcf33a) 17:47; `all_tiers_exhausted` 82ee78ae 17:49 /
  ab59c732 17:54 / c262f96c 17:58 / abe467e0 18:01 / **9731043f 18:02** (最后一个)。之后 18:03 起全部 200。
- 首位 200 于 18:03 (4d520bea), 到尾 18:14 连续 200 = 恢复干净, 无一眼错。

### Tier 层 (nv_tier_attempts 实查)
- 主链 dsv4f0731_nv: **全 5 key → fid 281478d0-f307** (37× nvcf_pexec, k0-k4), 主指纹保持 R1148 迁移结果;
  仅 2× 旧 fid **52e1ddb6** 尾误 (k0/k1 各 1) — 与 R1148 "主 fid 已切 281478d0-f307" 结论一致。
- 错误分类: 仅 `NVCFPexecRemoteDisconnected` × 2 (瞬时 egress), 其余全 pexec_success (38)。
- **429=0, empty200=0** → 排除 key-cooldown / integrate 空响应根因。

### nv_gw 日志 (buffer/wait/DEGRADED) — 自愈确认
- 无 WAIT-, 无 DEGRADED 新事件, 无 buffer exhaust。
- 全部 `[NV-BUFFER-ATTEMPT] attempt=1/5` → `[NV-BUFFER-VERDICT] success_tool_call` → direct flush
  (2-14s/req, e.g. 2586b/2016ms, 1572b/13954ms, 28729b/8364ms, 7890bc6a 33551b/13306ms) — 干净稳态签名。
- 容器: nv_gw 40006 ok, dsv4p_nv40066 40066 ok, 稳定未重启。

### fallback
- cc_requests 30min: **nb=0/1783** — fallback 未触发, ms_gw 未走。✅

## 改动: 无 (恢复期 NOP)

6 个 502 与 R1148 为同一场风暴 (17:47-18:02 UTC, fid DEGRADED + 全 key egress RemoteDisconnected),
降级带结束后的所有请求 100% SR。无新错误、无配置漂移, 参数快照与注入一致
(UPSTREAM_TIMEOUT=90, NVU_BUFFER_MAX_RETRIES=5, NVU_DISABLE_MS_FALLBACK=0, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv)。
改码 = 让健康链去对冲一个已过境瞬时, 得不偿失。继续 NOP 写数据。

## 数据 (相对上轮 R1148)

| 指标 | R1148 (30min 整窗) | R1149 (实查) | 判断 |
|---|---|---|---|
| cc2 主链 30min 整窗 SR | 95.8% (113/118) | 87.5% (42/48, 仍含风暴尾窗) | 恢复中 |
| **最新 5min SR** | **100% (16/16)** | **100% (20/20)** | ✅ 持续干净 |
| surface 错误 | all_tiers_exhausted 5 + buffer_exhausted 1 | 同 (无新类型) | 尾窗 |
| 末次失败时间 | 18:02 (9731043f) | 同 (最后失败已过) | ✅ |
| 降级带后续 SR | 28+ 连续 200 | 28+ 连续 200 | ✅ 过境 |
| tier 瞬时错误 | NVCFPexecRemoteDisconnected 多 | 仅 2 | ✅ 稀疏 |
| fid 主指纹 | 281478d0-f307 (87×) | 281478d0-f307 (37×) | ✅ 稳定 |
| fallback 触发 | 0 | 0/1783 | ✅ |
| buffer | 风暴期 attempt-2/3 → 过后全 1/5 | 全 1/5 direct flush | ✅ 干净 |

## 下一步
维持 R1148 结论: 该瞬时 (DEGRADED-fid + egress 风暴) 为一过境事件, 无参数可调、无码可改。
继续静稳观察 1-2 轮; 若 30min 整窗 SR 回升到 97%+ 即告恢复闭环, 若再出现全 5 key 连败或新错误类型再深挖。