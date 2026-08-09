---
name: r844-opclaw4103-fallback-timeout-fix
description: "R844 opclaw4103 fallback 机制迁移 cc4101 + 超时分层修复 (connect/TTFB/idle 三层分离, circuit 三态, retry primary)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 88f513be-ac30-40ea-b01d-436b672c0fa8
---

R844 (2026-07-14): 把 cc4101 已验证的 fallback 全套机制移植进 opclaw4103, 替换简陋版, 保留 opclaw4103 特有的 openclaw 适配层 (R842c content_filter zombie 拦截 / R766 supplement / R790 异常补 content / FALLBACK_NOTICE / prompt 预检 / all_tiers_exhausted / FALLBACK_RECOVER_S).

**修的真 bug (日志实锤)**: 重启前日志 `23:04:56 REQ → 23:06:26 UPSTREAM-ERR: TimeoutError` 等 90s 才切 fallback. 根因: 旧 `_post_upstream` 建连后立刻 `sock.settimeout(PRIMARY_STREAM_TIMEOUT_S=90s)`, 导致 getresponse() (含 TTFB) 用 90s read timeout 而非 connect timeout — R763 的 connect/read 分离没贯彻到 getresponse 阶段.

**超时三层分离 (对齐 cc4101)**:
- connect: `CC_CONNECT_TIMEOUT_S=10` (TCP 建连, socket.create_connection timeout=)
- header/TTFB: `PRIMARY_HEADER_TIMEOUT=25` / `FALLBACK_HEADER_TIMEOUT=30` (getresponse 阶段, sock.settimeout 在 getresponse 前)
- body idle: `UPSTREAM_IDLE_TIMEOUT=150` (响应头后 _restore_read_timeout 切换, 容纳 thinking 静默期, 对齐 nv_gw NV-THINKING-TIMEOUT 150s)
- 跨 stage 总预算: `CC4101_TOTAL_BUDGET_S=80`
验证: 容器内 `_post_upstream` 指向 accept-silent listener, getresponse hang 在 **25.0s** 超时 (修复前 90s).

**circuit 三态 CLOSED/OPEN/HALF_OPEN**: 模块级 `_fail_count`/`_open_until`/`_lock`, `time.monotonic()` (修 time.time 时钟跳变). `record_primary_success` 清计数+清 open_until (CLOSED). `record_primary_failure` 到阈值(CIRCUIT_FAILURE_THRESHOLD=5)开路. opclaw4103 保留 `_mark_fallback`+`FALLBACK_RECOVER_S=120` 单次 fallback 后短冷却 (cc4101 没有).

**retry primary**: RETRY_PRIMARY_AFTER_FALLBACK=True, 门控=开关+remaining>=PRIMARY_HEADER_TIMEOUT+not is_primary_open. 流式下保守: 仅 fallback 首字节前失败 retry (不在 fallback 流中途失败 retry, 避拼接已发 content).

**部署**: opclaw4103 的 `/app/gateway` 是 bind mount 自宿主 `/opt/cc-infra/proxy/cc-adapter/gateway` — 不需重建镜像, 改宿主源码 + `rm __pycache__/*.pyc` + `docker restart opclaw4103` 即可. 备份在原地 `*.preR844.20260714_050724`. 本地副本在 `/home/opc_uname/cc_ps/NVForge/opclaw4103_patch/`.

**env 实配 (opclaw4103)**: PRIMARY_STREAM_TIMEOUT_S=90(旧,保留兼容不直接用) FALLBACK_TIMEOUT_S=240 FALLBACK_RECOVER_S=120 CIRCUIT_FAILURE_THRESHOLD=5 CIRCUIT_OPEN_S=60 SUPPLEMENT_REASONING_AS_CONTENT=1 PROMPT_TOKEN_LIMIT=120000 ADAPTER_API_KEY=opclaw-gw-token(非默认!).

**未做 (下一轮)**: openclaw.json 配置缺陷 — fallbacks=[] 无第二出口, compaction.model=opclaw4103/glm5_2_nv 与 primary 同 (anti-pattern, 88k 死亡窗口成因). 见 [[r842-88k-zombie-window-root-cause]] [[openclaw-hm2-topology]]. 本轮只修 adapter, 不碰 openclaw 配置.

相关: [[cc-chain-layout-hm2]] [[shared-source-cross-host]] [[r842c-forwarder-content-filter-fallback-fix]] [[r840-openclaw-zombie-empty-stall-fix]]
