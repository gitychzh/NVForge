# R1113 cc2 NOP — 2026-08-07 (HM2 nv_gw 自优化)

## 结论: NOP 巡检轮 (不改码)

30min cc2 主链 111/111 = **100.0% SR 零错误** (cc4101-primary 经 nv_gw 40006, primary model=dsv4f0731_nv);
全量 dsv4f0731_nv 157/158 = **99.4% SR** (唯一 1× 502 zombie_empty_completion 归属 **hermes**, 非 cc2);
fallback 0%; cc2 范围错误分类 (无错误); per-key 全 pexec_success 为主, 仅 fid 52e1ddb6 的
k0 1× + k1 2× + k4 1× NVCFPexecRemoteDisconnected 一次性 distributed transient (单请求 buffer 自愈);
buffer 全 attempt-1 直 flush 无重试无级联。

## 依据 (注入轮前分析 2026-08-07 23:14 CST + 实时 DB/health 复核)

| 指标 | 结果 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | cc4101-primary **111/111 = 100.0% SR, 0 bad** (注入 200\|111) | ✅ |
| dsv4f0731_nv 全量 | 157/158 = **99.4% SR** (1× 502 zombie_empty_completion) | ✅ 非 cc2 |
| **非-200 归属 (实时 DB 复核)** | **caller=hermes, fid=52e1ddb6, k1, 502 zombie_empty_completion, dur 2001ms — 唯一 1 行, 归属 hermes 非 cc2** | ✅ 确认 |
| fallback 触发率 | 0% (158 total fb=0 全走 primary) | ✅ |
| per-key tier 错误 | 全 pexec_success 为主; 仅 fid 52e1ddb6 的 k0 1× RD + k1 2× RD + k4 1× RD 一次性 transient 单请求自愈, 无 multi-key 连续复发 | ✅ |
| buffer | 实时 logs: 全 attempt=1 direct flush (success_tool_call), elapsed 7-10s, 无重试无级联无 buffer_exhausted | ✅ |
| container /health | nv_gw 200 (5 key, dsv4f0731_nv 含), cc4101 200 (dsv4f0731_nv), Up 19-20h | ✅ |

## 改动
- 无。cc2 范围 SR ≥ 99% (100%) 且无新 cc2 签名 (唯一 502 zombie 归属 hermes), 无参数可调。

## 下一步
- 延续 NOP。连续多轮 (R1096-R1113) 100% SR + zero fallback。
- 唯一 502 (zombie_empty_completion) 归属 **hermes** (caller=hermes, bad fid 52e1ddb6, dur 2s):
  非 cc2 范围, 越界容器 40666 泄漏线模式, 单请求 transient, 不处置。
- k0/k1/k4 RD (bad fid 52e1ddb6): 量小 (总 4x, 单请求), 一次性 distributed transient 单请求 buffer 自愈。
  仅当 **multi-key 连续复发** (多独立请求多 key 持续失败) 才查链路/mihomo 线路。
- 若 zombie_empty_completion 或错误中出现 caller=cc4101-primary (c.parent) 才进 cc2 指标处置。

## 参数快照 (未动, 同 R1112)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  UPSTREAM_TIMEOUT=90, BUFFER 5×90s=450s, TIER_TIMEOUT_BUDGET_S=180, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  NVU_FORCE_STREAM_UPGRADE=0, MIN_OUTBOUND_INTERVAL_S=10, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4.
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_URL=http://nv_gw:40006/v1/messages,
  PRIMARY_HEADER_TIMEOUT=400, CC4101_STREAM_TOTAL_DEADLINE_S=470, UPSTREAM_TIMEOUT=130,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions (历史残留, 未触发).
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s SDK < 900s idle.