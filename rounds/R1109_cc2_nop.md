# R1109 — cc2 NOP (不改码)

日期: 2026-08-07 23:00 CST
主机: HM2 (100.109.57.26, 用户 opc2_uname)
容器: nv_gw:40006 (Up 19h, 200)
链路: cc4101-primary → nv_gw:40006 → dsv4f0731_nv (NVCF pexec) | 无 fallback 配置变更

## 结论

**NOP。cc2 主链 115/115 = 100.0% SR 零错误零 fallback, buffer 全 attempt-1 直 flush 秒回。**

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | cc4101-primary **115/115 = 100.0% SR, 0 bad** (报告注入 116, 实时复核 115) | ✅ |
| cc2 专属错误分类 | (无错误) | ✅ |
| 非-200 归属 | 0 rows (任何 caller 无非-200) | ✅ |
| fallback 触发率 | 0% (163 total, fb=0, 全走 primary) | ✅ |
| per-key tier 错误 | 全 pexec_success (k0 23, k1 23, k2 22, k3 24, k4 24); 仅 k0/k1 2× RD + k3 1× empty_200 — 一次性 distributed transient 与上轮同源, 单请求 buffer 自愈 | ✅ |
| buffer | 无 buffer/wait/keymanager 日志 — 无重试无级联无 buffer_exhausted | ✅ |
| container /health | nv_gw 200, cc4101 200 (Up 19h) | ✅ |

## 依据 (注入轮前分析 2026-08-07 22:58 + 实时复核 + /health)

- **30min 链路总览**: `cc4101-primary|dsv4f0731_nv|200|116` + `hermes|200|47` → 全 success。
  实时复核 `caller|status|count` = `cc4101-primary|200|115` (分钟滚动), decremented by 1, 仍 100%。
- **dsv4f0731_nv 全量 SR**: 163/163 = **100.0%** (所有 caller)。
- **错误分类**: (无错误) —— cc2 范围延续多轮 (R1096-R1109) 零非-200。
- **fallback**: f|163 → 0% (163 total, fb=0, 全走 primary)。
- **nv_tier_attempts 30min (tier=dsv4f0731_nv)**: 全 `pexec_success` (k0 23, k1 23, k2 22, k3 24, k4 24)
  + **2× NVCFPexecRemoteDisconnected** (k0/k1, fid 52e1ddb6 历史坏 fid) + **1× empty_200** (k3),
  一次性 distributed transient, 单请求 buffer 自愈, 与 R1108 的 3×RD+1×empty_200 基本持平未上升。
  无 multi-key 连续复发。
- **buffer 日志**: (无 buffer/wait/keymanager 日志) —— 全 attempt-1 直 flush, 无重试无级联。
- **容器 /health 2026-08-07 23:00 CST**: 40006 nv_gw http 200 (nv_num_keys=5, nvcf_pexec_models 含
  dsv4f0731_nv), 4101 cc4101 http 200 (primary=dsv4f0731_nv)。docker ps: nv_gw Up 19h。

## 改动

无 (NOP)。cc2 主链连续多轮 100% SR + zero fallback, 无参数可调。无新签名。

## 下一步

- 延续 NOP。仅当 RD/empty_200 在多 key **连续复发** (多个独立请求多 key 持续失败) 才查链路/mihomo 线路。
- fid 52e1ddb6 的 RD 泄漏源=越界容器 40666 (hermes 线, host 分离), 继续记录.
- 若 zombie_empty_completion / 任何错误中出现 caller=cc4101-primary (c.parent) 才进 cc2 指标并处置.

## 参数快照 (未动, 同 R1108)

- nv_gw: NVU_DISABLE_MS_FALLBACK=0, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, UPSTREAM_TIMEOUT=90,
  BUFFER 5×90s=450s, Tier budget 180s, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, MIN_OUTBOUND_INTERVAL_S=10.
  nvcf_pexec_models 含 dsv4f0731_nv.
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  PRIMARY_HEADER_TIMEOUT=400, CC4101_STREAM_TOTAL_DEADLINE_S=470, UPSTREAM_TIMEOUT=130,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions (历史残留, 未触发)。