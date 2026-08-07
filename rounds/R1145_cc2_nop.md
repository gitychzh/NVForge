# R1145 cc2 NOP 巡检轮 (不改码)

- 时间: 2026-08-08 01:50 CST
- 判定: **NOP** — 30min 主链零表面错误, cc2-primary 100% SR, fallback 0%, 无新错误
- 容器: nv_gw 22h, cc4101 22h, dsv4p_nv40066 3d (稳定未重启, /health ok)

## 轮前链路数据 (2026-08-08 01:33 注入 + 实查确认)

**30min 链路总览 (caller × model × status):**
```
cc4101-primary|dsv4f0731_nv|200|113     ← cc2 的请求
hermes|dsv4f0731_nv|200|25
hermes|dsv4f0731_nv|502|1
```

**30min cc4101-primary 专属 (cc2, 实查):** `200|113` = **0 行非-200, 100% SR**

**30min 错误分类 (type × sub × count × avg_dur):**
```
NVStream_IncompleteRead||1|55488
```
→ 唯一 surface 错误 (502, 55.5s) **归属 hermes** (实查 caller=hermes), cc2 0 行

**30min fallback (实查):** 113 行, fallback_triggered=0 = **0%** (未走 ms_gw)

**30min per-key tier 错误 (实查):**
```
0|NVCFPexecRemoteDisconnected|1      0|pexec_success|24
1|NVCFPexecRemoteDisconnected|1      1|pexec_success|23
2|NVCFPexecRemoteDisconnected|1      2|empty_200|1   2|pexec_success|21
3|NVCFPexecRemoteDisconnected|1      3|pexec_success|21
4|NVCFPexecRemoteDisconnected|3      4|pexec_success|24
```
→ RD (k4 3× 略偏高) + empty_200 (k2) 分布式单点 self-heal, 各 key/time 分散无同 key 连续复发, 低频下沉稳态

**30min buffer/wait/keymanager 日志 (实查):**
```
[NV-BUFFER-START] caller=cc4101-primary max_retries=5 stairs=[90x5] total_deadline=450s
[NV-BUFFER-ATTEMPT] attempt=1/5 timeout=90s ... (多 req 直接 attempt-1 VERDICT=success_tool_call → FLUSH → SUCCESS)
[NV-BUFFER-EXEC-FAIL] NVCF chain failed on attempt 1 key=k4 (req=fabdf347), all_keys_exhausted=True
  → attempt-1 verdict=execute_failed → BACKOFF 5s → attempt-2/5 → success_tool_call → SUCCESS (29s)
```
→ 本轮 1 次 execute_failed (k4, req fabdf347), 5s backoff 后 attempt-2 自愈成功; 其余全 direct flush (attempt-1 成功), 无 exhaust/无 WAIT

## 判定依据

- **cc2-primary (40006) 实查 30min = 0 行非-200, 100% SR** — 主链全绿
- 唯一 surface 错误 (NVStream_IncompleteRead 502) 实查 caller=hermes, **非 cc2**
- fallback 0% — 未触发 ms_gw; buffer 1× execute_failed 单 req 自愈
- tier RD/empty_200 延续 [[ssleof-error-transient-egress-blip]] 低频下沉稳态, 无上浮 surface
- 无新增错误类型, 无配置漂移, 无同 key 连续复发

## 行动

- **无改动 (NOP)**。主链滚动 30min 零表面错误、fallback 0%、buffer 无 exhaust/无 WAIT,
  cc2 范围无配置回归 → 不改码, 不重启。

## 下一步

- 延续 NOP。持续观察 tier RD (k4 3× 略偏高) / empty_200 分布式单点。
- 若无同 key 多请求连续复发、不影响 surface (cc2 0 行非-200), 继续 NOP。
- 若同 key RD/execute_failed 回升且浮上 surface (cc2 非-200 出现), 再查 mihomo 对应线路。