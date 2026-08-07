# R1107 cc2 — NOP 巡检轮 (不改码)

> 2026-08-07 ~22:52 CST | 30min 窗口 | cc2 主链 cc4101-primary 经 nv_gw(40006) dsv4f0731_nv

## 结论
**NOP。cc2 主链 112/112 = 100.0% SR 零错误零 fallback, buffer 全 attempt-1 直 flush 秒回。
唯一 1× zombie_empty_completion (502) 归属 hermes (peer), JOIN 铁证非 cc2 主链。
k0/k3 RD (fid 52e1ddb6 历史坏 fid) + k3 empty_200 量小一次性 distributed transient 与上轮持平
未上升, 无 multi-key 连续复发 → 不改码。**

## 数据

| 指标 | 值 | 状态 |
|---|---|---|
| cc2 主链 (40006) 30min | cc4101-primary **112/112 = 100.0% SR, 0 bad** (实时复核) | ✅ 全绿 |
| cc2 专属错误分类 | 0 rows (cc2 专属零错误) | ✅ |
| 非-200 归属 | 1× zombie_empty_completion (502), caller=**hermes** (peer) | ✅ peer 归属 |
| fallback 触发率 | 0% (142 total, fb=0, 全走 primary) | ✅ |
| per-key tier 错误 | 全 pexec_success 为主 (fid 281478d0); 仅 k0 2× + k1 1× RD (fid 52e1ddb6) + k3 1× empty_200 一次性 transient, 无 multi-key 连续复发 | ✅ |
| buffer | 全 attempt-1 直 flush (7-19s), verdict=success_tool_call/success_text, 零重试零级联零 buffer_exhausted | ✅ |
| container /health | nv_gw 200, cc4101 200 (实时复核) | ✅ |

### 依据 (实测 DB 2026-08-07 ~22:52 CST + 实时复核 + /health)

- **30min nv_requests (cc4101-primary)**: `caller|status` = `cc4101-primary|200|112` = 100% SR, 0 bad。
  实时复核 `cc4101-primary|200|112`, `hermes|200|38`, `hermes|502|1`。
- **30min 全量非-200 归属**: `SELECT caller,status,error_type` = `hermes|502|zombie_empty_completion|1`,
  cc4101-primary **0 rows** —— 归属铁证 (记忆 bad-fid 52e1ddb6 判归属法, JOIN request_id)。
- **fallback**: 0% (142 total, fallback_triggered=0, 全走 primary)。
- **nv_tier_attempts 30min**: tier=dsv4f0731_nv, 5 key 基本全 `pexec_success` (fid 281478d0);
  仅 k0 2× + k1 1× `NVCFPexecRemoteDisconnected` (fid 52e1ddb6, 历史记忆坏 fid — 越界容器 40666
  hermes 线泄漏源) + k3 1× `empty_200` 一次性 distributed transient 单请求 buffer 自愈。量小零
  buffer_exhausted, 无 multi-key 连续复发。与 R1106 (k0 1× + k3 1× RD + k3 1× empty_200) **基本持平**。
- **buffer 日志 (docker logs --since 30m)**: 全 `attempt=1/5` 直 flush 秒回, verdict 全
  success_tool_call/success_text (req=273044e7 elapsed=1.7s, req=0c48b1ae 9s, req=bbbbb66b 7s,
  req=c67b3586 9s), 零重试零级联零 buffer_exhausted (588 行 buffer 日志全部 attempt-1)。
- **容器 /health 实时复核**: nv_gw:200, cc4101:200。

## 下一步
- 延续 NOP。cc2 主链连续多轮 (R1096-R1107) 100% SR + zero fallback, 无参数可调。
- **k0/k1/k3 RD** (fid 52e1ddb6) + **k3 empty_200**: 量小 (总 4x, 均单请求, 与上轮基本持平未上升),
  一次性 distributed transient, 单请求 buffer 自愈, 与历史记忆模式一致 (泄漏源=越界容器 40666
  hermes 线, 宿主分离)。仅当 RD/empty_200 在多 key **连续复发** (多个独立请求多 key 持续失败)
  才查链路/mihomo 线路。
- **hermes 1× zombie_empty_completion** (peer) 持续关注, 归属 peer 非 cc2 不改动。
- 若 zombie_empty_completion 中出现 caller=cc4101-primary (c.parent) 才进 cc2 指标。

## 参数快照 (未动, 同 R1106)
- 本轮零改动。nv_gw env 复核: NV_GLM52_MODE_CHAIN=pexec_us_rr, NVU_DISABLE_MS_FALLBACK=0,
  UPSTREAM_TIMEOUT=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0, NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s)。
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions。