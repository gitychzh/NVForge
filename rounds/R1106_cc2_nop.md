# R1106 cc2 NOP 巡检轮 — 2026-08-07 22:50 CST

**状态: NOP (不改码, 只记数据)。** cc2 主链 30min 114/114 = 100.0% SR 零错误零 fallback,
无任何新签名 (cc2 范围)。全量唯一 bad 归属 peer。

## 30min 链路总览 (caller × status)

| caller | status | count |
|---|---|---|
| cc4101-primary | 200 | 114 |
| hermes | 200 | 28 |
| hermes | 502 | 1 |

- **cc2 (cc4101-primary)**: 114/114 = **100.0% SR, 0 bad** (较 R1105 的 109 略升, 全 200)
- **全量 dsv4f0731_nv**: 99.3% (142)? → 实测 114+28+1 = 143 total, 唯一 1 bad = hermes (peer)

## 错误归属
- 唯一 1× zombie_empty_completion (502) → caller=**hermes** (peer) 非 cc2 主链 (JOIN 铁证法,
  记忆 bad-fid + failed-hermes 判归属)。cc4101-primary 0 bad。

## fallback
- 0% (cc_requests 30min: 115 total, fb=0, 全走 primary)

## per-key tier 错误 (nv_tier_attempts 30min)

| key | fid | error_type | count |
|---|---|---|---|
| 0 | 281478d0 | pexec_success | 23 |
| 0 | 52e1ddb6 | NVCFPexecRemoteDisconnected | 1 |
| 1 | 281478d0 | pexec_success | 23 |
| 2 | 281478d0 | pexec_success | 22 |
| 3 | 281478d0 | pexec_success | 23 |
| 3 | 52e1ddb6 | NVCFPexecRemoteDisconnected | 1 |
| 3 | 52e1ddb6 | empty_200 | 1 |
| 4 | 281478d0 | pexec_success | 23 |

- 主 fid **281478d0** 全 pexec_success 无错误。
- 错误全落在 fid **52e1ddb6** (历史记忆坏 fid — 越界容器 40666 hermes 线泄漏源): k0 1× +
  k3 1× NVCFPexecRemoteDisconnected + k3 1× empty_200 = 总 3x 一次性 distributed transient,
  单请求 buffer 自愈, 与 R1105 基本持平未上升, 无 multi-key 连续复发。

## buffer
- 全 attempt-1 直 flush 秒回 (6-19s): req=df1bb9ea 12s, req=026a65d8 19s, req=fcb7e2ba 7s,
  req=6356d747 7s; verdict 全 success_tool_call/success_text; 零重试零级联零 buffer_exhausted。

## 容器
- /health 2026-08-07 22:50 CST: nv_gw 40006 http 200, cc4101 4101 http 200
- docker ps: nv_gw Up 19h, cc4101 Up 19h, dsv4p_nv40066 Up 3 days

## 结论
cc2 主链连续多轮 (R1096-R1106) 100% SR + zero fallback, 无参数可调, 不改码。NOP。

## 下一步
- 延续 NOP。仅当 52e1ddb6 RD / empty_200 在多 key 连续复发 (多个独立请求多 key 持续失败)
  或 zombie_empty_completion 出现 caller=cc4101-primary 才进 cc2 指标并查链路。