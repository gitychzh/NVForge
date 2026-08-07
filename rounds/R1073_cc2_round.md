# R1073 — cc2 NOP 巡检轮 (2026-08-07 20:05 CST)

## 结论: NOP, 不改码

cc2 主链 (cc4101-primary → nv_gw:40006, dsv4f0731_nv) 完全健康:
30min = **105/105 = 100% SR, 0 bad**; fallback 0 次 (0.0%, 1948 total);
唯一 bads 均 **caller=hermes** (越界宿主, 非 cc2 范围, 2× zombie_empty_completion);
per-key 全 pexec_success 15s 窗口内 105 请求 0 错误;
buffer 日志仅正常 traffic (default 5s backoff 因 attempt 1 → success), 无 WAIT/KEYMGR 死锁;
容器 /health 全 200 (40006 nv_gw, 4101 cc4101), nv_gw Up 17h, cc4101 Up 16h.

## 依据

- 注入轮前链路分析 (20:01 CST): cc4101-primary|dsv4f0731_nv|200|107 (100%, 0 bad);
  hermes|dsv4f0731_nv|502×1 (out-of-scope); 整体 dsv4f0731_nv SR=99.4% (174/175);
  top error zombie_empty_completion×1 (hermes); per-key 0/1/2/3/4 全 pexec_success.
- 独立 DB 复核: cc4101-primary 30min = 105/105 200, 0 fail; cc_requests fallback=0/1948;
  zombie_empty_completion×2 全归属 caller=hermes.
- buffer 日志抽查 20:02: 两次 REQUEST 均 attempt 1~2 内 success_tool_call 并 flushed, 无硬失败。

## 数据表

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **105/105 = 100% SR, 0 bad** | ✅ |
| 30min cc_requests | fallback 0 次 (0/1948, 0.0%) | ✅ |
| dsv4f0731_nv 整体 | 99.4% (作参考) | ✅ |
| hermes (越界宿主, 非 cc2) | zombie_empty_completion×2 | ⚠️ 非主链 |
| per-key | 全 5 key pexec_success, 0 误差 | ✅ |
| buffer 日志 | 仅 normal traffic, 无 WAIT/KEYMGR | ✅ |
| 容器 /health | 40006/4101 全 200; nv_gw Up 17h, cc4101 Up 16h | ✅ |

## 下一步

- 保持 NOP 观察。主链连续多轮 0 bad (R1073 = 连续第 N 轮) 已到完全健康基线, 无参数可调。
- 仅当 cc2 主链自身出现 bad 或 fallback > 约 10% 才行动; hermes 越界宿主 bads 不计入 cc2 范围。
- 追踪本窗口 buffer 里出现的 5s backoff (attempt 1 fail → 2): 单条正常, 若多请求连续多次 backoff 才查 NVCF 瞬时抖动; 当前 15s 内 2/2 全成功, 无需动作。

## 参数快照 (未动, 与上轮一致)

- cc4101: PRIMARY=http://nv_gw:40006/v1/messages model=dsv4f0731_nv; FALLBACK=http://ms_gw:40007 model=glm5_2_ms;
  STREAM_TOTAL_DEADLINE=470s, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3, PRIMARY_SKIP_S=30,
  UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, UPSTREAM_TIMEOUT=90,
  NV_INTEGRATE_KEY_COOLDOWN=90, KEY_COOLDOWN=30, NVU_FORCE_STREAM_UPGRADE=0, TIMEOUT=150,
  TIER_TIMEOUT_BUDGET=180, TIER_COOLDOWN=180, MIN_OUTBOUND_INTERVAL=10, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2
- Buffer 5×90s=450s; cc4101 fallback 受 ms_gw (铁律: 不主动禁用, 当前 0 触发)。