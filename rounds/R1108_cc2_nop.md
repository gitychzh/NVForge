# R1108 — cc2 NOP (不改码)

日期: 2026-08-07 22:55 CST
主机: HM2 (100.109.57.26, 用户 opc2_uname)
容器: nv_gw:40006 (Up 19h, 200)
链路: cc4101-primary → nv_gw:40006 → dsv4f0731_nv (NVCF pexec) | 无 fallback 配置变更

## 结论

**NOP。cc2 主链 117/117 = 100.0% SR 零错误零 fallback, buffer 全 attempt-1 直 flush 秒回。**

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | cc4101-primary **117/117 = 100.0% SR, 0 bad** | ✅ |
| cc2 专属错误分类 | 0 rows (零错误) | ✅ |
| 非-200 归属 | 0 rows (本窗口无任何非-200) | ✅ |
| fallback 触发率 | 0% (117 total, fb=0, 全走 primary) | ✅ |
| per-key tier 错误 | 117 pexec_success; 3× RD (fid 52e1ddb6) + 1× empty_200 — 一次性 distributed transient 与上轮同源, 单请求 buffer 自愈 | ✅ |
| buffer | 全 attempt-1 直 flush (7-9s), 零重试零级联零 buffer_exhausted | ✅ |
| container /health | nv_gw 200, cc4101 200 (Up 19h) | ✅ |

## 依据 (实测 DB 2026-08-07 22:55 CST + /health)

- **30min nv_requests (caller=cc4101-primary)**: status 仅 200 × **117** = 100.0% SR, 0 错误。
- **30min 非-200 归属**: `caller|status|count` = 空 rows —— 本窗口连 hermes 的 1× zombie 都移出了 30min。
  cc2 范围延续多轮 (R1096-R1108) 零非-200。
- **fallback**: 0% (117 total, fallback_triggered=0, 全走 primary)。
- **nv_tier_attempts 30min (tier=dsv4f0731_nv)**: 117 全 `pexec_success` + **3× NVCFPexecRemoteDisconnected** (k0/k1, fid 52e1ddb6 历史坏 fid) + **1× empty_200** (k3), 一次性 distributed transient,
  单请求 buffer 自愈。per-key ok: k0 24/26, k1 22/23, k2 22/22, k3 24/25, k4 25/25。无 multi-key 连续复发。
- **buffer 日志**: 全 `attempt=1/5` 直 flush 秒回 (req=e1eff9d7 elapsed=7s, req=2fcf56c2 elapsed=9s),
  verdict 全 success_tool_call, zero retry / zero buffer_exhausted。
- **容器 /health 2026-08-07 22:55 CST**: 40006 nv_gw http 200 (nv_num_keys=5, nvcf_pexec_models 含 dsv4f0731_nv),
  4101 cc4101 http 200 (primary=dsv4f0731_nv)。docker ps: nv_gw Up 19h。

## 改动

无 (NOP)。cc2 主链连续多轮 100% SR + zero fallback, 无参数可调。无新签名。

## 下一步

- 延续 NOP。仅当 RD/empty_200 在多 key **连续复发** (多个独立请求持续失败) 才查链路/mihomo 线路。
- fid 52e1ddb6 的 RD 泄漏源=越界容器 40666 (hermes 线, host 分离), 继续记录.
- 若 zombie_empty_completion / 任何错误中出现 caller=cc4101-primary 才进 cc2 指标并处置.

## 参数快照 (未动, 同 R1107)

- nv_gw: NVU_DISABLE_MS_FALLBACK=0, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, UPSTREAM_TIMEOUT=90,
  BUFFER 5×90s=450s, Tier budget 180s. nvcf_pexec_models 含 dsv4f0731_nv.
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  PRIMARY_HEADER_TIMEOUT=400, CC4101_STREAM_TOTAL_DEADLINE_S=470, UPSTREAM_TIMEOUT=130,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions (历史残留, 未触发)。